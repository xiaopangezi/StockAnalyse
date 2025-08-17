"""
app.py

使用Streamlit创建聊天界面，用于与年报分析AI进行交互

启动：streamlit run app.py

使用：
uv venv --python 3.11 .venv 指定python版本并创建虚拟环境
source .venv/bin/activate 开启python虚拟环境
uv pip install -r pyproject.toml 安装依赖
uv pip install 添加依赖

which python 验证虚拟环境是否正确

deactivate 关闭python虚拟环境

uv pip show streamlit 显示已安装版本

streamlit run app.py 启动streamlit应用

"""

import os
import sys
import streamlit as st
from langchain_community.chat_message_histories import StreamlitChatMessageHistory
from langchain.callbacks.streamlit import StreamlitCallbackHandler

# 添加项目根目录到Python路径
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from reports.LLM_reports import ReportAnalyzer

# 设置页面配置
st.set_page_config(
    page_title="年报分析助手",
    page_icon="📊",
    layout="wide"
)

# 初始化会话状态
if "analyzer" not in st.session_state:
    # 设置目录路径
    base_dir = os.path.dirname(os.path.dirname(__file__))
    txt_dir = os.path.join(base_dir, 'results', 'txt_reports')
    results_dir = os.path.join(base_dir, 'results')
    
    # 初始化消息历史和回调处理器
    messages = StreamlitChatMessageHistory()
    callback_handler = StreamlitCallbackHandler(st.container())
    
    # 初始化分析器
    st.session_state.analyzer = ReportAnalyzer(
        txt_dir=txt_dir,
        results_dir=results_dir,
        message_history=messages,
        callback_handler=callback_handler
    )

# 创建侧边栏
with st.sidebar:
    st.title("年报分析助手")
    st.markdown("""
    ### 功能介绍
    1. 年报内容检索
    2. 财务指标分析
    3. 行业信息查询
    4. 投资建议生成
    
    ### 使用说明
    - 输入公司代码或名称进行查询
    - 可以询问具体的财务指标
    - 支持多轮对话和上下文理解
    """)

# 主聊天界面
st.title("💬 与AI助手对话")

# 显示聊天历史
for message in st.session_state.analyzer.memory.chat_memory.messages:
    with st.chat_message(message.type):
        st.markdown(message.content)

# 获取用户输入
if prompt := st.chat_input("请输入您的问题"):
    # 显示用户消息
    with st.chat_message("human"):
        st.markdown(prompt)
    
    # 显示助手回复
    with st.chat_message("assistant"):
        response_container = st.empty()
        with st.spinner("思考中..."):
            response = st.session_state.analyzer.chat(prompt)
            response_container.markdown(response)

# 添加清除对话按钮
if st.button("清除对话历史"):
    st.session_state.analyzer.memory.clear()
    st.rerun() 