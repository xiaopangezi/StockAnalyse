"""
pdf_parser.py

使用 PyPDF2 库解析 PDF 文档，功能包括：
1. 提取文档大纲（目录结构）
2. 按章节拆分文档内容
3. 保存拆分后的文本
"""

import os
import logging
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

    def add_child(self, child: 'PdfOutlineNode'):
        child.parent = self
        self.children.append(child)

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
        def process_outline(node_data, parent_node: PdfOutlineNode, level: int) -> None:
            """
            处理目录节点
            :param node_data: PDF目录节点
            :param parent_node: 父节点
            :param level: 当前层级
            """

            try:
                
                # 获取标题
                title = node_data['/Title']
                
                # 获取目标页面
                dest = None
                if '/Dest' in node_data:
                    dest = node_data['/Dest']
                elif '/A' in node_data:
                    action = node_data['/A']
                    if isinstance(action, dict) and '/D' in action:
                        dest = action['/D']

                # 如果没有找到目标页面，跳过此节点
                if not dest:
                    return

                # 获取页码
                try:
                    if isinstance(dest, list) and len(dest) > 0:
                        page_ref = dest[0]
                        page_number = self.reader.get_page_number(page_ref) + 1
                    else:
                        return
                except Exception:
                    return

                # 创建当前节点
                current_node = PdfOutlineNode(title, page_number, level)
                parent_node.add_child(current_node)

                # 处理第一个子节点
                if '/First' in node_data:
                    first_child = node_data['/First']
                    process_outline(first_child, current_node, level + 1)
                    
                    # 处理同级的下一个节点
                    next_sibling = first_child
                    while '/Next' in next_sibling:
                        next_sibling = next_sibling['/Next']
                        process_outline(next_sibling, current_node, level + 1)

                # 处理同级的下一个节点
                if '/Next' in node_data:
                    next_node = node_data['/Next']
                    process_outline(next_node, parent_node, level)

            except Exception as e:
                logging.error(f"处理目录节点时出错: {str(e)}")

        try:
            # 创建根节点
            self.root_node = PdfOutlineNode("Root")
            
            # 获取文档大纲
            outline = self.reader.outline
            if not outline:
                logging.warning("PDF文档没有目录结构")
                return self.root_node

            # 处理第一个顶级目录项
            if isinstance(outline, list) and outline:
                first_outline = outline[0]
                if hasattr(first_outline, 'node'):
                    process_outline(first_outline.node, self.root_node, 0)

            # 设置每个节点的结束页码
            self._set_end_pages()

            return self.root_node
            
        except Exception as e:
            logging.error(f"提取目录结构时出错: {str(e)}")
            return PdfOutlineNode("Error")

    def _set_end_pages(self):
        """设置每个节点的结束页码"""
        def get_first_level_nodes(node: PdfOutlineNode) -> List[PdfOutlineNode]:
            """获取所有一级节点"""
            return [child for child in node.children if child.level == 0]

        # 获取一级节点并按页码排序
        first_level_nodes = get_first_level_nodes(self.root_node)
        first_level_nodes.sort(key=lambda x: x.page_number)
        
        # 设置每个节点的结束页码为下一个节点的起始页码
        for i in range(len(first_level_nodes) - 1):
            first_level_nodes[i].next_sibling_page = first_level_nodes[i + 1].page_number

        # 最后一个节点的结束页码为文档最后一页
        if first_level_nodes:
            first_level_nodes[-1].next_sibling_page = len(self.reader.pages)

    def extract_chapter_content(self, node: PdfOutlineNode) -> str:
        """
        提取指定章节的内容
        :param node: 目录节点
        :return: 章节内容
        """
        start_page = node.page_number - 1  # 转换为0基础的页码
        end_page = node.next_sibling_page - 1 if node.next_sibling_page else len(self.reader.pages)
        
        content = []
        for page_num in range(start_page, end_page):
            page = self.reader.pages[page_num]
            text = page.extract_text()
            
            # 如果是第一页，从章节标题开始提取
            if page_num == start_page:
                # 查找章节标题在文本中的位置
                title_pos = text.find(node.title)
                if title_pos != -1:
                    text = text[title_pos:]
            
            content.append(text)
        
        return "\n".join(content)

    def save_chapters(self, output_dir: str):
        """
        保存所有一级章节的内容到单独的文件
        :param output_dir: 输出目录
        """
        os.makedirs(output_dir, exist_ok=True)
        
        # 获取PDF文件名（不含扩展名）
        pdf_name = os.path.splitext(os.path.basename(self.pdf_path))[0]
        
        # 处理一级节点
        for node in self.root_node.children:
            if node.level == 0:  # 只处理一级节点
                # 清理文件名中的非法字符
                safe_title = re.sub(r'[\\/:*?"<>|]', '_', node.title)
                output_file = os.path.join(output_dir, f"{pdf_name}_{safe_title}.txt")
                
                try:
                    content = self.extract_chapter_content(node)
                    with open(output_file, 'w', encoding='utf-8') as f:
                        f.write(content)
                    logging.info(f"已保存章节：{node.title} -> {output_file}")
                except Exception as e:
                    logging.error(f"保存章节 {node.title} 时出错: {str(e)}")

    def print_outline(self):
        """打印目录结构"""
        def print_node(node: PdfOutlineNode):
            if node.level >= 0:  # 不打印根节点
                print(node)
            for child in node.children:
                print_node(child)
        
        print_node(self.root_node)

def process_pdf(pdf_path: str) -> List[Dict[str, str]]:
    """
    处理单个PDF文件，返回按章节分割的内容
    :param pdf_path: PDF文件路径
    :return: 包含章节标题和内容的字典列表，每个字典包含 'title' 和 'content' 两个键
    """
    try:
        parser = PdfParser(pdf_path)
        
        # 提取目录结构
        root_node = parser.extract_outline()
        if len(root_node.children) == 0:
            logging.warning(f"PDF文件 {pdf_path} 无法提取目录结构")
            return []
        
        # 打印目录结构
        logging.info(f"\nPDF文件 {pdf_path} 的目录结构：")
        parser.print_outline()
        
        # 获取PDF文件名（不含扩展名）作为标题前缀
        pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
        
        # 提取每个章节的内容
        chapters = []
        for node in root_node.children:
            if node.level == 0:  # 只处理一级节点
                try:
                    content = parser.extract_chapter_content(node)
                    chapters.append({
                        'title': f"{pdf_name} - {node.title}",
                        'content': content
                    })
                    logging.info(f"已提取章节：{node.title}")
                except Exception as e:
                    logging.error(f"提取章节 {node.title} 时出错: {str(e)}")
        
        return chapters
        
    except Exception as e:
        logging.error(f"处理PDF文件 {pdf_path} 时出错: {str(e)}")
        return []

def main():
    """主函数"""
    # 设置输入目录
    base_dir = os.path.dirname(os.path.dirname(__file__))
    pdf_dir = os.path.join(base_dir, 'results', 'pdf_reports')
    
    # 处理目录下的所有PDF文件
    total_chapters = []
    
    for file in os.listdir(pdf_dir):
        if file.endswith('.pdf'):
            pdf_path = os.path.join(pdf_dir, file)
            chapters = process_pdf(pdf_path)
            total_chapters.extend(chapters)
    
    logging.info(f"\n处理完成！共提取 {len(total_chapters)} 个章节")

if __name__ == '__main__':
    main() 