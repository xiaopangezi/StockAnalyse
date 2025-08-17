# Reports 模块说明文档

## 概述

`reports` 模块是 StockAnalyse 项目的核心组件，负责处理公司年报的下载、解析、分析和交互式查询。该模块集成了多种AI技术，包括自然语言处理、向量数据库和大型语言模型，为用户提供智能化的财务报告分析服务。

## 文件结构

```
reports/
├── __init__.py              # 模块初始化文件
├── app.py                   # Streamlit Web应用主界面
├── LLM_reports.py           # AI报告分析核心引擎
├── pdf_parser.py            # PDF文档解析器
├── download_reports.py      # 年报下载工具
├── fetch_reports.py         # 巨潮资讯网爬虫
├── demo.py                  # 功能演示脚本
└── json_reports/            # 解析后的JSON报告存储目录
```

## 核心文件详解

### 1. `app.py` - Streamlit Web应用界面

**功能描述：**
- 创建基于Streamlit的聊天界面，用于与年报分析AI进行交互
- 提供用户友好的Web界面，支持自然语言查询
- 集成聊天历史记录和上下文管理

**主要特性：**
- 响应式Web界面设计
- 实时AI对话功能
- 聊天历史持久化
- 清除对话记录功能

**使用方法：**
```bash
streamlit run reports/app.py
```

**技术架构：**
- 使用Streamlit框架构建Web界面
- 集成LangChain的Streamlit组件
- 支持流式输出和实时交互

### 2. `LLM_reports.py` - AI报告分析核心引擎

**功能描述：**
- 实现多代理AI系统，专门用于分析公司年报
- 集成向量数据库进行语义搜索
- 提供智能化的财务分析和投资建议

**核心组件：**
- **ReportAnalyzer类**: 主要的分析器类
- **向量存储**: 使用ChromaDB存储文档向量
- **文本分割**: 智能文本分块处理
- **多代理系统**: 不同类型的AI分析代理

**主要功能：**
- 年报内容检索和查询
- 财务指标智能分析
- 行业信息查询
- 投资建议生成
- 多年数据对比分析

**技术特点：**
- 使用HuggingFace中文嵌入模型
- 集成OpenAI API (通过OpenRouter)
- 支持流式输出和实时响应

### 3. `pdf_parser.py` - PDF文档解析器

**功能描述：**
- 解析PDF格式的年报文档
- 提取文档的目录结构和章节内容
- 将PDF转换为结构化的JSON格式

**核心类：**
- **PdfOutlineNode**: PDF目录节点类，构建树形结构
- **PdfParser**: PDF解析器主类

**主要功能：**
- 自动提取PDF目录结构
- 按章节拆分文档内容
- 智能内容清理（去除页眉页脚）
- 生成标准化的JSON输出
- 支持批量PDF处理

**技术特点：**
- 使用PyPDF2库进行PDF解析
- 智能章节识别和内容提取
- 自动生成章节ID和层级关系
- 支持中文文档处理

**输出格式：**
```json
{
  "pdf_metadata": {
    "file_name": "002594_比亚迪_2024.pdf",
    "report_title": "比亚迪2024年年度报告",
    "company_name": "比亚迪股份有限公司",
    "company_stock_code": "002594.SZ"
  },
  "outline": [
    {
      "content": "章节内容...",
      "metadata": {
        "section_id": "1.2.3",
        "section_title": "章节标题",
        "page": 15
      }
    }
  ]
}
```

### 4. `download_reports.py` - 年报下载工具

**功能描述：**
- 从网络下载公司年报PDF文件
- 支持PDF到TXT的格式转换
- 管理下载文件的存储和清理

**主要功能：**
- HTTP下载PDF文件
- 文件格式验证
- 重试机制和错误处理
- 文件存储管理
- 可选的PDF清理（节省存储空间）

**技术特点：**
- 使用requests库进行HTTP下载
- 支持断点续传和重试
- 智能文件命名和路径管理
- 集成pdfplumber进行格式转换

### 5. `fetch_reports.py` - 巨潮资讯网爬虫

**功能描述：**
- 从巨潮资讯网自动获取年报发布信息
- 支持按年份、行业、交易所等条件筛选
- 批量获取年报下载链接

**主要功能：**
- 自动分页获取年报列表
- 支持多种筛选条件
- 批量处理和数据导出
- 进度显示和状态监控

**技术特点：**
- 使用requests库进行API调用
- 支持分页和批量处理
- 智能重试和错误处理
- 数据格式化和导出

### 6. `demo.py` - 功能演示脚本

**功能描述：**
- 展示向量数据库和AI分析的基本功能
- 提供代码示例和测试用例
- 验证系统各组件的工作状态

**演示内容：**
- 文档向量化存储
- 语义搜索功能
- AI问答系统
- 元数据过滤查询

**使用方法：**
```bash
cd reports
python demo.py
```

## 工作流程

### 1. 年报获取流程
```
巨潮资讯网 → fetch_reports.py → 获取年报列表 → download_reports.py → 下载PDF文件
```

### 2. 文档处理流程
```
PDF文件 → pdf_parser.py → 解析目录结构 → 提取章节内容 → 生成JSON格式
```

### 3. AI分析流程
```
JSON报告 → LLM_reports.py → 向量化存储 → 语义搜索 → AI分析 → 生成报告
```

### 4. 用户交互流程
```
用户查询 → app.py → LLM_reports.py → 向量搜索 → AI分析 → 返回结果
```

## 配置要求

### 环境变量
```bash
OPENROUTER_API_KEY=your_openrouter_key
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
YOUR_SITE_URL=https://your-site.com
YOUR_SITE_NAME=StockAnalyse
```

### 依赖包
- langchain 及相关组件
- streamlit
- pypdf2/pdfplumber
- requests
- pandas
- huggingface transformers

## 使用示例

### 启动Web应用
```bash
cd reports
streamlit run app.py
```

### 批量处理PDF
```bash
cd reports
python pdf_parser.py
```

### 下载年报
```bash
cd reports
python download_reports.py
```

### 运行演示
```bash
cd reports
python demo.py
```

## 注意事项

1. **API密钥**: 确保正确配置OpenRouter API密钥
2. **存储空间**: PDF文件可能较大，注意磁盘空间管理
3. **网络连接**: 下载功能需要稳定的网络连接
4. **中文支持**: 系统专门优化了中文文档处理
5. **性能优化**: 大量文档处理时注意内存使用

## 扩展功能

- 支持更多文档格式（Word、Excel等）
- 集成更多AI模型和算法
- 添加数据可视化功能
- 支持多语言报告分析
- 增加实时数据更新功能
