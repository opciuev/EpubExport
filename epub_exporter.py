#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EPUB 章节导出工具
使用 Pandoc 将 EPUB 文件按章节导出为 Markdown 或 TXT 格式
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


class EpubExporter:
    """EPUB 导出器类"""
    
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
        获取所有章节内容
        
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
        
        # 获取书籍的导航结构
        toc = self.book.toc
        spine = self.book.spine
        
        if debug:
            print(f"\n📖 TOC 结构分析:")
            print(f"TOC 类型: {type(toc)}")
            print(f"TOC 长度: {len(toc) if toc else 0}")
            
        # 如果有目录结构，使用目录
        if toc:
            chapters.extend(self._extract_from_toc(toc, debug))
        else:
            # 否则从 spine 中提取
            chapters.extend(self._extract_from_spine(spine, debug))
        
        if debug:
            print(f"\n📊 章节提取结果:")
            for i, (title, content, chapter_id) in enumerate(chapters):
                print(f"  {i+1}. 标题: {title}")
                print(f"     ID: {chapter_id}")
                print(f"     内容长度: {len(content)} 字符")
                print(f"     内容预览: {content[:100].replace(chr(10), ' ')[:50]}...")
                print()
        
        # 检查是否所有章节内容都相同（常见问题）
        if len(chapters) > 1:
            first_content = chapters[0][1]
            if all(chapter[1] == first_content for chapter in chapters):
                print("⚠️  检测到所有章节内容相同，尝试基于内容分割...")
                # 尝试基于内容分割章节
                split_chapters = self._split_content_by_headings(first_content, debug)
                if split_chapters:
                    chapters = split_chapters
                    
        return chapters
    
    def _get_item_by_id(self, item_id: str):
        """根据 ID 获取项目（兼容不同版本的 ebooklib）"""
        # 尝试使用新版本的方法
        if hasattr(self.book, 'get_item_by_id'):
            return self.book.get_item_by_id(item_id)
        
        # 备用方法：遍历所有项目
        for item in self.book.get_items():
            if item.get_id() == item_id:
                return item
        return None
    
    def _print_epub_structure(self):
        """打印 EPUB 文件的详细结构信息"""
        print(f"\n🔍 EPUB 文件结构分析:")
        print(f"=" * 60)
        
        # 基本信息
        print(f"📚 书籍元数据:")
        metadata = self.book.metadata
        for key, values in metadata.items():
            print(f"  {key}: {[str(v[0]) for v in values]}")
        
        # Spine 信息
        print(f"\n📄 Spine 结构 (阅读顺序):")
        for i, (item_id, linear) in enumerate(self.book.spine):
            item = self._get_item_by_id(item_id)
            
            if item:
                print(f"  {i+1}. ID: {item_id}")
                print(f"     文件名: {item.get_name()}")
                print(f"     类型: {item.get_type()}")
                print(f"     线性: {linear}")
                if item.get_type() == ebooklib.ITEM_DOCUMENT:
                    try:
                        content = item.get_content().decode('utf-8')
                        print(f"     内容长度: {len(content)} 字符")
                    except:
                        print(f"     内容长度: 无法解码")
                print()
            else:
                print(f"  {i+1}. ID: {item_id} (未找到对应项目)")
                print(f"     线性: {linear}")
                print()
        
        # TOC 信息
        print(f"\n📑 目录 (TOC) 结构:")
        self._print_toc_recursive(self.book.toc, level=0)
        
        # 所有项目
        print(f"\n📦 所有文件项目:")
        for item in self.book.get_items():
            print(f"  ID: {item.get_id()}")
            print(f"  文件名: {item.get_name()}")
            print(f"  类型: {item.get_type()}")
            if item.get_type() == ebooklib.ITEM_DOCUMENT:
                content = item.get_content().decode('utf-8')
                print(f"  内容长度: {len(content)} 字符")
            print()
        
        print(f"=" * 60)
    
    def _print_toc_recursive(self, toc_items, level=0):
        """递归打印 TOC 结构"""
        indent = "  " * level
        for item in toc_items:
            if isinstance(item, tuple):
                # (Section, children)
                section, children = item
                print(f"{indent}📂 {section.title}")
                print(f"{indent}   href: {section.href}")
                if children:
                    self._print_toc_recursive(children, level + 1)
            else:
                # 单个条目
                print(f"{indent}📄 {item.title}")
                print(f"{indent}   href: {item.href}")
    
    def _extract_from_toc(self, toc, debug=False) -> List[Tuple[str, str, str]]:
        """从目录结构中提取章节"""
        chapters = []
        
        def process_toc_item(item, level=0):
            indent = "  " * level
            if isinstance(item, tuple):
                # (Section, children)
                section, children = item
                if debug:
                    print(f"{indent}处理 TOC 组: {section.title} -> {section.href}")
                
                if hasattr(section, 'title') and hasattr(section, 'href'):
                    content = self._get_item_content(section.href)
                    if content:
                        title = section.title or f"章节 {len(chapters) + 1}"
                        chapters.append((title, content, section.href))
                        if debug:
                            print(f"{indent}  ✓ 添加章节: {title} (长度: {len(content)})")
                    elif debug:
                        print(f"{indent}  ✗ 无内容: {section.href}")
                
                # 处理子章节
                if children:
                    for child in children:
                        process_toc_item(child, level + 1)
            else:
                # 单个章节
                if debug:
                    print(f"{indent}处理 TOC 项: {item.title} -> {item.href}")
                
                if hasattr(item, 'title') and hasattr(item, 'href'):
                    content = self._get_item_content(item.href)
                    if content:
                        title = item.title or f"章节 {len(chapters) + 1}"
                        chapters.append((title, content, item.href))
                        if debug:
                            print(f"{indent}  ✓ 添加章节: {title} (长度: {len(content)})")
                    elif debug:
                        print(f"{indent}  ✗ 无内容: {item.href}")
        
        if debug:
            print(f"\n🔄 开始处理 TOC 项目:")
        
        for item in toc:
            process_toc_item(item)
            
        return chapters
    
    def _extract_from_spine(self, spine, debug=False) -> List[Tuple[str, str, str]]:
        """从 spine 中提取章节"""
        chapters = []
        
        if debug:
            print(f"\n🔄 从 Spine 提取章节:")
        
        for item_id, _ in spine:
            item = self._get_item_by_id(item_id)
            
            if item and item.get_type() == ebooklib.ITEM_DOCUMENT:
                try:
                    content = item.get_content().decode('utf-8')
                    if content.strip():
                        # 尝试从内容中提取标题
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
    
    def _get_item_content(self, href: str) -> Optional[str]:
        """根据 href 获取内容，支持锚点分割"""
        # 分离文件名和锚点
        if '#' in href:
            file_name, anchor = href.split('#', 1)
        else:
            file_name, anchor = href, None
        
        # 获取完整文件内容
        full_content = None
        for item in self.book.get_items():
            if item.get_name() == file_name and item.get_type() == ebooklib.ITEM_DOCUMENT:
                full_content = item.get_content().decode('utf-8')
                break
        
        if not full_content:
            return None
        
        # 如果没有锚点，返回完整内容
        if not anchor:
            return full_content
        
        # 如果有锚点，尝试根据锚点分割内容
        return self._extract_content_by_anchor(full_content, anchor, href)
    
    def _extract_content_by_anchor(self, content: str, anchor: str, original_href: str) -> str:
        """根据锚点提取内容片段"""
        import re
        
        # 处理 filepos 类型的锚点
        if anchor.startswith('filepos'):
            return self._extract_by_filepos(content, anchor, original_href)
        
        # 处理普通 ID 锚点
        return self._extract_by_id_anchor(content, anchor)
    
    def _extract_by_filepos(self, content: str, anchor: str, original_href: str) -> str:
        """根据 filepos 锚点提取内容"""
        # filepos 通常表示文件中的字节位置，但在 HTML 中我们需要找到对应的标记
        # 尝试找到包含这个 filepos 的元素
        
        import re
        
        # 查找包含该 filepos 的 anchor 标签或 id 属性
        filepos_pattern = rf'(?:id|name)=["\']?{re.escape(anchor)}["\']?'
        match = re.search(filepos_pattern, content, re.IGNORECASE)
        
        if match:
            # 找到锚点位置，提取从这里到下一个主要标题的内容
            start_pos = match.start()
            
            # 查找下一个可能的章节分割点
            next_section_patterns = [
                r'<h[1-4][^>]*>',  # 下一个标题
                r'id=["\']?filepos\d+["\']?',  # 下一个 filepos
                r'<div[^>]*class=["\'][^"\']*chapter[^"\']*["\'][^>]*>',  # 章节 div
            ]
            
            end_pos = len(content)
            for pattern in next_section_patterns:
                matches = list(re.finditer(pattern, content[start_pos + 100:], re.IGNORECASE))
                if matches:
                    end_pos = start_pos + 100 + matches[0].start()
                    break
            
            extracted = content[start_pos:end_pos].strip()
            if extracted:
                return extracted
        
        # 如果找不到精确的锚点，尝试智能分割
        return self._smart_split_content(content, original_href)
    
    def _extract_by_id_anchor(self, content: str, anchor: str) -> str:
        """根据 ID 锚点提取内容"""
        import re
        
        # 查找具有指定 ID 的元素
        id_pattern = rf'<[^>]+id=["\']?{re.escape(anchor)}["\']?[^>]*>'
        match = re.search(id_pattern, content, re.IGNORECASE)
        
        if match:
            start_pos = match.start()
            # 查找下一个同级或更高级的标题
            next_heading = re.search(r'<h[1-4][^>]*>', content[start_pos + len(match.group()):])
            if next_heading:
                end_pos = start_pos + len(match.group()) + next_heading.start()
                return content[start_pos:end_pos].strip()
            else:
                return content[start_pos:].strip()
        
        return content
    
    def _smart_split_content(self, content: str, href: str) -> str:
        """智能分割内容 - 当无法找到精确锚点时的备用方案"""
        # 如果内容很长，尝试基于标题分割
        if len(content) > 10000:  # 如果内容超过 10KB
            # 尝试找到所有标题
            import re
            headings = list(re.finditer(r'<h[1-4][^>]*>(.*?)</h[1-4]>', content, re.IGNORECASE | re.DOTALL))
            
            if len(headings) > 1:
                # 如果有多个标题，返回第一个标题到第二个标题之间的内容
                start_pos = headings[0].start()
                end_pos = headings[1].start()
                return content[start_pos:end_pos].strip()
        
        # 默认返回原内容
        return content
    
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
                if title:
                    return title
        return None
    
    def _split_content_by_headings(self, content: str, debug=False) -> List[Tuple[str, str, str]]:
        """基于标题分割内容为多个章节"""
        chapters = []
        
        # 尝试多种标题模式
        heading_patterns = [
            r'<h[1-3][^>]*>(.*?)</h[1-3]>',  # HTML 标题标签
            r'^#+\s+(.+)$',  # Markdown 标题
            r'^第[一二三四五六七八九十\d]+章[：:\s]*(.*)$',  # 中文章节标题
            r'^第[一二三四五六七八九十\d]+部分[：:\s]*(.*)$',  # 中文部分标题
            r'^Chapter\s+\d+[：:\s]*(.*)$',  # 英文章节标题
            r'^\d+[\.、]\s*(.+)$',  # 数字编号标题
        ]
        
        # 首先尝试 HTML 标题标签分割
        html_chapters = self._split_by_html_headings(content)
        if html_chapters:
            return html_chapters
        
        # 如果 HTML 分割失败，尝试文本模式分割
        text_chapters = self._split_by_text_patterns(content, heading_patterns)
        if text_chapters:
            return text_chapters
            
        # 如果都失败了，返回原始内容作为单个章节
        print("⚠️  无法自动分割章节，将作为单个文件导出")
        return [("完整内容", content, "full_content")]
    
    def _split_by_html_headings(self, content: str) -> List[Tuple[str, str, str]]:
        """基于 HTML 标题标签分割内容"""
        import re
        from html import unescape
        
        chapters = []
        
        # 查找所有 h1-h3 标题
        heading_pattern = r'<h([1-3])[^>]*>(.*?)</h\1>'
        headings = list(re.finditer(heading_pattern, content, re.IGNORECASE | re.DOTALL))
        
        if len(headings) < 2:
            return []
        
        for i, heading in enumerate(headings):
            # 提取标题文本
            title_html = heading.group(2)
            title = re.sub(r'<[^>]+>', '', title_html)
            title = unescape(title).strip()
            
            if not title:
                title = f"章节 {i + 1}"
            
            # 确定章节内容范围
            start_pos = heading.start()
            end_pos = headings[i + 1].start() if i + 1 < len(headings) else len(content)
            
            chapter_content = content[start_pos:end_pos].strip()
            
            if chapter_content:
                chapters.append((title, chapter_content, f"chapter_{i + 1}"))
        
        return chapters if len(chapters) > 1 else []
    
    def _split_by_text_patterns(self, content: str, patterns: List[str]) -> List[Tuple[str, str, str]]:
        """基于文本模式分割内容"""
        import re
        
        # 移除 HTML 标签，转换为纯文本
        text_content = re.sub(r'<[^>]+>', '\n', content)
        text_content = re.sub(r'\n+', '\n', text_content).strip()
        
        lines = text_content.split('\n')
        chapters = []
        current_chapter = []
        current_title = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # 检查是否是标题行
            is_heading = False
            title = None
            
            for pattern in patterns:
                match = re.match(pattern, line, re.IGNORECASE)
                if match:
                    is_heading = True
                    title = match.group(1).strip() if match.groups() else line
                    break
            
            if is_heading and current_chapter:
                # 保存上一章节
                chapter_content = '\n'.join(current_chapter).strip()
                if chapter_content:
                    chapters.append((current_title or f"章节 {len(chapters) + 1}", 
                                   chapter_content, f"chapter_{len(chapters) + 1}"))
                
                # 开始新章节
                current_chapter = [line]
                current_title = title
            else:
                current_chapter.append(line)
        
        # 保存最后一章节
        if current_chapter:
            chapter_content = '\n'.join(current_chapter).strip()
            if chapter_content:
                chapters.append((current_title or f"章节 {len(chapters) + 1}", 
                               chapter_content, f"chapter_{len(chapters) + 1}"))
        
        return chapters if len(chapters) > 1 else []

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
def main(epub_file: str, output: str, format: str):
    """
    EPUB 章节导出工具
    
    将 EPUB 文件按章节导出为 Markdown 或 TXT 格式
    
    示例:
        python epub_exporter.py book.epub
        python epub_exporter.py book.epub -o ./chapters -f txt
    """
    try:
        print(f"🚀 开始处理 EPUB 文件: {epub_file}")
        
        exporter = EpubExporter(epub_file)
        exporter.export_chapters(output, format)
        
    except Exception as e:
        print(f"❌ 错误: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
