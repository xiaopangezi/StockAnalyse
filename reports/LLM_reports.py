import os
import json
import logging
from datetime import datetime
from typing import List, Dict, Any

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.chains import LLMChain
from langchain.agents import AgentExecutor, create_structured_chat_agent
from langchain_core.messages import SystemMessage
import pandas as pd

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ReportAnalyzer:
    def __init__(self, txt_dir: str, results_dir: str):
        """
        初始化分析器
        :param txt_dir: 存放年报txt文件的目录
        :param results_dir: 存放分析结果的目录
        """
        self.txt_dir = txt_dir
        self.results_dir = results_dir
        
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
            temperature=0
        )
        
        # 初始化文本分割器
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=4000,  # 增加chunk大小以获取更多上下文
            chunk_overlap=400,
            length_function=len,
            separators=["\n\n", "\n", "。", "！", "？", ".", "!", "?"]  # 优化中文分割
        )
        
        # 初始化Agent
        self.setup_agents()

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
        
        self.final_agent = create_structured_chat_agent(
            llm=self.llm,
            tools=[],
            prompt=ChatPromptTemplate([
                ("system", final_system_message),
                ("human", """
            请基于以下信息生成综合分析报告：
            公司信息：{company_info}
            多年分析：{multi_year_analysis}
            
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
        self.final_executor = AgentExecutor(agent=self.final_agent, tools=[])

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
