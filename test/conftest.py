#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试配置文件
配置pytest测试环境和共享的fixture
"""

import pytest
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(scope="session")
def project_root():
    """返回项目根目录路径"""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture(scope="session")
def test_data_dir():
    """返回测试数据目录路径"""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


@pytest.fixture(scope="function")
def mock_pdf_reader():
    """模拟PDF读取器"""
    from unittest.mock import Mock
    
    mock_reader = Mock()
    mock_reader.pages = [Mock() for _ in range(10)]  # 模拟10页
    
    # 模拟页面文本提取
    for i, page in enumerate(mock_reader.pages):
        page.extract_text.return_value = f"第{i+1}页的内容"
    
    return mock_reader
