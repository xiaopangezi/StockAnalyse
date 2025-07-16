"""
main.py

主程序入口
使用策略模式实现股票筛选

使用：
uv venv --python 3.11 .venv 指定python版本并创建虚拟环境
source .venv/bin/activate 开启python虚拟环境
uv pip install -r pyproject.toml 安装依赖
uv pip install 添加依赖

which python 验证虚拟环境是否正确

deactivate 关闭python虚拟环境

python main.py 运行程序

"""

from stock_data_fetcher import (
    get_stock_list,
    get_financial_data,
    save_results
)
from strategies import ConservativeStrategy

def main():
    # 获取股票列表
    stocks, stock_codes = get_stock_list(exclude_st=True)
    
    if not stock_codes:
        print("未获取到股票列表，请检查网络连接")
        return
    
    # 创建策略实例
    strategy = ConservativeStrategy(years=5)
    
    # 存储筛选结果
    results = []
    
    # 对每只股票进行筛选
    for code in stock_codes:
        print(f"正在分析股票: {code}")
        # 获取财务数据
        df = get_financial_data(code)
        # 检查是否成功获取财务数据
        if df is None:
            print(f"跳过 {code}: 未能获取财务数据")
            continue
        # 应用策略
        if strategy.apply(df):
            # 获取股票名称
            name = stocks.loc[code]['display_name']
            # 收集结果
            row = {'code': code, 'name': name}
            if df is not None:
                row.update(df.iloc[0].to_dict())
            results.append(row)
    
    # 保存结果
    save_results(results)

if __name__ == '__main__':
    main() 