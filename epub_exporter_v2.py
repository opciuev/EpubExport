#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EPUB 章节导出工具 v2.0
基于 ebooklib 标准方法的简化实现，避免复杂的自制锚点处理算法
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path
import click
import ebooklib
from ebooklib import epub
import pypandoc
import re
from typing import List, Tuple, Optional
from html import unescape


class EpubExporterV2:
    """EPUB 导出器 v2.0 - 基于标准方法的简化实现"""
    
    def __init__(self, epub_path: str):
        """
        初始化 EPUB 导出器
        
        Args:
            epub_path: EPUB 文件路径
        """
        self.epub_path = Path(epub_path)
        self.book = None
        self.temp_dir = None
        
        if not self.epub_path.exists():
            raise FileNotFoundError(f"EPUB 文件不存在: {epub_path}")
            
    def load_epub(self) -> None:
        """加载 EPUB 文件"""
        try:
            self.book = epub.read_epub(str(self.epub_path))
            print(f"✓ 成功加载 EPUB 文件: {self.epub_path.name}")
        except Exception as e:
            raise Exception(f"无法加载 EPUB 文件: {e}")
    
    def get_chapters(self, debug=False) -> List[Tuple[str, str, str]]:
        """
        获取所有章节内容 - 使用标准方法
        
        Args:
            debug: 是否输出调试信息
            
        Returns:
            List of (chapter_title, chapter_content, chapter_id)
        """
        if not self.book:
            self.load_epub()
            
        if debug:
            self._print_epub_structure()
            
        chapters = []
        
        # 方法1: 优先使用 TOC (目录) 结构
        if self.book.toc:
            if debug:
                print(f"\n📖 使用 TOC 结构提取章节")
            chapters = self._extract_from_toc_standard(debug)
        
        # 方法2: 如果 TOC 为空或提取失败，使用 Spine 顺序
        if not chapters:
            if debug:
                print(f"\n📄 TOC 提取失败，使用 Spine 顺序提取")
            chapters = self._extract_from_spine_standard(debug)
        
        if debug:
            print(f"\n📊 最终章节统计:")
            total_length = 0
            for i, (title, content, chapter_id) in enumerate(chapters):
                content_length = len(content)
                total_length += content_length
                print(f"  {i+1:2d}. {title[:50]:<50} | {content_length:>8,} 字符")
            print(f"总内容长度: {total_length:,} 字符")
        
        return chapters
    
    def _extract_from_toc_standard(self, debug=False) -> List[Tuple[str, str, str]]:
        """使用标准方法从 TOC 提取章节 - 避免复杂的锚点处理"""
        chapters = []
        processed_files = set()  # 跟踪已处理的文件，避免重复
        
        def process_toc_item(item, level=0):
            indent = "  " * level
            
            if isinstance(item, tuple):
                # (Section, children) 格式
                section, children = item
                if debug:
                    print(f"{indent}处理 TOC 组: {section.title}")
                
                # 处理当前节
                if hasattr(section, 'href') and section.href:
                    self._process_single_toc_entry(section, chapters, processed_files, debug, indent)
                
                # 处理子节
                if children:
                    for child in children:
                        process_toc_item(child, level + 1)
            else:
                # 单个 TOC 条目
                if debug:
                    print(f"{indent}处理 TOC 项: {item.title}")
                
                if hasattr(item, 'href') and item.href:
                    self._process_single_toc_entry(item, chapters, processed_files, debug, indent)
        
        if debug:
            print(f"开始处理 {len(self.book.toc)} 个 TOC 项目")
        
        for item in self.book.toc:
            process_toc_item(item)
            
        return chapters
    
    def _process_single_toc_entry(self, toc_entry, chapters, processed_files, debug, indent):
        """处理单个 TOC 条目 - 使用保守的方法"""
        href = toc_entry.href
        title = toc_entry.title or f"章节 {len(chapters) + 1}"
        
        if debug:
            print(f"{indent}  处理链接: {href}")
        
        # 分离文件名和锚点
        if '#' in href:
            file_name, anchor = href.split('#', 1)
        else:
            file_name, anchor = href, None
        
        # 查找对应的文档项目
        doc_item = None
        for item in self.book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
            if item.get_name() == file_name:
                doc_item = item
                break
        
        if not doc_item:
            if debug:
                print(f"{indent}    ❌ 未找到文档: {file_name}")
            return
        
        # 获取文档内容
        try:
            content = doc_item.get_content().decode('utf-8')
        except Exception as e:
            if debug:
                print(f"{indent}    ❌ 解码失败: {e}")
            return
        
        # 关键决策：如何处理锚点
        if anchor:
            if debug:
                print(f"{indent}    🔗 发现锚点: {anchor}")
            
            # 保守方法：如果文件已经被处理过，跳过（避免重复）
            # 如果文件未被处理过，提取整个文件内容（避免复杂的锚点分割）
            file_key = f"{file_name}#{anchor}"
            if file_key in processed_files:
                if debug:
                    print(f"{indent}    ⚠️  锚点已处理，跳过: {file_key}")
                return
            
            # 简单的锚点处理：只处理明显的章节分割
            processed_content = self._simple_anchor_processing(content, anchor, debug, indent)
            if processed_content and len(processed_content) > 500:  # 确保有足够内容
                chapters.append((title, processed_content, file_key))
                processed_files.add(file_key)
                if debug:
                    print(f"{indent}    ✓ 添加章节 (锚点): {title} ({len(processed_content)} 字符)")
            else:
                # 如果锚点处理失败，使用整个文件（如果未处理过）
                if file_name not in processed_files:
                    chapters.append((title, content, file_name))
                    processed_files.add(file_name)
                    if debug:
                        print(f"{indent}    ✓ 添加章节 (整个文件): {title} ({len(content)} 字符)")
        else:
            # 无锚点：直接使用整个文件
            if file_name not in processed_files:
                chapters.append((title, content, file_name))
                processed_files.add(file_name)
                if debug:
                    print(f"{indent}    ✓ 添加章节 (无锚点): {title} ({len(content)} 字符)")
            elif debug:
                print(f"{indent}    ⚠️  文件已处理，跳过: {file_name}")
    
    def _simple_anchor_processing(self, content: str, anchor: str, debug=False, indent="") -> Optional[str]:
        """简单的锚点处理 - 只处理明显的情况，避免复杂算法"""
        
        # 方法1: 查找精确的 id 或 name 属性
        patterns = [
            rf'<[^>]+id=["\']?{re.escape(anchor)}["\']?[^>]*>',
            rf'<[^>]+name=["\']?{re.escape(anchor)}["\']?[^>]*>',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                start_pos = match.start()
                
                # 查找下一个明显的章节分割点（只查找标题标签）
                next_heading = re.search(r'<h[1-4][^>]*>', content[start_pos + 100:], re.IGNORECASE)
                if next_heading:
                    end_pos = start_pos + 100 + next_heading.start()
                    extracted = content[start_pos:end_pos].strip()
                    if debug:
                        print(f"{indent}      ✓ 锚点匹配成功，提取 {len(extracted)} 字符")
                    return extracted
                else:
                    # 没找到下一个标题，返回从锚点到文件末尾的内容
                    extracted = content[start_pos:].strip()
                    if debug:
                        print(f"{indent}      ✓ 锚点匹配成功，提取到文件末尾 {len(extracted)} 字符")
                    return extracted
        
        if debug:
            print(f"{indent}      ❌ 锚点匹配失败: {anchor}")
        return None
    
    def _extract_from_spine_standard(self, debug=False) -> List[Tuple[str, str, str]]:
        """使用标准方法从 Spine 提取章节"""
        chapters = []
        
        if debug:
            print(f"从 Spine 提取 {len(self.book.spine)} 个文档")
        
        for i, (item_id, linear) in enumerate(self.book.spine):
            if not linear:  # 跳过非线性项目
                continue
                
            item = self.book.get_item_with_id(item_id)
            
            if item and item.get_type() == ebooklib.ITEM_DOCUMENT:
                try:
                    content = item.get_content().decode('utf-8')
                    if content.strip():
                        # 从内容中提取标题
                        title = self._extract_title_from_content(content) or f"章节 {len(chapters) + 1}"
                        chapters.append((title, content, item_id))
                        if debug:
                            print(f"  ✓ 添加章节: {title} (ID: {item_id}, 长度: {len(content)})")
                    elif debug:
                        print(f"  ✗ 空内容: {item_id}")
                except Exception as e:
                    if debug:
                        print(f"  ✗ 解码失败: {item_id} - {e}")
            elif debug:
                if item:
                    print(f"  ✗ 非文档项: {item_id} (类型: {item.get_type()})")
                else:
                    print(f"  ✗ 未找到项目: {item_id}")
                    
        return chapters
    
    def _extract_title_from_content(self, content: str) -> Optional[str]:
        """从 HTML 内容中提取标题"""
        # 尝试提取 h1, h2 等标题标签
        title_patterns = [
            r'<h[1-6][^>]*>(.*?)</h[1-6]>',
            r'<title[^>]*>(.*?)</title>',
        ]
        
        for pattern in title_patterns:
            match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
            if match:
                title = re.sub(r'<[^>]+>', '', match.group(1)).strip()
                title = unescape(title)
                if title:
                    return title
        return None
    
    def _print_epub_structure(self):
        """打印 EPUB 文件的基本结构信息"""
        print(f"\n🔍 EPUB 文件结构分析:")
        print(f"=" * 60)
        
        # 基本信息
        print(f"📚 书籍信息:")
        title = self.book.get_metadata('DC', 'title')
        author = self.book.get_metadata('DC', 'creator')
        print(f"  标题: {title[0][0] if title else '未知'}")
        print(f"  作者: {author[0][0] if author else '未知'}")
        
        # TOC 信息
        print(f"\n📑 目录结构:")
        print(f"  TOC 项目数: {len(self.book.toc) if self.book.toc else 0}")
        
        # Spine 信息
        print(f"\n📄 阅读顺序:")
        print(f"  Spine 项目数: {len(self.book.spine) if self.book.spine else 0}")
        
        # 文档项目
        doc_items = list(self.book.get_items_of_type(ebooklib.ITEM_DOCUMENT))
        print(f"\n📦 文档项目:")
        print(f"  文档数量: {len(doc_items)}")
        
        print(f"=" * 60)
    
    def _sanitize_filename(self, filename: str) -> str:
        """清理文件名，移除非法字符"""
        # 移除或替换非法字符
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        # 移除多余的空格和点
        filename = re.sub(r'\s+', ' ', filename).strip()
        filename = filename.strip('.')
        # 限制长度
        if len(filename) > 100:
            filename = filename[:100]
        return filename or "untitled"
    
    def export_chapters(self, output_dir: str, format_type: str = 'markdown') -> None:
        """
        导出所有章节
        
        Args:
            output_dir: 输出目录
            format_type: 输出格式 ('markdown' 或 'txt')
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        chapters = self.get_chapters()
        
        if not chapters:
            print("⚠️  未找到任何章节内容")
            return
        
        print(f"📚 找到 {len(chapters)} 个章节，开始导出...")
        
        # 导出图片资源
        images_exported = self._export_images(output_path)
        if images_exported:
            print(f"🖼️  导出了 {images_exported} 个图片文件")
        
        # 创建临时目录用于 pandoc 转换
        with tempfile.TemporaryDirectory() as temp_dir:
            self.temp_dir = temp_dir
            
            for i, (title, content, chapter_id) in enumerate(chapters, 1):
                try:
                    # 处理内容中的图片链接
                    processed_content = self._process_image_links(content, format_type)
                    
                    self._export_single_chapter(
                        title, processed_content, i, output_path, format_type
                    )
                except Exception as e:
                    print(f"❌ 导出章节 '{title}' 失败: {e}")
                    continue
        
        print(f"✅ 导出完成！文件保存在: {output_path}")
    
    def _export_images(self, output_path: Path) -> int:
        """导出 EPUB 中的所有图片，保持原始目录结构"""
        if not self.book:
            return 0
        
        exported_count = 0
        self.image_mapping = {}  # 存储原始路径到新路径的映射
        
        for item in self.book.get_items():
            if item.get_type() == ebooklib.ITEM_IMAGE:
                try:
                    # 获取原始图片路径
                    original_path = item.get_name()
                    
                    # 创建完整的输出路径（保持目录结构）
                    image_output_path = output_path / original_path
                    
                    # 确保目录存在
                    image_output_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # 保存图片
                    with open(image_output_path, 'wb') as f:
                        f.write(item.get_content())
                    
                    # 记录映射关系
                    self.image_mapping[original_path] = original_path
                    
                    exported_count += 1
                    print(f"  📷 导出图片: {original_path}")
                    
                except Exception as e:
                    print(f"  ❌ 导出图片失败 {item.get_name()}: {e}")
        
        return exported_count
    
    def _process_image_links(self, content: str, format_type: str) -> str:
        """处理内容中的图片链接"""
        import re
        
        if format_type.lower() != 'markdown':
            return content
        
        # 查找所有 img 标签
        img_pattern = r'<img[^>]*src=["\']([^"\']+)["\'][^>]*>'
        
        def replace_img_tag(match):
            img_tag = match.group(0)
            src = match.group(1)
            
            # 清理路径（移除 ../ 等相对路径前缀）
            clean_src = src
            while clean_src.startswith('../'):
                clean_src = clean_src[3:]
            
            # 尝试提取 alt 文本
            alt_match = re.search(r'alt=["\']([^"\']*)["\']', img_tag, re.IGNORECASE)
            alt_text = alt_match.group(1) if alt_match else "图片"
            
            # 检查是否有映射关系
            if hasattr(self, 'image_mapping') and clean_src in self.image_mapping:
                image_path = self.image_mapping[clean_src]
            else:
                # 如果没有映射，使用原始路径
                image_path = clean_src
            
            # 返回 Markdown 格式的图片链接（使用相对路径）
            return f'![{alt_text}]({image_path})'
        
        # 替换所有 img 标签
        processed_content = re.sub(img_pattern, replace_img_tag, content, flags=re.IGNORECASE)
        
        return processed_content
    
    def _export_single_chapter(self, title: str, content: str, index: int, 
                             output_path: Path, format_type: str) -> None:
        """导出单个章节"""
        # 清理标题作为文件名
        safe_title = self._sanitize_filename(title)
        
        # 生成文件名
        if format_type.lower() == 'markdown':
            filename = f"{index:02d}_{safe_title}.md"
            pandoc_format = 'markdown'
        else:
            filename = f"{index:02d}_{safe_title}.txt"
            pandoc_format = 'plain'
        
        output_file = output_path / filename
        
        try:
            # 使用 pandoc 转换 HTML 到目标格式
            converted_content = pypandoc.convert_text(
                content,
                pandoc_format,
                format='html',
                extra_args=['--wrap=none']  # 不自动换行
            )
            
            # 写入文件
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(converted_content)
            
            print(f"✓ 已导出: {filename}")
            
        except Exception as e:
            print(f"❌ 转换章节 '{title}' 时出错: {e}")
            # 如果 pandoc 转换失败，尝试简单的 HTML 标签清理
            self._fallback_export(content, output_file, title)
    
    def _fallback_export(self, content: str, output_file: Path, title: str) -> None:
        """备用导出方法（简单的 HTML 标签清理）"""
        try:
            # 简单的 HTML 标签清理
            import html
            
            # 移除 HTML 标签
            clean_content = re.sub(r'<[^>]+>', '', content)
            # 解码 HTML 实体
            clean_content = html.unescape(clean_content)
            # 清理多余的空白
            clean_content = re.sub(r'\n\s*\n', '\n\n', clean_content)
            clean_content = clean_content.strip()
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(clean_content)
            
            print(f"✓ 已导出 (备用方法): {output_file.name}")
            
        except Exception as e:
            print(f"❌ 备用导出也失败了: {e}")


@click.command()
@click.argument('epub_file', type=click.Path(exists=True))
@click.option('--output', '-o', default='./output', 
              help='输出目录 (默认: ./output)')
@click.option('--format', '-f', type=click.Choice(['markdown', 'txt']), 
              default='markdown', help='输出格式 (默认: markdown)')
@click.option('--debug', '-d', is_flag=True, help='启用调试模式')
def main(epub_file: str, output: str, format: str, debug: bool):
    """
    EPUB 章节导出工具 v2.0
    
    基于标准方法的简化实现，避免复杂的自制锚点处理算法
    
    示例:
        python epub_exporter_v2.py book.epub
        python epub_exporter_v2.py book.epub -o ./chapters -f txt -d
    """
    try:
        print(f"🚀 开始处理 EPUB 文件: {epub_file}")
        
        exporter = EpubExporterV2(epub_file)
        
        if debug:
            print("🔍 调试模式已启用")
            # 先运行调试分析
            chapters = exporter.get_chapters(debug=True)
            print(f"\n是否继续导出？(y/n): ", end="")
            response = input().strip().lower()
            if response != 'y':
                print("已取消导出")
                return
        
        exporter.export_chapters(output, format)
        
    except Exception as e:
        print(f"❌ 错误: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
