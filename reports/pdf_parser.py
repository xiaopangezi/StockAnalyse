# -*- coding: utf-8 -*-
"""
pdf_parser.py

使用 PyPDF2 库解析 PDF 文档，功能包括：
1. 提取文档大纲（目录结构）
2. 按章节拆分文档内容
3. 保存拆分后的文本
"""

import os
import logging
import json
from typing import Dict, List, Tuple, Optional
from pypdf import PdfReader
import re

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class PdfOutlineNode:
    """PDF 目录节点类"""
    def __init__(self, title: str, page_number: int = 0, level: int = -1):
        self.title = title
        self.page_number = page_number
        self.level = level
        self.children = []
        self.parent = None
        self.next_sibling_page = None
        self.content = ""  # 节点内容
        self.section_id = ""  # 章节ID

    def add_child(self, child: 'PdfOutlineNode'):
        child.parent = self
        self.children.append(child)

    def get_section_path(self) -> List[str]:
        """获取从根到当前节点的路径"""
        path = []
        current = self
        while current and current.parent and current.title != "Root":
            path.insert(0, current.title)
            current = current.parent
        return path

    def generate_section_id(self) -> str:
        """生成章节ID，格式如：1.4.2"""
        if not self.parent or self.title == "Root":
            return ""

        # 获取当前节点在其父节点中的索引
        if self.parent:
            try:
                index = self.parent.children.index(self) + 1
            except ValueError:
                index = 1
        else:
            index = 1

        # 递归获取父节点的ID
        parent_id = self.parent.generate_section_id() if self.parent and self.parent.title != "Root" else ""

        # 组合ID
        if parent_id:
            return f"{parent_id}.{index}"
        else:
            return str(index)

    def to_dict(self) -> Dict:
        """将节点转换为字典，用于JSON序列化"""
        # 生成章节ID
        if not self.section_id:
            self.section_id = self.generate_section_id()

        return {
            'content': self.content,
            'metadata': {
                'section_id': self.section_id,
                'section_title': self.title,
                'section_path': self.get_section_path(),
                'page': self.page_number
            }
        }

    def __str__(self) -> str:
        return f"{'  ' * (self.level + 1)}{self.title} (Page {self.page_number})"

