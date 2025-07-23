import os
import json
import logging
from datetime import datetime
from typing import List, Dict, Any

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.chains import LLMChain, ConversationChain
from langchain.agents import AgentExecutor, create_structured_chat_agent
from langchain_core.messages import SystemMessage
from langchain.tools import Tool
from langchain_community.docstore.wikipedia import Wikipedia
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.memory import ConversationBufferMemory
from langchain.memory.chat_message_histories import StreamlitChatMessageHistory
from langchain.callbacks.streamlit import StreamlitCallbackHandler
import pandas as pd

from download_reports import ensure_stock_reports
from analyze.strategies_buffett import analyze_stock, screen_stocks
from pdf_parser import process_pdf

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ReportAnalyzer:
    def __init__(self, txt_dir: str, results_dir: str, message_history=None, callback_handler=None):
        """
        初始化分析器
        :param txt_dir: 存放年报txt文件的目录
        :param results_dir: 存放分析结果的目录
        :param message_history: Streamlit消息历史记录对象
        :param callback_handler: Streamlit回调处理器
        """
        self.txt_dir = txt_dir
        self.results_dir = results_dir
        self.vector_store = None
        self.message_history = message_history
        self.callback_handler = callback_handler
        
        # 初始化对话记忆
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            chat_memory=message_history if message_history else None,
            return_messages=True
        )
        
        # 初始化LLM
        self.llm = ChatOpenAI(
            openai_api_key=os.getenv("OPENROUTER_API_KEY"),
            openai_api_base=os.getenv("OPENROUTER_BASE_URL"),
            model="deepseek/deepseek-chat-v3-0324:free",
            default_headers={
                "HTTP-Referer": os.getenv("YOUR_SITE_URL"),
                "X-Title": os.getenv("YOUR_SITE_NAME"),
                "OpenRouter-Provider": "chutes/fp8"
            },
            temperature=0,
            streaming=True  # 启用流式输出
        )
        
        # 初始化文本分割器
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=4000,  # 增加chunk大小以获取更多上下文
            chunk_overlap=400,
            length_function=len,
            separators=["\n\n", "\n", "。", "！", "？", ".", "!", "?"]  # 优化中文分割
        )
        
        # 初始化向量化模型
        self.embeddings = HuggingFaceEmbeddings(
            model_name="shibing624/text2vec-base-chinese",
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True}
        )
        
        # 初始化或加载向量存储
        self._init_vector_store()
        
        # 初始化Agent
        self.setup_agents()

    def _init_vector_store(self):
        """初始化或加载向量存储"""
        persist_directory = os.path.join(self.results_dir, 'vector_store')
        
        # 如果向量存储目录存在，加载现有的存储
        if os.path.exists(persist_directory):
            self.vector_store = Chroma(
                persist_directory=persist_directory,
                embedding_function=self.embeddings
            )
        else:
            # 创建新的向量存储
            self.vector_store = Chroma(
                persist_directory=persist_directory,
                embedding_function=self.embeddings
            )

    def process_and_store_pdf(self, pdf_path: str):
        """
        处理PDF文件并存储到向量数据库
        :param pdf_path: PDF文件路径
        """
        try:
            # 处理PDF文件，获取章节内容
            chapters = process_pdf(pdf_path)
            if not chapters:
                logging.warning(f"未能从 {pdf_path} 提取到任何章节内容")
                return
            
            # 准备文档列表
            texts = []
            metadatas = []
            
            # 处理每个章节
            for chapter in chapters:
                # 分割章节内容
                chunks = self.text_splitter.split_text(chapter['content'])
                
                # 为每个文本块添加元数据
                for chunk in chunks:
                    texts.append(chunk)
                    metadatas.append({
                        'title': chapter['title'],
                        'source': pdf_path,
                        'chunk_size': len(chunk)
                    })
            
            # 添加到向量存储
            self.vector_store.add_texts(
                texts=texts,
                metadatas=metadatas
            )
            
            # 持久化存储
            self.vector_store.persist()
            
            logging.info(f"成功处理并存储 {pdf_path} 的内容，共 {len(texts)} 个文本块")
            
        except Exception as e:
            logging.error(f"处理PDF文件 {pdf_path} 时出错: {str(e)}")

    def create_download_tool(self) -> Tool:
        """
        创建一个用于下载和转换年报的工具
        :return: Langchain Tool对象
        """
        def download_reports(stock_code: str) -> str:
            """
            下载并转换指定股票的年报
            :param stock_code: 股票代码
            :return: 处理结果信息
            """
            return ensure_stock_reports(stock_code, self.results_dir, delete_pdf=False)
        
        return Tool(
            name="download_stock_reports",
            func=download_reports,
            description="下载并转换指定股票代码的年报为文本格式。输入参数为股票代码（字符串格式）。"
        )

    def create_stock_screening_tool(self) -> Tool:
        """
        创建一个用于股票筛选的工具
        :return: Langchain Tool对象
        """
        def screen_stock(query: str) -> str:
            """
            根据查询内容执行股票筛选
            :param query: 查询字符串，格式为：
                        - "analyze:股票代码:交易所:行业"（分析单个股票）
                        - "screen:行业"（筛选所有符合条件的股票）
            :return: 分析结果或筛选结果的描述
            """
            try:
                parts = query.split(':')
                action = parts[0].lower()

                if action == 'analyze':
                    if len(parts) < 3:
                        return "错误：分析单个股票需要提供股票代码和交易所。格式：analyze:股票代码:交易所[:行业]"
                    
                    stock_code = parts[1]
                    exchange = parts[2]
                    industry = parts[3] if len(parts) > 3 else None
                    
                    success, result = analyze_stock(stock_code, exchange, industry)
                    if success:
                        return f"股票 {stock_code} 符合巴菲特投资策略，详细指标：\n" + \
                               "\n".join([f"{k}: {v}" for k, v in result.items()])
                    else:
                        reason = result.get('reason', result.get('error', '未知原因'))
                        return f"股票 {stock_code} 不符合巴菲特投资策略。原因：{reason}"

                elif action == 'screen':
                    industry = parts[1] if len(parts) > 1 else None
                    output_file = os.path.join(self.results_dir, 'screened_stocks.csv')
                    
                    # 执行筛选
                    screen_stocks(output_file, industry)
                    
                    # 读取结果并返回摘要
                    if os.path.exists(output_file):
                        df = pd.read_csv(output_file)
                        return f"筛选完成！共找到 {len(df)} 只符合巴菲特投资策略的股票。\n" + \
                               f"结果已保存至：{output_file}"
                    else:
                        return "筛选完成，但未找到符合条件的股票。"
                else:
                    return "错误：无效的操作。请使用 'analyze' 或 'screen'。"

            except Exception as e:
                return f"执行股票筛选时出错：{str(e)}"

        return Tool(
            name="stock_screening",
            func=screen_stock,
            description="""
            股票筛选工具，支持两种操作：
            1. 分析单个股票：使用 'analyze:股票代码:交易所[:行业]' 格式
               例如：'analyze:600519:SH:白酒' 或 'analyze:600519:SH'
            2. 筛选所有股票：使用 'screen[:行业]' 格式
               例如：'screen:白酒' 或 'screen'
            """
        )

    def create_wiki_search_tool(self) -> Tool:
        """
        创建一个用于维基百科搜索的工具
        :return: Langchain Tool对象
        """
        wiki = Wikipedia()

        def search_wiki(query: str) -> str:
            """
            在维基百科中搜索信息
            :param query: 搜索关键词
            :return: 搜索结果
            """
            try:
                # 尝试搜索维基百科
                result = wiki.search(query)
                
                # 如果结果是字符串，说明没有找到精确匹配，返回相似条目提示
                if isinstance(result, str):
                    return f"未找到精确匹配的条目。{result}"
                
                # 如果找到了文档，返回其内容
                return f"找到相关信息：\n\n{result.page_content}"
                
            except Exception as e:
                return f"维基百科搜索出错：{str(e)}"

        return Tool(
            name="wiki_search",
            func=search_wiki,
            description="""
            维基百科搜索工具，用于查找公司、行业或其他相关信息。
            输入：搜索关键词（如公司名称、行业名称等）
            输出：相关的维基百科内容摘要
            示例：
            - "贵州茅台"
            - "白酒行业"
            - "证券交易所"
            """
        )

    def create_retriever_tool(self) -> Tool:
        """
        创建一个用于检索年报内容的工具
        :return: Langchain Tool对象
        """
        def retrieve_content(query: str) -> str:
            """
            检索年报内容
            :param query: 查询字符串
            :return: 相关内容
            """
            try:
                # 使用向量存储进行相似度搜索
                docs = self.vector_store.similarity_search_with_score(
                    query=query,
                    k=3  # 返回前3个最相关的结果
                )
                
                if not docs:
                    return "未找到相关内容。"
                
                # 格式化结果
                results = []
                for doc, score in docs:
                    results.append(f"来源: {doc.metadata['title']}\n相关度: {1 - score:.2%}\n内容:\n{doc.page_content}\n")
                
                return "\n---\n".join(results)
                
            except Exception as e:
                return f"检索过程出错：{str(e)}"

        return Tool(
            name="report_retriever",
            func=retrieve_content,
            description="""
            年报内容检索工具，用于查找特定主题或关键词在年报中的相关内容。
            输入：查询关键词或问题
            输出：相关的年报内容片段
            示例查询：
            - "公司的主营业务是什么"
            - "近年来的营收情况"
            - "未来发展战略"
            """
        )

    def setup_agents(self):
        """设置不同任务的agents"""
        # 年报分析agent
        system_message = """你是一个专业的财务分析师，擅长分析企业年报。你的分析应该：
            1. 客观准确，基于事实和数据
            2. 重点突出，抓住关键信息
            3. 逻辑清晰，层次分明
            4. 专业严谨，用词准确
        """
        human_message = """
            请分析以下年报内容：
            {text_chunk}
            
            请从以下几个方面进行分析，要求简洁明了，直击重点：
            1. 主营业务发展情况：
               - 营收和利润情况
               - 主要业务板块表现
               - 市场份额变化
            
            2. 下一年发展计划：
               - 具体业务目标
               - 战略重点
               - 投资计划
            
            3. 存在的主要风险：
               - 行业风险
               - 经营风险
               - 财务风险
            \n前面的工具使用记录：\n{agent_scratchpad}
        """
        
        self.single_report_agent = create_structured_chat_agent(
            llm=self.llm,
            tools=[],
            prompt=ChatPromptTemplate([
                ("system", system_message),
                ("human", human_message),
            ]),
        )
        self.single_report_executor = AgentExecutor(agent=self.single_report_agent, tools=[])

        # 多年对比agent
        comparison_system_message = """你是一个资深的企业战略分析师，擅长对比分析企业多年发展历程。你的分析应该：
            1. 找出发展趋势
            2. 评估战略执行力
            3. 判断管理层能力
            4. 预测未来发展
        """
        
        self.comparison_agent = create_structured_chat_agent(
            llm=self.llm,
            tools=[],
            prompt=ChatPromptTemplate([
                ("system", comparison_system_message),
                ("human", """
                    请对比分析该公司多年的年报数据：
                    {yearly_analyses}
                    
                    请从以下维度进行分析：
                    1. 计划执行力分析：
                    - 去年计划与今年实际的对比
                    - 完成度评估
                    - 未完成项目原因分析
                    
                    2. 战略连续性分析：
                    - 战略方向变化
                    - 战略执行的连续性
                    - 转型或调整的合理性
                    
                    3. 管理层决策评估：
                    - 重大决策的效果
                    - 风险应对措施的有效性
                    - 管理层执行力评价
                    \n前面的工具使用记录：\n{agent_scratchpad}
                """),
            ])
        )
        self.comparison_executor = AgentExecutor(agent=self.comparison_agent, tools=[])

        # 最终总结agent
        final_system_message = """你是一个专业的投资顾问，需要基于企业分析给出专业的投资建议。你的分析应该：
            1. 全面系统
            2. 前瞻性强
            3. 建议可执行
            4. 风险提示充分
        """
        
        # 创建工具
        download_tool = self.create_download_tool()
        screening_tool = self.create_stock_screening_tool()
        wiki_tool = self.create_wiki_search_tool()
        retriever_tool = self.create_retriever_tool()
        
        # 设置Agent的回调
        callbacks = [self.callback_handler] if self.callback_handler else None
        
        self.final_agent = create_structured_chat_agent(
            llm=self.llm,
            tools=[download_tool, screening_tool, wiki_tool, retriever_tool],
            prompt=ChatPromptTemplate([
                ("system", final_system_message),
                ("human", """
            请基于以下信息生成综合分析报告：
            公司信息：{company_info}
            多年分析：{multi_year_analysis}
            聊天历史：{chat_history}
            
            请从以下维度进行深入分析：
            1. 行业分析：
               - 行业发展阶段
               - 行业竞争格局
               - 未来发展趋势
            
            2. 宏观影响：
               - 政策影响
               - 经济周期影响
               - 技术变革影响
            
            3. 公司战略：
               - 战略定位评估
               - 转型效果分析
               - 核心竞争力分析
            
            4. 管理层评估：
               - 管理团队背景
               - 过往业绩表现
               - 社会评价分析
            
            5. 投资建议：
               - 投资价值分析
               - 主要风险提示
               - 具体投资建议
            \n前面的工具使用记录：\n{agent_scratchpad}
            """),
            ])
        )
        self.final_executor = AgentExecutor(
            agent=self.final_agent,
            tools=[download_tool, screening_tool, wiki_tool, retriever_tool],
            memory=self.memory,
            callbacks=callbacks,
            verbose=True
        )

    def analyze_single_report(self, file_path: str) -> Dict[str, Any]:
        """
        分析单个年报文件
        :param file_path: txt格式年报文件路径
        :return: 年报分析结果字典
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()

            # 切分文本
            chunks = self.text_splitter.split_text(text)
            
            # 分析每个文本块并合并结果
            all_analyses = []
            for chunk in chunks:
                result = self.single_report_executor.invoke({
                    "text_chunk": chunk
                })
                all_analyses.append(result['output'])
            
            # 合并所有分析结果
            combined_analysis = "\n\n".join(all_analyses)
            
            # 提取年份和公司信息
            filename = os.path.basename(file_path)
            code, name, year = filename.replace('.txt', '').split('_')
            
            return {
                'code': code,
                'name': name,
                'year': year,
                'analysis': combined_analysis
            }
            
        except Exception as e:
            logging.error(f"分析年报时出错 {file_path}: {str(e)}")
            return None

    def compare_multiple_years(self, company_analyses: List[Dict[str, Any]]) -> str:
        """
        对比多年的年报分析
        :param company_analyses: 按年份排序的公司年报分析列表
        :return: 多年对比分析结果
        """
        try:
            result = self.comparison_executor.invoke({
                "yearly_analyses": json.dumps(company_analyses, ensure_ascii=False)
            })
            return result['output']
        except Exception as e:
            logging.error(f"多年对比分析时出错: {str(e)}")
            return ""

    def generate_final_summary(self, company_info: Dict[str, Any], multi_year_analysis: str) -> str:
        """
        生成最终的综合分析报告
        :param company_info: 公司基本信息
        :param multi_year_analysis: 多年对比分析结果
        :return: 最终报告内容
        """
        try:
            result = self.final_executor.invoke({
                "company_info": json.dumps(company_info, ensure_ascii=False),
                "multi_year_analysis": multi_year_analysis
            })
            return result['output']
        except Exception as e:
            logging.error(f"生成最终报告时出错: {str(e)}")
            return ""

    def save_analysis(self, company_code: str, final_report: str) -> None:
        """
        保存分析报告
        :param company_code: 公司代码
        :param final_report: 最终报告内容
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{company_code}_analysis_{timestamp}.txt"
        output_path = os.path.join(self.results_dir, filename)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(final_report)
        
        logging.info(f"分析报告已保存到: {output_path}")

    def process_company(self, company_code: str) -> None:
        """
        处理单个公司的所有年报
        :param company_code: 公司代码
        """
        try:
            # 获取该公司的所有年报文件
            company_files = [f for f in os.listdir(self.txt_dir) 
                           if f.startswith(f"{company_code}_") and f.endswith('.txt')]
            
            if not company_files:
                logging.error(f"未找到公司 {company_code} 的年报文件")
                return
            
            # 按年份排序
            company_files.sort(key=lambda x: x.split('_')[2].replace('.txt', ''))
            
            # 分析每个年报
            yearly_analyses = []
            for file_name in company_files:
                logging.info(f"正在分析年报: {file_name}")
                file_path = os.path.join(self.txt_dir, file_name)
                analysis = self.analyze_single_report(file_path)
                if analysis:
                    yearly_analyses.append(analysis)
            
            # 多年对比分析
            logging.info("开始多年对比分析...")
            multi_year_analysis = self.compare_multiple_years(yearly_analyses)
            
            # 生成最终报告
            logging.info("生成最终综合报告...")
            company_info = {
                'code': company_code,
                'name': yearly_analyses[0]['name'],
                'years_analyzed': [a['year'] for a in yearly_analyses]
            }
            final_report = self.generate_final_summary(company_info, multi_year_analysis)
            
            # 保存分析结果
            self.save_analysis(company_code, final_report)
            
        except Exception as e:
            logging.error(f"处理公司 {company_code} 时出错: {str(e)}")

    def chat(self, message: str) -> str:
        """
        处理用户消息并返回回复
        :param message: 用户消息
        :return: AI回复
        """
        try:
            # 使用Agent处理消息
            response = self.final_executor.invoke({
                "input": message
            })
            return response["output"]
        except Exception as e:
            logging.error(f"处理消息时出错: {str(e)}")
            return f"抱歉，处理您的消息时出现错误：{str(e)}"

def main():
    # 设置目录路径
    base_dir = os.path.dirname(os.path.dirname(__file__))
    txt_dir = os.path.join(base_dir, 'results', 'txt_reports')
    results_dir = os.path.join(base_dir, 'results')
    
    # 创建分析器实例
    analyzer = ReportAnalyzer(txt_dir, results_dir)
    
    # 测试分析平安银行的年报
    test_company_code = '000001'
    analyzer.process_company(test_company_code)

if __name__ == '__main__':
    main()
