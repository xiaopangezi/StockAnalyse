#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试运行脚本
提供多种方式运行测试的入口点
"""

import sys
import os
import subprocess
import argparse

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def run_unittest():
    """使用unittest运行测试"""
    print("🚀 使用unittest运行测试...")
    
    # 导入并运行测试
    from test_pdf_parser import run_tests
    return run_tests()


def run_pytest():
    """使用pytest运行测试"""
    print("🚀 使用pytest运行测试...")
    
    try:
        # 检查是否安装了pytest
        import pytest
        print("✅ pytest已安装")
        
        # 运行pytest
        test_dir = os.path.dirname(os.path.abspath(__file__))
        result = subprocess.run([
            sys.executable, "-m", "pytest", 
            test_dir, 
            "-v", 
            "--tb=short"
        ], capture_output=True, text=True)
        
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        
        return result.returncode == 0
        
    except ImportError:
        print("❌ pytest未安装，请运行: pip install pytest")
        return False


def run_specific_test(test_name):
    """运行特定的测试"""
    print(f"🚀 运行特定测试: {test_name}")
    
    try:
        import pytest
        test_dir = os.path.dirname(os.path.abspath(__file__))
        result = subprocess.run([
            sys.executable, "-m", "pytest", 
            test_dir, 
            "-k", test_name,
            "-v"
        ], capture_output=True, text=True)
        
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        
        return result.returncode == 0
        
    except ImportError:
        print("❌ pytest未安装，请运行: pip install pytest")
        return False


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="运行PDF解析器测试")
    parser.add_argument(
        "--runner", 
        choices=["unittest", "pytest"], 
        default="unittest",
        help="选择测试运行器 (默认: unittest)"
    )
    parser.add_argument(
        "--test", 
        type=str,
        help="运行特定的测试（仅pytest支持）"
    )
    
    args = parser.parse_args()
    
    print("🧪 PDF解析器测试套件")
    print("=" * 50)
    
    if args.runner == "unittest":
        success = run_unittest()
    elif args.runner == "pytest":
        if args.test:
            success = run_specific_test(args.test)
        else:
            success = run_pytest()
    else:
        print(f"❌ 不支持的测试运行器: {args.runner}")
        return 1
    
    print("\n" + "=" * 50)
    if success:
        print("✅ 测试运行完成")
        return 0
    else:
        print("❌ 测试运行失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
