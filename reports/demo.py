from dotenv import load_dotenv
from langchain_core.runnables import RunnablePassthrough
from langchain_openai import ChatOpenAI
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
import os
from langchain_core.documents import Document
from langchain_core.prompts import PromptTemplate

# 加载 .env 文件中的环境变量
load_dotenv()

llm = ChatOpenAI(
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

embeddings = HuggingFaceEmbeddings(
    model_name="shibing624/text2vec-base-chinese",
    model_kwargs={'device': 'mps'},
    encode_kwargs={'normalize_embeddings': True}
)

# 为每个文档添加元数据
documents_with_metadata = [
    Document(
        page_content = "一、公司治理的基本状况",
        metadata = {
            "stock": "比亚迪",
            "year": "2024",
            "report_type": "annual",
            "content": "报告期内，公司严格按照《公司法》、《证券法》、《上市公司治理准则》等法律法规的要求，不断完善公司治理结构，提高公司治理水平。公司治理结构合理，决策程序规范，内部控制有效，信息披露及时、准确、完整。"
        },
    ),
    Document(
        page_content = "二、公司相对于控股股东、实际控制人在保证公司资产、人员、财务、机构、业务等方面的独立情况",
        metadata = {
            "stock": "比亚迪",
            "year": "2024",
            "report_type": "annual",
            "content": """公司在业务、人员、资产、机构、财务等方面与控股股东相互独立，公司具有独立完整的业务及自主经营能力。
1、业务：公司业务独立于控股股东及其下属企业，拥有独立完整的供应、生产和销售系统，独立开展业务，不
依赖于股东或其它任何关联方。
2、人员：公司人员、劳动、人事及工资完全独立。公司总裁、副总裁、董事会秘书、财务总监等高级管理人员
均在公司工作并领取薪酬。未在控股股东及其下属企业担任除董事、监事以外的任何职务和领取报酬。
3、资产：公司拥有独立于控股股东的生产经营场所，拥有独立完整的资产结构，拥有独立的生产系统、辅助生
产系统和配套设施、土地使用权、房屋所有权等资产，拥有独立的采购和销售系统。
4、机构：公司设立了健全的组织机构体系，独立运作，不存在与控股股东或其职能部门之间的从属关系。
5、财务：公司有独立的财务会计部门，建立了独立的会计核算体系和财务管理制度，独立进行财务决策。公司
独立开设银行账户，独立纳税。"""
        },
    ),
    Document(
        page_content = "四、报告期内召开的年度股东大会和临时股东大会的有关情况",
        metadata = {
            "stock": "比亚迪",
            "year": "2024",
            "report_type": "annual",
            "content": """公司现任董事、监事、高级管理人员专业背景、主要工作经历以及目前在公司的主要职责
（1）董事会成员
王传福先生，一九六六年出生，中国国籍，硕士研究生学历，高级工程师。王先生于一九八七年毕业于中南工业
大学（现为中南大学），主修冶金物理化学，获学士学位；并于一九九零年毕业于中国北京有色金属研究总院，主修
冶金物理化学，获硕士学位。王先生历任北京有色金属研究总院副主任、深圳市比格电池有限公司总经理，并于一九
九五年二月与吕向阳先生共同创办深圳市比亚迪实业有限公司（于二零零二年六月十一日变更为比亚迪股份有限公司，
以下简称“比亚迪实业”）任总经理；现任本公司董事长、执行董事兼总裁，负责本公司一般营运及制定本公司各项
业务策略，并担任比亚迪电子（国际）有限公司的非执行董事及主席、比亚迪半导体股份有限公司董事长、深圳腾势
新能源汽车有限公司董事长、南方科技大学理事。王先生为享受国务院特殊津贴的科技专家，曾荣获「二零零八年
CCTV 中国经济年度人物年度创新奖」、「二零一四年扎耶德未来能源奖个人终身成就奖」、「二零一六年联合国开
发计划署「可持续发展顾问委员会」创始成员」、「“十三五”国家发展规划专家委员会委员」、「二零一九年第五
届全国非公有制经济人士优秀中国特色社会主义事业建设者」、「深圳经济特区建立 40 周年创新创业人物和先进模
范人物」、「全国抗击新冠肺炎民营经济先进个人」等奖项，王先生在《财富》杂志评选的“2023 年中国最具影响
力的 50 位商界领袖”以及福布斯中国发布的“2023 福布斯中国最佳 CEO”榜单中，均荣登榜首。"""
        },
    ),
]

vector_store = Chroma.from_documents(
    documents_with_metadata,
    embedding=embeddings,
)

retriever = vector_store.as_retriever(search_kwargs={
    "k": 1,
    "filter": {
        "$and": [
            {"stock": "比亚迪"},
            {"year": "2023"}
        ]
    }
})

messages = """
    使用提供的上下文回答这个问题
    {question}
    
    上下文：
    {context}
"""

prompt = PromptTemplate.from_template(messages)

chain = {'question': RunnablePassthrough(), 'context': retriever} | prompt | llm

response = chain.invoke('比亚迪公司的基本面')
print(response)