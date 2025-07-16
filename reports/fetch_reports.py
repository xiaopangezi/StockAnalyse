'''
@Project ：PycharmProjects
@File    ：巨潮资讯年报2.0.py
@IDE     ：PyCharm
@Author  ：lingxiaotian
@Date    ：2023/5/20 12:38
'''

import requests
import re
import time
import pandas as pd
import os
import logging

# 全局变量声明
counter = 0
sum = 0

# 确保results文件夹存在
def ensure_results_dir():
    """确保results文件夹存在，如果不存在则创建"""
    # 获取当前文件所在目录的上一级目录，并在其中找到results文件夹
    results_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'results')
    if not os.path.exists(results_dir):
        os.makedirs(results_dir)
    return results_dir

def get_report(page_num,date):
    url = "http://www.cninfo.com.cn/new/hisAnnouncement/query"
    headers = {
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
        "Content-Length": "195",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Host": "www.cninfo.com.cn",
        "Origin": "http://www.cninfo.com.cn",
        "Proxy-Connection": "keep-alive",
        "Referer": "http://www.cninfo.com.cn/new/commonUrl/pageOfSearch?url=disclosure/list/search&checkedCategory=category_ndbg_szsh",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36 Edg/113.0.1774.42",
        "X-Requested-With": "XMLHttpRequest"
    }
    data = {
        "pageNum": page_num,
        "pageSize": 30,
        "column": "szse",
        "tabName": "fulltext",
        "plate": plate,
        "searchkey": "",
        "secid": "",
        "category": "category_ndbg_szsh",
        "trade": trade,
        "seDate": date,
        "sortName": "code",
        "sortType": "asc",
        "isHLtitle": "false"
    }
    response = requests.post(url, data=data, headers=headers)
    return response

def download_report(date):
    global counter  # 声明使用全局变量
    all_results = []
    page_num = 1
    response_test = get_report(page_num, date)

    try:
        data_test = response_test.json()
        total_pages = data_test["totalpages"]

        if total_pages == 0:
            return all_results

    except (ValueError, KeyError) as e:
        print(f"获取总页数失败: {e}")
        return all_results

    max_retries = 3

    while page_num <= total_pages+1:
        retry_count = 0
        while retry_count <= max_retries:
            try:
                response = get_report(page_num, date)
                response.raise_for_status()
                data = response.json()

                if data["announcements"] is None:
                    break
                else:
                    all_results.extend(data["announcements"])

                if total_pages > 0:
                    per = (counter / total_pages)
                    if per < 1:
                        print(f"\r当前年份下载进度 {per * 100:.2f} %", end='')
                    else:
                        print(f"\r下载完成，正在保存……", end='')
                else:
                    print("无法计算下载进度，总页数为0。")

                break

            except requests.exceptions.RequestException as e:
                print(f"出现网络请求错误！: {e}")
                print(f"5秒后重试...")
                time.sleep(5)
                retry_count += 1

            except (ValueError, KeyError) as e:
                print(f"解析响应数据失败: {e}")
                print(f"5秒后重试...")
                time.sleep(5)
                retry_count += 1

            if retry_count > max_retries:
                print(f"{max_retries}次重试后均失败. 跳过第{page_num}页.")
                break

        page_num += 1
        counter += 1

    return all_results

def process_year_data(year):
    global sum, counter  # 声明使用全局变量
    # 计数器
    date_count = f"{year}-01-01~{year}-12-31"
    response = get_report(1,date_count)
    data = response.json()
    sum = data["totalpages"]

    year = year+1
    all_results = []
    time_segments = [
        f"{year}-01-01~{year}-04-01",
        f"{year}-04-02~{year}-04-15",
        f"{year}-04-16~{year}-04-22",
        f"{year}-04-23~{year}-04-26",
        f"{year}-04-27~{year}-04-28",
        f"{year}-04-29~{year}-04-30",
        f"{year}-05-01~{year}-07-31",
        f"{year}-08-01~{year}-10-31",
        f"{year}-11-01~{year}-11-30",
        f"{year}-12-01~{year}-12-31"
    ]
    for i in time_segments:
        results = download_report(i)
        all_results.extend(results)

    # 处理年度数据并返回DataFrame
    year_data = []
    for item in all_results:
        company_code = item["secCode"]
        company_name = item["secName"]
        title = item["announcementTitle"].strip()
        title = re.sub(r"<.*?>", "", title)
        title = title.replace("：", "")
        title = f"《{title}》"

        adjunct_url = item["adjunctUrl"]
        report_year = re.search(r"(\d{4})年", title)
        if report_year:
            report_year = report_year.group(1)
        else:
            report_year = str(year-1)  # 使用实际年份
        announcement_url = f"http://static.cninfo.com.cn/{adjunct_url}"

        # 检查排除关键词
        exclude_flag = False
        for keyword in exclude_keywords:
            if keyword in title:
                exclude_flag = True
                break

        if not exclude_flag:
            year_data.append({
                "公司代码": company_code,
                "公司简称": company_name,
                "标题": title,
                "年份": report_year,
                "年报链接": announcement_url
            })

    return pd.DataFrame(year_data)

def main(start_year, end_year):
    global counter  # 声明使用全局变量
    # 存储所有年份的数据
    all_years_data = []
    
    # 获取每年的数据
    for year in range(start_year, end_year):
        counter = 1  # 重置计数器
        print(f"\n开始下载 {year} 年的数据...")
        year_df = process_year_data(year)
        all_years_data.append(year_df)
        print(f"\n{year}年数据下载完成")

    # 合并所有年份的数据
    if all_years_data:
        combined_df = pd.concat(all_years_data, ignore_index=True)
        
        # 按公司代码和年份排序
        combined_df = combined_df.sort_values(by=['公司代码', '年份'], ascending=[True, False])
        
        # 确保results文件夹存在
        results_dir = ensure_results_dir()
        
        # 构建输出文件路径
        output_file = os.path.join(results_dir, f'{start_year}_{end_year}_年报汇总.csv')
        
        # 保存到CSV
        combined_df.to_csv(output_file, index=False, encoding='utf-8-sig')
            
        print(f"\n所有数据已合并保存到 {output_file}")
    else:
        print("\n没有找到任何数据")

if __name__ == '__main__':
    # 排除列表
    exclude_keywords = ['英文','已取消','摘要']
    # 行业控制
    trade = ""
    # 板块控制：深市sz 沪市sh 深主板szmb 沪主板shmb 创业板szcy 科创板shkcp 北交所bj
    plate = "sz;sh"
    
    # 设置下载年份范围
    start_year = 2015
    end_year = 2025
    
    # 运行主程序
    main(start_year, end_year)