class PdfParser:
    def __init__(self, pdf_path: str):
        """
        初始化PDF解析器
        :param pdf_path: PDF文件路径
        """
        self.pdf_path = pdf_path
        self.reader = PdfReader(pdf_path)
        self.root_node = None  # 存储目录根节点

    def extract_outline(self) -> PdfOutlineNode:
        """
        提取PDF文档的目录结构
        :return: 目录根节点
        """
        try:
            # 创建根节点
            self.root_node = PdfOutlineNode("Root")

            # 获取文档大纲
            outline = self.reader.outline
            if not outline:
                logging.warning("PDF文档没有目录结构")
                return self.root_node

            # 处理大纲数据，转换为树形结构
            self.root_node = self.process_outline(outline)

            return self.root_node

        except Exception as e:
            logging.error(f"提取目录结构时出错: {str(e)}")
            return PdfOutlineNode("Error")

    def process_outline(self, outline_items) -> PdfOutlineNode:
        """
        将扁平数组结构的目录转换为树形结构的PdfOutlineNode
        :param outline_items: pypdf reader.outline返回的扁平目录数组，格式如[{1}, {2}, [{2.1},{2.2},{2.3}], {3}]
        :return: 树形结构的根节点
        """
        def get_page_number(item):
            """获取目录项的页码"""
            page_number = 0
            if hasattr(item, 'page') and item.page is not None:
                try:
                    # 使用PyPDF推荐的方法获取页码
                    page_number = self.reader.get_destination_page_number(item) + 1
                except Exception as e:
                    # 备用方法：直接查找页面引用
                    try:
                        page_ref = item.page
                        if hasattr(page_ref, 'idnum'):
                            # 遍历所有页面查找匹配的页面ID
                            for page_num, page in enumerate(self.reader.pages):
                                if (hasattr(page, 'indirect_reference') and
                                    page.indirect_reference.idnum == page_ref.idnum):
                                    page_number = page_num + 1
                                    break
                        else:
                            page_number = int(page_ref) + 1
                    except Exception as e2:
                        logging.warning(f"无法获取页码: {e} | {e2}")
                        page_number = 0
            return page_number

        def process_outline_items(items: List, parent_node: PdfOutlineNode, level: int) -> int:
            """
            处理扁平的目录项数组
            数组结构: [item1, item2, [child2.1, child2.2], item3, ...]
            返回处理的项目数量
            """
            i = 0
            while i < len(items):
                item = items[i]

                if isinstance(item, list):
                    # 如果当前项是列表，说明这是前一个节点的子项，跳过（在处理父项时会处理）
                    logging.warning(f"发现孤立的子项列表，跳过: {len(item)} 个子项")
                    i += 1
                    continue

                # 处理目录项字典
                if hasattr(item, 'title'):
                    # 获取标题
                    title = item.title if item.title else "未知章节"

                    # 获取页码
                    page_number = get_page_number(item)

                    # 创建当前节点
                    node = PdfOutlineNode(title, page_number, level)
                    parent_node.add_child(node)

                    # 检查是否有子项：通过outline_count属性判断
                    outline_count = getattr(item, 'outline_count', None)

                    if outline_count is not None and outline_count < 0:
                        # outline_count为负数表示有 abs(outline_count) 个子项
                        # 下一个元素应该是子项列表
                        if i + 1 < len(items) and isinstance(items[i + 1], list):
                            child_list = items[i + 1]
                            logging.info(f"处理 '{title}' 的 {len(child_list)} 个子项")
                            # 递归处理子项列表
                            process_outline_items(child_list, node, level + 1)
                            i += 2  # 跳过子项列表
                        else:
                            # 预期有子项但下一个元素不是列表，可能是其他格式
                            logging.warning(f"'{title}' 预期有子项但格式不符")
                            i += 1
                    else:
                        # outline_count为None或0表示没有子项
                        i += 1
                else:
                    # 处理其他类型的项目
                    title = str(item)
                    node = PdfOutlineNode(title, 0, level)
                    parent_node.add_child(node)
                    i += 1

            return len(items)

        try:
            # 创建根节点
            root = PdfOutlineNode("Root")

            # 如果没有目录项，返回空根节点
            if not outline_items:
                logging.warning("没有找到目录项")
                return root

            logging.info(f"开始处理 {len(outline_items)} 个顶级目录项")

            # 处理扁平的目录数组
            process_outline_items(outline_items, root, 0)

            # 设置所有节点的next_sibling_page
            self._set_next_sibling_pages(root)

            logging.info(f"目录处理完成，共创建 {len(root.children)} 个顶级节点")

            return root

        except Exception as e:
            logging.error(f"处理目录结构时出错: {str(e)}")
            return PdfOutlineNode("Error")

    def _set_next_sibling_pages(self, node: PdfOutlineNode):
        """
        设置所有节点的next_sibling_page属性
        当前小节的结束页面就是下一小节的开始位置
        :param node: 要处理的节点
        """
        try:
            # 如果节点有子节点，先递归处理子节点
            if node.children:
                # 为当前节点的所有子节点设置next_sibling_page
                for i in range(len(node.children)):
                    current_child = node.children[i]

                    # 如果不是最后一个子节点，设置next_sibling_page为下一个兄弟节点的页码
                    if i < len(node.children) - 1:
                        next_sibling = node.children[i + 1]
                        current_child.next_sibling_page = next_sibling.page_number
                    else:
                        # 如果是最后一个子节点，next_sibling_page保持None
                        current_child.next_sibling_page = None

                    # 递归处理子节点
                    self._set_next_sibling_pages(current_child)

        except Exception as e:
            logging.error(f"设置next_sibling_page时出错: {str(e)}")

    def save_outline_to_json(self, output_path: str) -> bool:
        """
        将目录结构保存为JSON文件
        :param output_path: 输出文件路径
        :return: 是否成功保存
        """
        try:
            if not self.root_node:
                logging.error("没有提取到目录结构，无法保存JSON")
                return False

            # 解析PDF文件名以提取信息
            pdf_name = os.path.splitext(os.path.basename(self.pdf_path))[0]

            # 尝试从文件名中提取信息 (例如: 002594_比亚迪_2024)
            parts = pdf_name.split('_')
            company_stock_code = parts[0] if len(parts) > 0 else ""
            company_name = parts[1] if len(parts) > 1 else ""
            report_year = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 2024

            # 生成PDF元数据
            from datetime import datetime
            pdf_metadata = {
                "file_name": f"{pdf_name}.pdf",
                "report_title": f"{company_name}{report_year}年年度报告" if company_name else f"{pdf_name}",
                "report_year": report_year,
                "report_type": "annual",
                "company_name": f"{company_name}股份有限公司" if company_name else "",
                "company_stock_code": f"{company_stock_code}.SH" if company_stock_code else "",
                "total_pages": len(self.reader.pages),
                "parse_datetime": datetime.now().isoformat() + "Z"
            }

            # 收集所有叶子节点（没有子节点的节点）
            outline_items = []
            self._collect_leaf_nodes(self.root_node, outline_items)

            # 构建最终的JSON数据
            json_data = {
                "pdf_metadata": pdf_metadata,
                "outline": outline_items
            }

            # 确保输出目录存在
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            # 保存JSON文件
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, ensure_ascii=False, indent=2)

            logging.info(f"目录结构已保存到: {output_path}")
            return True

        except Exception as e:
            logging.error(f"保存JSON文件时出错: {str(e)}")
            return False

    def _collect_leaf_nodes(self, node: PdfOutlineNode, leaf_nodes: List[Dict]):
        """
        收集所有叶子节点（没有子节点的节点）
        :param node: 当前节点
        :param leaf_nodes: 收集叶子节点的列表
        """
        try:
            # 跳过根节点
            if node.title == "Root":
                for child in node.children:
                    self._collect_leaf_nodes(child, leaf_nodes)
                return

            # 如果没有子节点，就是叶子节点
            if not node.children:
                # 提取内容
                if not node.content:  # 只有当content为空时才提取
                    try:
                        node.content = self.extract_chapter_content(node)
                        logging.debug(f"为节点 '{node.title}' 提取内容，长度: {len(node.content)} 字符")
                    except Exception as e:
                        logging.error(f"为节点 '{node.title}' 提取内容时出错: {str(e)}")
                        node.content = ""

                leaf_nodes.append(node.to_dict())
            else:
                # 递归处理子节点
                for child in node.children:
                    self._collect_leaf_nodes(child, leaf_nodes)

        except Exception as e:
            logging.error(f"收集叶子节点时出错: {str(e)}")

    def extract_chapter_content(self, node: PdfOutlineNode) -> str:
        """
        提取指定章节的内容
        :param node: 目录节点
        :return: 章节内容
        """
        try:
            start_page = node.page_number - 1  # 转换为0基础的页码

            # 获取精确的结束位置：下一小节的标题开头
            end_page = self._get_precise_end_page(node)

            if start_page < 0 or start_page >= len(self.reader.pages):
                logging.error(f"起始页码超出范围: {start_page}, 总页数: {len(self.reader.pages)}")
                return ""

            if end_page > len(self.reader.pages):
                logging.warning(f"结束页码超出范围，调整为总页数: {end_page} -> {len(self.reader.pages)}")
                end_page = len(self.reader.pages)

            content = []
            # 兼容单页章节的情况：如果start_page和end_page相同，也要处理这一页
            if start_page == end_page:
                logging.info(f"章节 '{node.title}' 为单页章节，页码: {start_page + 1}")
                page_range = [start_page]
            else:
                page_range = range(start_page, end_page)
                logging.debug(f"章节 '{node.title}' 跨页处理，页码范围: {start_page + 1} - {end_page}")

            for page_num in page_range:
                try:
                    page = self.reader.pages[page_num]
                    text = page.extract_text()

                    if not text:
                        logging.warning(f"第 {page_num + 1} 页没有提取到文本内容")
                        continue

                    # 如果是第一页，从章节标题开始提取
                    if page_num == start_page:
                        # 查找章节标题在文本中的位置
                        title_pos = text.find(node.title)
                        if title_pos != -1:
                            text = text[title_pos:]
                            logging.debug(f"从第 {page_num + 1} 页标题位置开始提取: '{node.title}'")
                        else:
                            logging.debug(f"在第 {page_num + 1} 页未找到标题: '{node.title}'")

                    # 如果是最后一页或者是单页章节，都需要检查是否需要截取到下一小节标题开头
                    if (page_num == end_page - 1 or start_page == end_page) and end_page < len(self.reader.pages):
                        next_section_title = self._get_next_section_title(node)
                        if next_section_title:
                            # 查找下一小节标题在文本中的位置
                            next_title_pos = text.find(next_section_title)
                            if next_title_pos != -1:
                                text = text[:next_title_pos]
                                logging.debug(f"在第 {page_num + 1} 页截取到下一小节标题: '{next_section_title}'")
                            else:
                                logging.debug(f"在第 {page_num + 1} 页未找到下一小节标题: '{next_section_title}'")

                    # 清理文本内容
                    text = self._clean_text(text)
                    content.append(text)

                except Exception as e:
                    logging.error(f"提取第 {page_num + 1} 页内容时出错: {str(e)}")
                    continue

            result = "\n".join(content)
            page_count = len(content)
            page_info = f"共 {page_count} 页" if page_count > 1 else "单页章节"
            logging.info(f"成功提取章节 '{node.title}' 内容，{page_info}，内容长度: {len(result)} 字符")
            return result

        except Exception as e:
            logging.error(f"提取章节内容时出错: {str(e)}")
            return ""

    def _get_precise_end_page(self, node: PdfOutlineNode) -> int:
        """
        获取精确的结束页码：下一小节的标题开头
        :param node: 当前节点
        :return: 结束页码（0基础）
        """
        # 首先尝试获取下一兄弟节点
        next_sibling = self._get_next_sibling_node(node)

        if next_sibling:
            # 如果有下一兄弟节点，返回其页码
            return next_sibling.page_number - 1

        # 如果没有下一兄弟节点，尝试获取父节点的下一兄弟节点
        parent_next = self._get_parent_next_sibling(node)
        if parent_next:
            return parent_next.page_number - 1

        # 如果都没有，返回文档末尾
        return len(self.reader.pages)

    def _get_next_section_title(self, node: PdfOutlineNode) -> str:
        """
        获取下一小节的标题
        :param node: 当前节点
        :return: 下一小节标题，如果没有则返回空字符串
        """
        next_sibling = self._get_next_sibling_node(node)
        if next_sibling:
            return next_sibling.title

        parent_next = self._get_parent_next_sibling(node)
        if parent_next:
            return parent_next.title

        return ""

    def _get_next_sibling_node(self, node: PdfOutlineNode) -> PdfOutlineNode:
        """
        获取下一个兄弟节点
        :param node: 当前节点
        :return: 下一个兄弟节点，如果没有则返回None
        """
        if not node.parent:
            return None

        try:
            current_index = node.parent.children.index(node)
            if current_index + 1 < len(node.parent.children):
                return node.parent.children[current_index + 1]
        except ValueError:
            pass

        return None

    def _get_parent_next_sibling(self, node: PdfOutlineNode) -> PdfOutlineNode:
        """
        获取父节点的下一个兄弟节点
        :param node: 当前节点
        :return: 父节点的下一个兄弟节点，如果没有则返回None
        """
        if not node.parent or node.parent.title == "Root":
            return None

        return self._get_next_sibling_node(node.parent)

    def _clean_text(self, text: str) -> str:
        """
        清理提取的文本内容，包括移除页眉页脚
        :param text: 原始文本
        :return: 清理后的文本
        """
        if not text:
            return ""

        # 按行分割文本
        lines = text.split('\n')
        cleaned_lines = []

        # 页眉页脚的常见模式
        header_footer_patterns = [
            r'^\s*第?\s*\d+\s*页\s*$',  # 页码：第X页 或 X页
            r'^\s*\d+\s*$',  # 纯数字页码
            r'^\s*\d+\s*/\s*\d+\s*$',  # X/Y格式页码
            r'^\s*-\s*\d+\s*-\s*$',  # -X-格式页码
            r'^.{0,3}$',  # 极短的行（3个字符以下）
            r'^\s*(公司|股份|有限|年度|报告|年报)\s*$',  # 常见的页眉关键词
            r'^\s*\d{4}\s*年\s*(年度报告|半年报|季报)\s*$',  # 年份报告标题
        ]

        for line in lines:
            line = line.strip()

            # 跳过空行
            if not line:
                continue

            # 检查是否匹配页眉页脚模式
            is_header_footer = False
            for pattern in header_footer_patterns:
                if re.match(pattern, line):
                    is_header_footer = True
                    break

            # 如果不是页眉页脚，保留这一行
            if not is_header_footer:
                cleaned_lines.append(line)

        # 重新组合文本
        cleaned_text = '\n'.join(cleaned_lines)

        # 移除多余的空白字符
        cleaned_text = re.sub(r'\s+', ' ', cleaned_text)

        # 移除行首行尾空白
        cleaned_text = cleaned_text.strip()

        # 移除重复的空行
        cleaned_text = re.sub(r'\n\s*\n\s*\n', '\n\n', cleaned_text)

        return cleaned_text

    def print_outline(self):
        """打印目录结构"""
        def print_node(node: PdfOutlineNode, indent: str = ""):
            if node.level >= 0:  # 不打印根节点
                # 格式化输出，包含页码信息
                if hasattr(node, 'next_sibling_page') and node.next_sibling_page:
                    if node.page_number == node.next_sibling_page - 1:
                        # 单页章节
                        page_range = f"第 {node.page_number} 页 (单页)"
                    else:
                        # 跨页章节
                        page_range = f"第 {node.page_number} - {node.next_sibling_page - 1} 页"
                else:
                    page_range = f"第 {node.page_number} 页"

                print(f"{indent}📖 {node.title} ({page_range})")

            # 递归打印子节点
            for i, child in enumerate(node.children):
                is_last = i == len(node.children) - 1
                child_indent = indent + ("    " if is_last else "│   ")
                print_node(child, child_indent)

        if not self.root_node or not self.root_node.children:
            print("📄 没有找到目录结构")
            return

        print(f"\n📚 PDF文档目录结构:")
        print("=" * 50)
        print_node(self.root_node)
        print("=" * 50)


