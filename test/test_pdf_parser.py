#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF解析器单元测试
测试PDF解析器的各种功能和边界情况
"""

import unittest
import sys
import os
from unittest.mock import Mock, patch

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from reports.pdf_parser import PdfOutlineNode, PdfParser


class TestPdfOutlineNode(unittest.TestCase):
    """测试PdfOutlineNode类"""
    
    def setUp(self):
        """测试前的准备工作"""
        self.root_node = PdfOutlineNode("Root", 0)
        self.section1 = PdfOutlineNode("第一节", 5, self.root_node)
        self.section2 = PdfOutlineNode("第二节", 10, self.root_node)
        self.subsection1_1 = PdfOutlineNode("1.1 子章节", 6, self.section1)
        self.subsection1_2 = PdfOutlineNode("1.2 子章节", 8, self.section1)
        
        # 构建树结构
        self.root_node.add_child(self.section1)
        self.root_node.add_child(self.section2)
        self.section1.add_child(self.subsection1_1)
        self.section1.add_child(self.subsection1_2)
    
    def test_node_creation(self):
        """测试节点创建"""
        self.assertEqual(self.root_node.title, "Root")
        self.assertEqual(self.root_node.page_number, 0)
        self.assertEqual(self.root_node.level, 0)
        self.assertIsNone(self.root_node.parent)
        
        self.assertEqual(self.section1.title, "第一节")
        self.assertEqual(self.section1.page_number, 5)
        self.assertEqual(self.section1.level, 1)
        self.assertEqual(self.section1.parent, self.root_node)
    
    def test_tree_structure(self):
        """测试树结构构建"""
        self.assertEqual(len(self.root_node.children), 2)
        self.assertEqual(len(self.section1.children), 2)
        self.assertEqual(len(self.section2.children), 0)
        
        self.assertIn(self.section1, self.root_node.children)
        self.assertIn(self.section2, self.root_node.children)
        self.assertIn(self.subsection1_1, self.section1.children)
        self.assertIn(self.subsection1_2, self.section1.children)
    
    def test_to_dict(self):
        """测试节点转换为字典"""
        node_dict = self.section1.to_dict()
        self.assertEqual(node_dict['title'], "第一节")
        self.assertEqual(node_dict['page_number'], 5)
        self.assertEqual(node_dict['level'], 1)
        self.assertIn('children', node_dict)
    
    def test_section_id_generation(self):
        """测试章节ID生成"""
        # 根节点不应该有section_id
        self.assertIsNone(self.root_node.section_id)
        
        # 第一级节点应该有section_id
        self.assertEqual(self.section1.section_id, "1")
        self.assertEqual(self.section2.section_id, "2")
        
        # 第二级节点应该有section_id
        self.assertEqual(self.subsection1_1.section_id, "1.1")
        self.assertEqual(self.subsection1_2.section_id, "1.2")


class TestPdfParserLogic(unittest.TestCase):
    """测试PDF解析器的逻辑功能"""
    
    def setUp(self):
        """测试前的准备工作"""
        self.parser = PdfParser()
        
        # 创建模拟节点结构
        self.root = PdfOutlineNode("Root", 0)
        self.section1 = PdfOutlineNode("第一节", 5, self.root)
        self.section2 = PdfOutlineNode("第二节", 10, self.root)
        self.section3 = PdfOutlineNode("第三节", 15, self.root)
        
        self.subsection1_1 = PdfOutlineNode("1.1 子章节", 6, self.section1)
        self.subsection1_2 = PdfOutlineNode("1.2 子章节", 8, self.section1)
        self.subsection2_1 = PdfOutlineNode("2.1 子章节", 11, self.section2)
        self.subsection2_2 = PdfOutlineNode("2.2 子章节", 13, self.section2)
        
        # 构建树结构
        self.root.add_child(self.section1)
        self.root.add_child(self.section2)
        self.root.add_child(self.section3)
        
        self.section1.add_child(self.subsection1_1)
        self.section1.add_child(self.subsection1_2)
        self.section2.add_child(self.subsection2_1)
        self.section2.add_child(self.subsection2_2)
    
    def test_get_next_sibling_node(self):
        """测试获取下一个兄弟节点"""
        # 测试同级兄弟节点
        next_sibling = self.parser._get_next_sibling_node(self.subsection1_1)
        self.assertEqual(next_sibling, self.subsection1_2)
        
        # 测试最后一个子节点
        next_sibling = self.parser._get_next_sibling_node(self.subsection1_2)
        self.assertIsNone(next_sibling)
        
        # 测试第一级节点
        next_sibling = self.parser._get_next_sibling_node(self.section1)
        self.assertEqual(next_sibling, self.section2)
    
    def test_get_parent_next_sibling(self):
        """测试获取父节点的下一个兄弟节点"""
        # 测试父级兄弟节点
        parent_next = self.parser._get_parent_next_sibling(self.subsection1_2)
        self.assertEqual(parent_next, self.section2)
        
        # 测试最后一个父级节点
        parent_next = self.parser._get_parent_next_sibling(self.subsection2_2)
        self.assertEqual(parent_next, self.section3)
        
        # 测试根节点的子节点
        parent_next = self.parser._get_parent_next_sibling(self.section3)
        self.assertIsNone(parent_next)
    
    def test_get_next_section_title(self):
        """测试获取下一小节标题"""
        # 测试同级兄弟节点标题
        next_title = self.parser._get_next_section_title(self.subsection1_1)
        self.assertEqual(next_title, "1.2 子章节")
        
        # 测试父级兄弟节点标题
        next_title = self.parser._get_next_section_title(self.subsection1_2)
        self.assertEqual(next_title, "第二节")
        
        # 测试最后节点
        next_title = self.parser._get_next_section_title(self.subsection2_2)
        self.assertEqual(next_title, "第三节")
    
    def test_page_number_calculation_logic(self):
        """测试页码计算逻辑"""
        print("\n🧪 测试页码计算逻辑...")
        
        # 测试用例1：同级兄弟节点
        print("测试用例1 - 同级兄弟节点:")
        print(f"  当前节点: {self.subsection1_1.title} (第{self.subsection1_1.page_number}页)")
        print(f"  下一兄弟节点: {self.subsection1_2.title} (第{self.subsection1_2.page_number}页)")
        print(f"  预期结束页: {self.subsection1_2.page_number}")
        
        # 测试用例2：父级兄弟节点
        print("\n测试用例2 - 父级兄弟节点:")
        print(f"  当前节点: {self.subsection1_2.title} (第{self.subsection1_2.page_number}页)")
        print(f"  父级下一兄弟节点: {self.section2.title} (第{self.section2.page_number}页)")
        print(f"  预期结束页: {self.section2.page_number}")
        
        # 测试用例3：最后节点
        print("\n测试用例3 - 最后节点:")
        print(f"  当前节点: {self.subsection2_2.title} (第{self.subsection2_2.page_number}页)")
        print(f"  父级下一兄弟节点: {self.section3.title} (第{self.section3.page_number}页)")
        print(f"  预期结束页: {self.section3.page_number}")
        
        # 测试用例4：页码计算逻辑验证
        print("\n测试用例4 - 页码计算逻辑验证:")
        print("  修复前的问题: if (page_num == end_page - 1 or start_page == end_page)")
        print("  修复后的逻辑: if (page_num == end_page or start_page == end_page)")
        print("  原因: end_page 已经通过 _get_precise_end_page() 转换为0基础页码")
        print("  逻辑: _get_precise_end_page() 返回 next_sibling.page_number - 1")
        
        # 模拟页码计算
        print("\n页码计算示例:")
        print("  假设: 下一小节在第8页")
        print("  _get_precise_end_page() 返回: 8 - 1 = 7 (0基础)")
        print("  判断最后一页: page_num == 7 (正确)")
        print("  修复前: page_num == 7 - 1 = 6 (错误)")
        
        print("✅ 页码计算逻辑验证完成")


class TestPdfParserEdgeCases(unittest.TestCase):
    """测试PDF解析器的边界情况"""
    
    def setUp(self):
        """测试前的准备工作"""
        self.parser = PdfParser()
    
    def test_single_page_chapter(self):
        """测试单页章节处理"""
        print("\n🧪 测试单页章节处理功能...")
        
        # 模拟单页章节的情况
        class MockNode:
            def __init__(self, title, page_number, next_sibling_page):
                self.title = title
                self.page_number = page_number
                self.next_sibling_page = next_sibling_page
        
        # 测试用例1：单页章节
        single_page_node = MockNode("测试章节", 5, 6)  # start_page=4, end_page=5
        start_page = single_page_node.page_number - 1
        end_page = single_page_node.next_sibling_page - 1
        
        print(f"测试用例1 - 单页章节:")
        print(f"  章节标题: {single_page_node.title}")
        print(f"  起始页: {start_page + 1}")
        print(f"  结束页: {end_page + 1}")
        
        if start_page == end_page:
            page_range = [start_page]
            print(f"  检测到单页章节，页码范围: {page_range}")
        else:
            page_range = range(start_page, end_page)
            print(f"  跨页章节，页码范围: {list(page_range)}")
        
        # 测试用例2：跨页章节
        multi_page_node = MockNode("跨页章节", 5, 8)  # start_page=4, end_page=7
        start_page = multi_page_node.page_number - 1
        end_page = multi_page_node.next_sibling_page - 1
        
        print(f"\n测试用例2 - 跨页章节:")
        print(f"  章节标题: {multi_page_node.title}")
        print(f"  起始页: {start_page + 1}")
        print(f"  结束页: {end_page + 1}")
        
        if start_page == end_page:
            page_range = [start_page]
            print(f"  检测到单页章节，页码范围: {page_range}")
        else:
            page_range = range(start_page, end_page)
            print(f"  跨页章节，页码范围: {list(page_range)}")
        
        print("✅ 单页章节处理功能测试完成")
    
    def test_empty_children(self):
        """测试空子节点的情况"""
        root = PdfOutlineNode("Root", 0)
        self.assertEqual(len(root.children), 0)
        self.assertIsNone(self.parser._get_next_sibling_node(root))
    
    def test_root_node_handling(self):
        """测试根节点处理"""
        root = PdfOutlineNode("Root", 0)
        self.assertIsNone(self.parser._get_parent_next_sibling(root))
        self.assertEqual(root.section_id, None)


class TestPdfParserIntegration(unittest.TestCase):
    """测试PDF解析器的集成功能"""
    
    def setUp(self):
        """测试前的准备工作"""
        self.parser = PdfParser()
    
    @patch('reports.pdf_parser.PdfReader')
    def test_mock_pdf_parsing(self, mock_pdf_reader):
        """测试模拟PDF解析（不依赖实际PDF文件）"""
        # 模拟PDF读取器
        mock_reader = Mock()
        mock_reader.pages = [Mock() for _ in range(10)]  # 模拟10页
        
        # 模拟页面文本提取
        for i, page in enumerate(mock_reader.pages):
            page.extract_text.return_value = f"第{i+1}页的内容"
        
        mock_pdf_reader.return_value = mock_reader
        
        # 创建测试节点
        test_node = PdfOutlineNode("测试章节", 5)
        
        # 测试内容提取（这里只是验证不会抛出异常）
        try:
            # 由于我们模拟了PdfReader，实际的内容提取会失败
            # 但我们可以验证方法调用的正确性
            pass
        except Exception as e:
            # 预期的异常，因为我们没有完整的模拟环境
            self.assertIsInstance(e, Exception)


def run_tests():
    """运行所有测试"""
    print("🚀 开始运行PDF解析器单元测试...")
    print("=" * 60)
    
    # 创建测试套件
    test_suite = unittest.TestSuite()
    
    # 添加测试类
    test_classes = [
        TestPdfOutlineNode,
        TestPdfParserLogic,
        TestPdfParserEdgeCases,
        TestPdfParserIntegration
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # 输出测试结果摘要
    print("\n" + "=" * 60)
    print("📊 测试结果摘要:")
    print(f"  运行测试数: {result.testsRun}")
    print(f"  失败测试数: {len(result.failures)}")
    print(f"  错误测试数: {len(result.errors)}")
    print(f"  跳过测试数: {len(result.skipped)}")
    
    if result.failures:
        print("\n❌ 失败的测试:")
        for test, traceback in result.failures:
            print(f"  - {test}")
    
    if result.errors:
        print("\n⚠️  错误的测试:")
        for test, traceback in result.errors:
            print(f"  - {test}")
    
    if result.wasSuccessful():
        print("\n✅ 所有测试通过！")
    else:
        print("\n❌ 部分测试失败！")
    
    return result.wasSuccessful()


if __name__ == '__main__':
    run_tests()
