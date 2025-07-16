"""
strategies.py

实现股票筛选策略：
1. 资产负债率 > 50%
2. 净资产收益率 > 15%
3. 销售毛利率 > 30%
4. 销售净利率 > 10%
5. 自由现金流为正
6. 主营利润比率 > 70%
"""

import pandas as pd
from stock_data_fetcher import (
    get_stock_list,
    get_financial_abstract,
    get_cash_flow,
    get_financial_indicator
)

def analyze_stock(stock_code, exchange):
    """
    分析单个股票的财务数据
    
    Args:
        stock_code (str): 股票代码
        exchange (str): 交易所代码
    
    Returns:
        dict or None: 符合条件的股票信息，不符合则返回None
    """
    try:
        
        # 1. 获取财务报表数据
        abstract_data = get_financial_abstract(stock_code)
        if abstract_data is None or abstract_data.empty:
            print(f"{stock_code}: 获取财务报表数据失败")
            return None
        # 获取最近5年的数据
        # 由于数据按时间倒序排列，取最后5行即为最近5年
        recent_5_years = abstract_data.tail(5)
        
        # 检查每年的净资产收益率是否都大于15%
        for _, year_data in recent_5_years.iterrows():
            try:
                roe = float(year_data['净资产收益率-摊薄'].strip('%')) # 去掉百分号后再转换为浮点数
                if roe <= 15:
                    print(f"{stock_code}: 净资产收益率 {roe}% <= 15%")
                    return None
            except (ValueError, TypeError):
                # 数据转换失败时返回None
                print(f"{stock_code}: 净资产收益率数据转换失败")
                return None
            
        # 获取最新一年的数据
        # 获取最新一年的数据（数据按时间倒序排列，最后一行是最新数据）
        latest_abstract = abstract_data.iloc[-1]
        
        # 检查财务指标
        if not (
            float(latest_abstract['资产负债率'].strip('%')) < 50 and
            float(latest_abstract['销售毛利率'].strip('%')) > 30 and
            float(latest_abstract['销售净利率'].strip('%')) > 10
        ):
            print(f"{stock_code}: 财务指标不符合要求 - 资产负债率:{latest_abstract['资产负债率']}, 销售毛利率:{latest_abstract['销售毛利率']}, 销售净利率:{latest_abstract['销售净利率']}")
            return None
            
        # 2. 获取现金流量表数据
        cash_flow_data = get_cash_flow(stock_code)
        if cash_flow_data is None or cash_flow_data.empty:
            print(f"{stock_code}: 获取现金流量表数据失败")
            return None
            
        # 获取最新一年的数据
        latest_cash_flow = cash_flow_data.iloc[0]
                
        operating_cash_flow = convert_to_float(latest_cash_flow['经营活动产生的现金流量净额'])
        investment_cash_flow = convert_to_float(latest_cash_flow['购建固定资产、无形资产和其他长期资产支付的现金'])
        free_cash_flow = operating_cash_flow - investment_cash_flow
        
        if free_cash_flow <= 0:
            print(f"{stock_code}: 自由现金流为负 ({free_cash_flow})")
            return None
            
        # 3. 获取财务分析指标
        indicator_data = get_financial_indicator(stock_code, start_year='2020')
        if indicator_data is None or indicator_data.empty:
            print(f"{stock_code}: 获取财务分析指标数据失败")
            return None
            
        # 获取最新一年的数据
        latest_indicator = indicator_data.iloc[-1]
        
        # 检查主营利润比率
        if float(latest_indicator['主营利润比重']) <= 70:
            print(f"{stock_code}: 主营利润比重 {latest_indicator['主营利润比重']}% <= 70%")
            return None
            
        # 收集符合条件的股票信息
        return {
            'stock_code': stock_code,
            'exchange': exchange,
            'asset_liability_ratio': latest_abstract['资产负债率'],
            'roe': latest_abstract['净资产收益率'],
            'gross_profit_margin': latest_abstract['销售毛利率'],
            'net_profit_margin': latest_abstract['销售净利率'],
            'free_cash_flow': free_cash_flow,
            'main_business_ratio': latest_indicator['主营利润比重']
        }
        
    except Exception as e:
        print(f"分析股票 {stock_code} 时出错: {str(e)}")
        return None


# 计算自由现金流
# 处理带单位（万、亿）的金额字符串，转换为浮点数
def convert_to_float(amount_str):
    
    # 处理带"万"的数字
    if '万' in amount_str:
        return float(amount_str.replace('万', '')) * 10000
    # 处理带"亿"的数字    
    elif '亿' in amount_str:
        return float(amount_str.replace('亿', '')) * 100000000
    # 处理纯数字
    else:
        return float(amount_str)


def screen_stocks(output_file='results/screened_stocks.csv'):
    """
    筛选所有符合条件的股票
    
    Args:
        output_file (str): 输出文件名
    """
    # 获取所有股票列表
    stocks_df, _ = get_stock_list(exclude_st=True)
    
    # 存储符合条件的股票
    qualified_stocks = []
    
    # 遍历所有股票
    total_stocks = len(stocks_df)
    for idx, (code, row) in enumerate(stocks_df.iterrows(), 1):
        print(f"\r处理进度: {idx}/{total_stocks} ({idx/total_stocks*100:.2f}%)", end='')
        
        # 分析股票
        result = analyze_stock(code, row['exchange'])
        if result:
            qualified_stocks.append(result)
    
    print("\n筛选完成!")
    
    # 保存结果
    if qualified_stocks:
        df_result = pd.DataFrame(qualified_stocks)
        df_result.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"符合条件的股票数量: {len(qualified_stocks)}")
        print(f"结果已保存至: {output_file}")
    else:
        print("没有找到符合条件的股票。")

if __name__ == '__main__':
    # 运行股票筛选
    # screen_stocks() 
    
    result = analyze_stock('834950', 'BJ')
    print(result)
    
    # abstract_data = get_financial_abstract('430017')
    # print(abstract_data)