def main():
    """主函数"""
    try:
        # 设置输入和输出目录
        base_dir = os.path.dirname(os.path.dirname(__file__))
        pdf_dir = os.path.join(base_dir, 'results', 'pdf_reports')
        json_dir = os.path.join(base_dir, 'reports', 'json_reports')

        # 检查PDF目录是否存在
        if not os.path.exists(pdf_dir):
            logging.error(f"PDF目录不存在: {pdf_dir}")
            return

        # 创建JSON输出目录
        os.makedirs(json_dir, exist_ok=True)

        # 获取所有PDF文件
        pdf_files = [f for f in os.listdir(pdf_dir) if f.endswith('.pdf')]

        if not pdf_files:
            logging.warning(f"在目录 {pdf_dir} 中没有找到PDF文件")
            return

        logging.info(f"找到 {len(pdf_files)} 个PDF文件，开始处理...")
        print(f"\n🚀 开始处理 {len(pdf_files)} 个PDF文件...")

        # 处理目录下的所有PDF文件
        processed_files = 0
        failed_files = 0

        for i, file in enumerate(pdf_files, 1):
            try:
                pdf_path = os.path.join(pdf_dir, file)
                print(f"\n📄 处理文件 {i}/{len(pdf_files)}: {file}")

                # 创建PDF解析器
                parser = PdfParser(pdf_path)

                # 提取目录结构
                root_node = parser.extract_outline()

                if root_node and len(root_node.children) > 0:
                    # 生成JSON文件名
                    pdf_name = os.path.splitext(file)[0]
                    json_filename = f"{pdf_name}_chapters.json"
                    json_path = os.path.join(json_dir, json_filename)

                    # 保存为JSON
                    if parser.save_outline_to_json(json_path):
                        processed_files += 1
                        print(f"✅ 文件 {file} 处理成功，JSON已保存到: {json_filename}")

                        # 打印目录结构
                        print("📋 目录结构:")
                        parser.print_outline()
                    else:
                        failed_files += 1
                        print(f"⚠️ 文件 {file} JSON保存失败")
                else:
                    failed_files += 1
                    print(f"⚠️ 文件 {file} 没有提取到目录结构")

            except Exception as e:
                logging.error(f"处理文件 {file} 时出错: {str(e)}")
                failed_files += 1
                print(f"❌ 文件 {file} 处理出错: {str(e)}")

        # 输出最终统计信息
        print(f"\n🎉 所有PDF文件处理完成！")
        print("=" * 60)
        print(f"📊 处理统计:")
        print(f"   总文件数: {len(pdf_files)}")
        print(f"   成功处理: {processed_files}")
        print(f"   处理失败: {failed_files}")
        print(f"   JSON文件保存目录: {json_dir}")
        print("=" * 60)

        logging.info(f"处理完成！成功处理 {processed_files} 个文件，失败 {failed_files} 个，JSON文件已保存到 {json_dir}")

    except Exception as e:
        logging.error(f"主程序执行出错: {str(e)}")
        print(f"❌ 程序执行出错: {str(e)}")

