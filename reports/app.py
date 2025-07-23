"""
app.py

使用Streamlit创建聊天界面，用于与年报分析AI进行交互
"""

import os
import streamlit as st
from langchain.memory.chat_message_histories import StreamlitChatMessageHistory
from langchain.callbacks.streamlit import StreamlitCallbackHandler

from LLM_reports import ReportAnalyzer

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
    
    # 添加PDF处理功能
    st.markdown("---")
    st.subheader("添加年报PDF")
    uploaded_file = st.file_uploader("选择PDF文件", type="pdf")
    if uploaded_file:
        # 保存上传的文件
        pdf_dir = os.path.join(st.session_state.analyzer.results_dir, 'pdf_reports')
        os.makedirs(pdf_dir, exist_ok=True)
        pdf_path = os.path.join(pdf_dir, uploaded_file.name)
        
        with open(pdf_path, "wb") as f:
            f.write(uploaded_file.getvalue())
        
        # 处理PDF文件
        with st.spinner("正在处理PDF文件..."):
            st.session_state.analyzer.process_and_store_pdf(pdf_path)
        st.success(f"成功处理文件：{uploaded_file.name}")

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