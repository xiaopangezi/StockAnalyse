import requests
import re
import os
import logging
import pdfplumber
import pandas as pd

#下载pdf
def download_pdf(pdf_url, pdf_file_path):
    try:
        headers = {
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Cache-Control": "no-cache",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        }

        session = requests.Session()
        session.headers.update(headers)

        # 请求PDF文件
        response = session.get(pdf_url, stream=True, timeout=15)
        # 检查HTTP状态码
        if response.status_code == 403:
            logging.error(f"❌ 403 Forbidden: 服务器禁止访问 {pdf_url}")
            return False
        elif response.status_code != 200:
            logging.error(f"❌ 请求失败: {response.status_code} - {response.text[:500]}")
            return False
        content_type = response.headers.get("Content-Type", "")
        if "pdf" not in content_type.lower():
            logging.error(f"❌ 服务器返回的不是 PDF: {content_type}")
            return False
        # 写入PDF文件
        with open(pdf_file_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        # 验证文件是否为PDF
        if os.path.exists(pdf_file_path) and os.path.getsize(pdf_file_path) > 0:
            with open(pdf_file_path, "rb") as f:
                first_bytes = f.read(5)
                if not first_bytes.startswith(b"%PDF"):
                    logging.error(f"❌ 下载的文件不是 PDF！可能是 HTML 错误页面，请检查 {pdf_file_path}")
                    return False
        else:
            logging.error(f"❌ 下载失败，文件大小为 0 KB: {pdf_file_path}")
            return False
        logging.info(f"✅ PDF 下载成功: {pdf_file_path}")
        return True
    except requests.exceptions.RequestException as e:
        logging.error(f"❌ 下载 PDF 文件失败: {e}")
        return False

#文件转换
def convert(code, name, year, pdf_url, pdf_dir, txt_dir, flag_pdf):
    pdf_file_path = os.path.join(pdf_dir, re.sub(r'[\\/:*?"<>|]', '',f"{code:06}_{name}_{year}.pdf"))
    txt_file_path = os.path.join(txt_dir, re.sub(r'[\\/:*?"<>|]', '', f"{code:06}_{name}_{year}.txt"))

    try:
        # 下载PDF文件
        if not os.path.exists(pdf_file_path):
            retry_count = 3
            while retry_count > 0:
                if download_pdf(pdf_url, pdf_file_path):
                    break
                else:
                    retry_count -= 1
            if retry_count == 0:
                logging.error(f"下载失败：{pdf_url}")
                return

        # 转换PDF文件为TXT文件
        with pdfplumber.open(pdf_file_path) as pdf:
            with open(txt_file_path, 'w', encoding='utf-8') as f:
                for page in pdf.pages:
                    
                    page_height = page.height
                    page_width = page.width
                    top_margin = 80
                    bottom_margin = 65
                    # 生成一个裁剪区域（bounding box: (x0, top, x1, bottom)）
                    cropped_page = page.crop((0, top_margin, page_width, page_height - bottom_margin))
                    
                    text = cropped_page.extract_text()
                    f.write(text)

        logging.info(f"{txt_file_path} 已保存.")

    except Exception as e:
        logging.error(f"处理 {code:06}_{name}_{year}时出错： {e}")
    else:
        # 删除已转换的PDF文件，以节省空间
        if flag_pdf:
            os.remove(pdf_file_path)
            logging.info(f"{pdf_file_path} 已被删除.")

def process_stock_reports(stock_code, csv_file, delete_pdf=True):
    """
    处理指定股票代码的年报
    :param stock_code: 股票代码
    :param csv_file: 年报汇总CSV文件路径
    :param delete_pdf: 是否在转换后删除PDF文件
    """
    # 设置日志格式
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    # 确保结果目录存在
    results_dir = os.path.dirname(csv_file)
    pdf_dir = os.path.join(results_dir, 'pdf_reports')
    txt_dir = os.path.join(results_dir, 'txt_reports')
    os.makedirs(pdf_dir, exist_ok=True)
    os.makedirs(txt_dir, exist_ok=True)

    try:
        # 读取CSV文件
        df = pd.read_csv(csv_file)
        
        # 过滤指定股票的记录
        stock_reports = df[df['公司代码'] == int(stock_code)]
        
        if stock_reports.empty:
            logging.error(f"未找到股票代码 {stock_code} 的年报记录")
            return
        
        # 处理每个年报
        for _, row in stock_reports.iterrows():
            code = row['公司代码']
            name = row['公司简称']
            year = row['年份']
            pdf_url = row['年报链接']
            
            logging.info(f"开始处理 {code} {name} {year}年报...")
            convert(code, name, year, pdf_url, pdf_dir, txt_dir, delete_pdf)
            
    except Exception as e:
        logging.error(f"处理过程中出错: {e}")

if __name__ == '__main__':
    # 测试代码
    csv_file = os.path.join('results', '2015_2025_年报汇总.csv')
    
    # 测试处理单个股票的年报
    test_stock_code = '002594'
    process_stock_reports(test_stock_code, csv_file, delete_pdf=False)