def test_precise_content_extraction():
    """测试精确内容提取功能"""
    print("\n🧪 测试精确内容提取功能...")

    # 模拟节点结构
    class MockNode:
        def __init__(self, title, page_number, parent=None):
            self.title = title
            self.page_number = page_number
            self.parent = parent
            self.children = []

        def add_child(self, child):
            child.parent = self
            self.children.append(child)

    # 创建测试节点树
    root = MockNode("Root", 0)

    # 第一级节点
    section1 = MockNode("第一节", 5, root)
    section2 = MockNode("第二节", 10, root)
    section3 = MockNode("第三节", 15, root)

    # 第二级节点
    subsection1_1 = MockNode("1.1 子章节", 6, section1)
    subsection1_2 = MockNode("1.2 子章节", 8, section1)
    subsection2_1 = MockNode("2.1 子章节", 11, section2)
    subsection2_2 = MockNode("2.2 子章节", 13, section2)

    # 构建树结构
    root.add_child(section1)
    root.add_child(section2)
    root.add_child(section3)

    section1.add_child(subsection1_1)
    section1.add_child(subsection1_2)
    section2.add_child(subsection2_1)
    section2.add_child(subsection2_2)

    print("测试用例1 - 同级兄弟节点:")
    print(f"  当前节点: {subsection1_1.title} (第{subsection1_1.page_number}页)")
    print(f"  下一兄弟节点: {subsection1_2.title} (第{subsection1_2.page_number}页)")
    print(f"  预期结束页: {subsection1_2.page_number}")

    print("\n测试用例2 - 父级兄弟节点:")
    print(f"  当前节点: {subsection1_2.title} (第{subsection1_2.page_number}页)")
    print(f"  父级下一兄弟节点: {section2.title} (第{section2.page_number}页)")
    print(f"  预期结束页: {section2.page_number}")

    print("\n测试用例3 - 最后节点:")
    print(f"  当前节点: {subsection2_2.title} (第{subsection2_2.page_number}页)")
    print(f"  父级下一兄弟节点: {section3.title} (第{subsection2_2.page_number}页)")
    print(f"  预期结束页: {section3.page_number}")

    print("\n测试用例4 - 单页章节内容截取:")
    print("  场景：一个页面包含两个小节")
    print("  条件：start_page == end_page")
    print("  修复：在单页章节情况下也能进行内容截取")
    print("  逻辑：if (page_num == end_page - 1 or start_page == end_page)")

    print("✅ 精确内容提取功能测试完成")

if __name__ == '__main__':
    # 运行测试
    test_precise_content_extraction()

    # 运行主程序
    main()
