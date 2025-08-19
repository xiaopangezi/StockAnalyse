# StockAnalyse

面向中文年报的智能分析平台，集成了 PDF 解析、目录抽取、章节拆分、向量检索与多代理大模型分析。

## 环境与安装

- Python: >= 3.13
- 推荐使用 pip 或 uv 安装项目依赖。

使用 pip：
```bash
pip install -U pip
pip install -e .
```

或使用 uv（可选）：
```bash
pipx install uv  # 若尚未安装
uv pip install -e .
```

依赖说明：
- 已在 `pyproject.toml` 中声明 `pdfplumber`，用于结合坐标读取页面行与表格；`pypdf` 用于读取目录与基本页信息。

## 快速开始

### 1. 批量解析 PDF 年报并生成 JSON
从项目根目录运行：
```bash
python reports/pdf_parser.py
```
默认读取 `results/pdf_reports` 目录下的 PDF，输出 JSON 至 `reports/json_reports`。

解析逻辑（简要）：
- 目录抽取：使用 `pypdf` 读取大纲为树形结构。
- 内容抽取：使用 `pdfplumber` 的行级 API 与表格检测。
  - 起始页：从章节标题所在行开始截取。
  - 表格处理：检测表格区域坐标，落入表格区域的文本行由表格内容替换（按行拼接）。
  - 结束页：截断至下一章节标题出现之前（若无同级下一节则递归寻找祖先的下一节；最终退化到文档末尾）。

### 2. 启动 Streamlit 分析界面
```bash
streamlit run reports/app.py
```

### 3. 下载 PDF 年报
```bash
python reports/download_reports.py
```

## 环境变量
将以下变量写入 `.env` 或在环境中导出：
```bash
OPENROUTER_API_KEY=your_openrouter_key
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
YOUR_SITE_URL=https://your-site.com
YOUR_SITE_NAME=StockAnalyse
```

## 测试
项目提供 `test/` 目录的单元测试：
```bash
pytest -q
```

## 常见问题
- 若本机无系统级依赖，`pdfplumber` 仍可直接工作（其依赖已在 `pyproject.toml` 声明，包括 `pdfminer-six` 和 `Pillow`）。
- 若页面不含可提取文本，日志会提示并跳过该页。


