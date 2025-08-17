# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

StockAnalyse is a comprehensive Chinese stock analysis platform that combines traditional financial analysis with AI-powered insights. The system provides:

- **Stock Screening**: Implements Warren Buffett-style investment criteria for filtering stocks
- **AI-Powered Report Analysis**: Uses LLMs to analyze annual reports and provide investment recommendations
- **Interactive Chat Interface**: Streamlit-based web interface for querying stock information
- **Multi-year Analysis**: Compares company performance across multiple years

## Architecture

The codebase is organized into two main packages:

### 1. `analyze/` - Financial Analysis Engine
- **Data Fetching**: Uses AKShare to retrieve real-time Chinese stock market data
- **Buffett Strategy**: Implements 6-criteria screening system (ROE >15%, debt ratio <50%, etc.)
- **Stock Processing**: Handles stock codes from Beijing (BJ), Shanghai (SH), and Shenzhen (SZ) exchanges

### 2. `reports/` - AI Report Analysis System
- **PDF Processing**: Extracts and structures annual report content from PDFs
- **Vector Storage**: Uses ChromaDB with Chinese text embeddings for semantic search
- **Multi-Agent System**: Three specialized AI agents for different analysis types
- **Streamlit Interface**: Interactive web-based chat interface

## Key Dependencies

- **Data**: AKShare, pandas, openpyxl
- **AI**: LangChain, OpenAI API (via OpenRouter), HuggingFace embeddings
- **Web**: Streamlit for UI, ChromaDB for vector storage
- **PDF**: pdfplumber, pypdf for document processing

## Common Commands

### Development Setup
```bash
# Install dependencies
uv venv --python 3.11 .venv
source .venv/bin/activate
uv pip install -r pyproject.toml

# Start web interface
streamlit run reports/app.py

# Run stock screening (from project root)
python -c "from analyze.strategies_buffett import screen_stocks; screen_stocks()"
```

### Stock Analysis
```bash
# Analyze single stock
python -c "from analyze.strategies_buffett import analyze_stock; print(analyze_stock('600519', 'SH'))"

# Screen stocks by industry
python -c "from analyze.strategies_buffett import screen_stocks; screen_stocks(industry='白酒')"
```

### AI Report Processing
```bash
# Process company reports (from project root)
python -c "from reports.LLM_reports import ReportAnalyzer; ReportAnalyzer('results/txt_reports', 'results').process_company('000001')"
```

## Environment Setup

Required `.env` file:
```
OPENROUTER_API_KEY=your_openrouter_key
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
YOUR_SITE_URL=https://your-site.com
YOUR_SITE_NAME=StockAnalyse
```

## File Structure

```
├── analyze/                    # Financial analysis package
│   ├── stock_data_fetcher.py   # AKShare data retrieval
│   └── strategies_buffett.py   # Buffett screening logic
├── reports/                    # AI analysis package
│   ├── LLM_reports.py          # Multi-agent AI system
│   ├── app.py                  # Streamlit web interface
│   ├── pdf_parser.py           # PDF processing utilities
│   └── download_reports.py     # Report download automation
├── results/                    # Generated outputs
│   ├── txt_reports/           # Processed annual reports
│   ├── vector_store/          # ChromaDB vector storage
│   └── screened_stocks.csv    # Buffett screening results
└── pyproject.toml             # Python dependencies
```

## Key Features

### Stock Screening Criteria (Buffett Strategy)
1. ROE > 15% (5-year average)
2. Debt ratio < 50%
3. Gross profit margin > 30%
4. Net profit margin > 10%
5. Positive free cash flow
6. Main business profit ratio > 70%

### AI Analysis Workflow
1. **PDF Processing**: Extract text from annual reports
2. **Vector Storage**: Index content for semantic search
3. **Multi-Agent Analysis**: 
   - Single report analysis
   - Multi-year comparison
   - Investment recommendation synthesis
4. **Interactive Query**: Natural language querying via Streamlit

## Usage Patterns

### For Stock Screening
- Use `analyze.strategies_buffett.screen_stocks()` for batch processing
- Results saved to `results/screened_stocks.csv`
- Supports industry-specific filtering

### For Report Analysis
- Reports processed from `results/txt_reports/`
- Vector store in `results/vector_store/`
- Final reports saved to `results/[company_code]_analysis_[timestamp].txt`

### For Web Interface
- Access via `http://localhost:8501` after `streamlit run reports/app.py`
- Supports natural language queries about stocks and reports
- Real-time chat with AI financial analyst