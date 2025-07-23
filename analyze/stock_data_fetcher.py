"""
stock_data_fetcher.py

使用AKShare获取股票数据的工具函数集合：
1. 获取A股列表
2. 获取同花顺财务报表数据
3. 获取同花顺现金流量表数据
4. 获取财务分析指标数据
5. 获取股票详细信息
"""

import os
from datetime import datetime
import akshare as ak
import pandas as pd

def process_stock_df(df, exchange):
    """
    处理股票数据，统一格式
    
    Args:
        df (pandas.DataFrame): 原始股票数据
        exchange (str): 交易所标识
    
    Returns:
        pandas.DataFrame: 处理后的数据
    """
    if df.empty:
        return pd.DataFrame(columns=['code', 'name'])
        
    # Create a copy of the DataFrame to avoid SettingWithCopyWarning
    df = df.copy()
    
    # 统一列名
    # 北交所: code, company_name
    # 上交所: 证券代码, 证券简称
    # 深交所: A股代码, A股简称
    if '证券代码' in df.columns:
        df = df[['证券代码', '证券简称']]
        df.columns = ['code', 'name']
    elif 'A股代码' in df.columns:
        df = df[['A股代码', 'A股简称']]
        df.columns = ['code', 'name']
    else:
        df = df[['code', 'company_name']]
        df.columns = ['code', 'name']
    
    # 添加交易所信息
    df['exchange'] = exchange
    
    return df

def get_stock_list(exclude_st=True):
    """
    获取A股股票列表（包含北京、上海、深圳三个交易所）
    
    Args:
        exclude_st (bool): 是否排除ST股票
    
    Returns:
        tuple: (stock_df, stock_codes)
        - stock_df: 包含股票基本信息的DataFrame
        - stock_codes: 股票代码列表
    """
    try:
        # 获取北交所股票列表
        bj_stocks = ak.stock_info_bj_name_code()
        bj_stocks = process_stock_df(bj_stocks, 'BJ')
        
        # 获取上交所股票列表
        sh_stocks = ak.stock_info_sh_name_code()
        sh_stocks = process_stock_df(sh_stocks, 'SH')
        
        # 获取深交所股票列表
        sz_stocks = ak.stock_info_sz_name_code()
        sz_stocks = process_stock_df(sz_stocks, 'SZ')
        
        # 合并所有股票信息
        all_stocks = pd.concat([bj_stocks, sh_stocks, sz_stocks], ignore_index=True)
        
        if exclude_st:
            # 排除ST股票
            all_stocks = all_stocks[~all_stocks['name'].str.contains('ST', na=False)]
        
        # 添加完整的股票代码（带交易所标识）
        all_stocks['full_code'] = all_stocks.apply(
            lambda x: f"{x['code']}.{x['exchange']}", axis=1
        )
        
        # 重命名name列为display_name以保持一致性
        all_stocks.rename(columns={'name': 'display_name'}, inplace=True)
        
        # 获取股票代码列表
        stock_codes = all_stocks['code'].tolist()
        
        # 设置code为索引 (在获取代码列表后再设置索引)
        all_stocks.set_index('code', inplace=True)
        
        return all_stocks, stock_codes
        
    except Exception as e:
        print(f"获取股票列表时出错: {str(e)}")
        return pd.DataFrame(), []

def get_financial_abstract(stock_code):
    """
    获取同花顺财务报表数据
    
    Args:
        stock_code (str): 股票代码（如：600519）
    
    Returns:
        pandas.DataFrame: 财务报表数据
    """
    try:
        # 获取年度财务报表数据
        df = ak.stock_financial_abstract_ths(symbol=stock_code, indicator="按年度")
        return df
    except Exception as e:
        print(f"获取 {stock_code} 财务报表数据时出错: {str(e)}")
        return None

def get_cash_flow(stock_code):
    """
    获取同花顺现金流量表数据
    
    Args:
        stock_code (str): 股票代码（带市场标识，如：SH600519）
    
    Returns:
        pandas.DataFrame: 现金流量表数据
    """
    try:
        # 获取年度现金流量表数据
        df = ak.stock_financial_cash_ths(symbol=stock_code, indicator="按年度")
        return df
    except Exception as e:
        print(f"获取 {stock_code} 现金流量表数据时出错: {str(e)}")
        return None

def get_financial_indicator(stock_code, start_year='2020'):
    """
    获取财务分析指标数据
    
    Args:
        stock_code (str): 股票代码（不带市场标识）
    
    Returns:
        pandas.DataFrame: 财务分析指标数据
    """
    try:
        # 获取财务分析指标数据
        df = ak.stock_financial_analysis_indicator(symbol=stock_code, start_year=start_year)
        return df
    except Exception as e:
        print(f"获取 {stock_code} 财务分析指标数据时出错: {str(e)}")
        return None

def get_stock_detail(stock_code: str) -> pd.DataFrame:
    """
    获取股票的详细信息（包括公司概况、融资融券、行业分类等信息）
    
    Args:
        stock_code (str): 股票代码（如：600519）
        
    Returns:
        pandas.DataFrame: 包含股票详细信息的DataFrame，具体字段包括：
            - 总市值
            - 流通市值
            - 行业
            - 上市时间
            - 股票代码
            - 股票简称
            - 总股本
            - 流通股
            - 员工人数
            - 主营业务
            - 公司简介
            等...
            
    Example:
        >>> detail = get_stock_detail('600519')
        >>> print(detail)
    """
    try:
        # 获取股票详细信息
        df = ak.stock_individual_info_em(symbol=stock_code)
        
        if df is not None and not df.empty:
            # 将DataFrame的index转换为列名，values转换为对应的值
            df = df.reset_index()
            df.columns = ['指标', '值']
            
            # 转换为字典格式，方便使用
            info_dict = dict(zip(df['指标'], df['值']))
            
            # 创建一个单行的DataFrame
            result_df = pd.DataFrame([info_dict])
            
            return result_df
        else:
            print(f"未找到股票 {stock_code} 的详细信息")
            return pd.DataFrame()
            
    except Exception as e:
        print(f"获取股票 {stock_code} 详细信息时出错: {str(e)}")
        return pd.DataFrame()

# 测试代码
if __name__ == '__main__':
    # 测试用的股票代码 - 贵州茅台(SH600519)
    test_code = 'SH600519'
    print(f"\n测试获取 {test_code} 的财务数据:")
    
    # 测试获取财务报表数据
    print("\n1. 测试获取财务报表数据:")
    abstract_data = get_financial_abstract(test_code)
    if abstract_data is not None:
        print("财务报表数据形状:", abstract_data.shape)
        print("财务报表指标:", abstract_data.columns.tolist())
    
    # 测试获取现金流量表数据
    print("\n2. 测试获取现金流量表数据:")
    cash_flow_data = get_cash_flow(test_code)
    if cash_flow_data is not None:
        print("现金流量表数据形状:", cash_flow_data.shape)
        print("现金流量表指标:", cash_flow_data.columns.tolist())
    
    # 测试获取财务分析指标数据
    print("\n3. 测试获取财务分析指标数据:")
    indicator_data = get_financial_indicator(test_code.replace('SH', ''))
    if indicator_data is not None:
        print("财务分析指标数据形状:", indicator_data.shape)
        print("财务分析指标:", indicator_data.columns.tolist())
        
    # 测试获取股票详细信息
    print("\n4. 测试获取股票详细信息:")
    detail_data = get_stock_detail(test_code.replace('SH', ''))
    if not detail_data.empty:
        print("股票详细信息:")
        for column in detail_data.columns:
            print(f"{column}: {detail_data[column].iloc[0]}")
