#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EPUB Chapter Exporter Tool
Export EPUB files chapter by chapter to Markdown or TXT format using Pandoc
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
    """EPUB Exporter Class"""
    
    def __init__(self, epub_path: str):
        """
        Initialize EPUB Exporter
        
        Args:
            epub_path: Path to EPUB file
        """
        self.epub_path = Path(epub_path)
        self.book = None
        self.temp_dir = None
        
        if not self.epub_path.exists():
            raise FileNotFoundError(f"EPUB file does not exist: {epub_path}")
            
    def load_epub(self) -> None:
        """Load EPUB file"""
        try:
            self.book = epub.read_epub(str(self.epub_path))
            print(f"✓ Successfully loaded EPUB file: {self.epub_path.name}")
        except Exception as e:
            raise Exception(f"Unable to load EPUB file: {e}")
    
    def get_chapters(self, debug=False) -> List[Tuple[str, str, str]]:
        """
        Get all chapter contents
        
        Args:
            debug: Whether to output debug information
            
        Returns:
            List of (chapter_title, chapter_content, chapter_id)
        """
        if not self.book:
            self.load_epub()
            
        if debug:
            self._print_epub_structure()
            
        chapters = []
        
        # Get book's navigation structure
        toc = self.book.toc
        spine = self.book.spine
        
        if debug:
            print(f"\n📖 TOC Structure Analysis:")
            print(f"TOC Type: {type(toc)}")
            print(f"TOC Length: {len(toc) if toc else 0}")
            
        # If TOC structure exists, use TOC
        if toc:
            chapters.extend(self._extract_from_toc(toc, debug))
        else:
            # Otherwise extract from spine
            chapters.extend(self._extract_from_spine(spine, debug))
        
        if debug:
            print(f"\n📊 Chapter Extraction Results:")
            for i, (title, content, chapter_id) in enumerate(chapters):
                print(f"  {i+1}. Title: {title}")
                print(f"     ID: {chapter_id}")
                print(f"     Content Length: {len(content)} characters")
                print(f"     Content Preview: {content[:100].replace(chr(10), ' ')[:50]}...")
                print()
        
        # Check if all chapter contents are identical (common issue)
        if len(chapters) > 1:
            first_content = chapters[0][1]
            if all(chapter[1] == first_content for chapter in chapters):
                print("⚠️  Detected identical content in all chapters, attempting content-based splitting...")
                # Try content-based chapter splitting
                split_chapters = self._split_content_by_headings(first_content, debug)
                if split_chapters:
                    chapters = split_chapters
                    
        return chapters
    
    def _get_item_by_id(self, item_id: str):
        """Get item by ID (compatible with different ebooklib versions)"""
        # Try new version method
        if hasattr(self.book, 'get_item_by_id'):
            return self.book.get_item_by_id(item_id)
        
        # Fallback: iterate through all items
        for item in self.book.get_items():
            if item.get_id() == item_id:
                return item
        return None
    
    def _print_epub_structure(self):
        """Print detailed EPUB file structure information"""
        print(f"\n🔍 EPUB File Structure Analysis:")
        print(f"=" * 60)
        
        # Basic information
        print(f"📚 Book Metadata:")
        metadata = self.book.metadata
        for key, values in metadata.items():
            print(f"  {key}: {[str(v[0]) for v in values]}")
        
        # Spine information
        print(f"\n📄 Spine Structure (Reading Order):")
        for i, (item_id, linear) in enumerate(self.book.spine):
            item = self._get_item_by_id(item_id)
            
            if item:
                print(f"  {i+1}. ID: {item_id}")
                print(f"     Filename: {item.get_name()}")
                print(f"     Type: {item.get_type()}")
                print(f"     Linear: {linear}")
                if item.get_type() == ebooklib.ITEM_DOCUMENT:
                    try:
                        content = item.get_content().decode('utf-8')
                        print(f"     Content Length: {len(content)} characters")
                    except:
                        print(f"     Content Length: Unable to decode")
                print()
            else:
                print(f"  {i+1}. ID: {item_id} (corresponding item not found)")
                print(f"     Linear: {linear}")
                print()
        
        # TOC information
        print(f"\n🔖 Table of Contents (TOC) Structure:")
        self._print_toc_recursive(self.book.toc, level=0)
        
        # All items
        print(f"\n📦 All File Items:")
        for item in self.book.get_items():
            print(f"  ID: {item.get_id()}")
            print(f"  Filename: {item.get_name()}")
            print(f"  Type: {item.get_type()}")
            if item.get_type() == ebooklib.ITEM_DOCUMENT:
                content = item.get_content().decode('utf-8')
                print(f"  Content Length: {len(content)} characters")
            print()
        
        print(f"=" * 60)
    
    def _print_toc_recursive(self, toc_items, level=0):
        """Recursively print TOC structure"""
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
                # Single item
                print(f"{indent}📄 {item.title}")
                print(f"{indent}   href: {item.href}")
    
    def _extract_from_toc(self, toc, debug=False) -> List[Tuple[str, str, str]]:
        """Extract chapters from TOC structure"""
        chapters = []
        
        # First collect all TOC items (flat list, for getting next chapter info)
        all_items = []
        
        def collect_items(item):
            if isinstance(item, tuple):
                section, children = item
                if hasattr(section, 'title') and hasattr(section, 'href'):
                    all_items.append(section)
                if children:
                    for child in children:
                        collect_items(child)
            else:
                if hasattr(item, 'title') and hasattr(item, 'href'):
                    all_items.append(item)
        
        # Collect all items
        for item in toc:
            collect_items(item)
        
        if debug:
            print(f"\n📄 Collected {len(all_items)} TOC items")
        
        # Process each item, passing the next item's href
        for i, item in enumerate(all_items):
            next_href = all_items[i + 1].href if i + 1 < len(all_items) else None
            
            if debug:
                print(f"\nProcessing TOC item: {item.title}")
                print(f"  Current href: {item.href}")
                if next_href:
                    print(f"  Next href: {next_href}")
            
            content = self._get_item_content(item.href, next_href)
            if content:
                title = item.title or f"Chapter {len(chapters) + 1}"
                chapters.append((title, content, item.href))
                if debug:
                    print(f"  ✓ Added chapter: {title} (length: {len(content)})")
            elif debug:
                print(f"  ✗ No content")
            
        return chapters
    
    def _extract_from_spine(self, spine, debug=False) -> List[Tuple[str, str, str]]:
        """Extract chapters from spine"""
        chapters = []
        
        if debug:
            print(f"\n📄 Extracting chapters from Spine:")
        
        for item_id, _ in spine:
            item = self._get_item_by_id(item_id)
            
            if item and item.get_type() == ebooklib.ITEM_DOCUMENT:
                try:
                    content = item.get_content().decode('utf-8')
                    if content.strip():
                        # Try to extract title from content
                        title = self._extract_title_from_content(content) or f"Chapter {len(chapters) + 1}"
                        chapters.append((title, content, item_id))
                        if debug:
                            print(f"  ✓ Added chapter: {title} (ID: {item_id}, length: {len(content)})")
                    elif debug:
                        print(f"  ✗ Empty content: {item_id}")
                except Exception as e:
                    if debug:
                        print(f"  ✗ Decode failed: {item_id} - {e}")
            elif debug:
                if item:
                    print(f"  ✗ Non-document item: {item_id} (type: {item.get_type()})")
                else:
                    print(f"  ✗ Item not found: {item_id}")
                    
        return chapters
    
    def _get_item_content(self, href: str, next_href: Optional[str] = None) -> Optional[str]:
        """
        Get content by href, supports anchor splitting
        
        Args:
            href: Current chapter's link
            next_href: Next chapter's link, used to determine current chapter's end position
        """
        # Separate filename and anchor
        if '#' in href:
            file_name, anchor = href.split('#', 1)
        else:
            file_name, anchor = href, None
        
        # Get complete file content
        full_content = None
        for item in self.book.get_items():
            if item.get_name() == file_name and item.get_type() == ebooklib.ITEM_DOCUMENT:
                full_content = item.get_content().decode('utf-8')
                break
        
        if not full_content:
            return None
        
        # If no anchor, return complete content
        if not anchor:
            return full_content
        
        # If has anchor, try to split content by anchor
        return self._extract_content_by_anchor(full_content, anchor, href, next_href)
    
    def _extract_content_by_anchor(self, content: str, anchor: str, original_href: str, next_href: Optional[str] = None) -> str:
        """
        Extract content segment by anchor
        
        Args:
            content: Complete file content
            anchor: Current anchor
            original_href: Current complete link
            next_href: Next chapter link, used to determine end position
        """
        import re
        
        # Handle filepos type anchor
        if anchor.startswith('filepos'):
            return self._extract_by_filepos(content, anchor, original_href, next_href)
        
        # Handle regular ID anchor
        return self._extract_by_id_anchor(content, anchor)
    
    def _extract_by_filepos(self, content: str, anchor: str, original_href: str, next_href: Optional[str] = None) -> str:
        """
        Extract content by filepos anchor
        
        Args:
            content: Complete file content
            anchor: Current filepos anchor
            original_href: Current complete link
            next_href: Next chapter link
        """
        import re
        
        # Find anchor tag or id attribute containing this filepos
        filepos_pattern = rf'(?:id|name)=["\']?{re.escape(anchor)}["\']?'
        match = re.search(filepos_pattern, content, re.IGNORECASE)
        
        if not match:
            # If exact anchor not found, try smart splitting
            return self._smart_split_content(content, original_href)
        
        # Found anchor position
        start_pos = match.start()
        
        # Determine end position
        end_pos = len(content)
        
        # **KEY FIX**: If next chapter link is provided, use it to determine end position
        if next_href:
            # Parse next chapter's link
            if '#' in next_href:
                next_file, next_anchor = next_href.split('#', 1)
                # Check if in same file
                current_file = original_href.split('#')[0] if '#' in original_href else original_href
                
                if next_file == current_file and next_anchor.startswith('filepos'):
                    # In same file, find next anchor's position
                    next_pattern = rf'(?:id|name)=["\']?{re.escape(next_anchor)}["\']?'
                    next_match = re.search(next_pattern, content, re.IGNORECASE)
                    if next_match:
                        end_pos = next_match.start()
        
        # If next chapter position not found, use original heuristic method to find possible split points
        if end_pos == len(content):
            next_section_patterns = [
                r'<h[1-4][^>]*>',  # Next heading
                r'id=["\']?filepos\d+["\']?',  # Next filepos
                r'<div[^>]*class=["\'][^"\']*chapter[^"\']*["\'][^>]*>',  # Chapter div
            ]
            
            for pattern in next_section_patterns:
                matches = list(re.finditer(pattern, content[start_pos + 100:], re.IGNORECASE))
                if matches:
                    end_pos = start_pos + 100 + matches[0].start()
                    break
        
        extracted = content[start_pos:end_pos].strip()
        return extracted if extracted else content
    
    def _extract_by_id_anchor(self, content: str, anchor: str) -> str:
        """Extract content by ID anchor"""
        import re
        
        # Find element with specified ID
        id_pattern = rf'<[^>]+id=["\']?{re.escape(anchor)}["\']?[^>]*>'
        match = re.search(id_pattern, content, re.IGNORECASE)
        
        if match:
            start_pos = match.start()
            # Find next same-level or higher-level heading
            next_heading = re.search(r'<h[1-4][^>]*>', content[start_pos + len(match.group()):])
            if next_heading:
                end_pos = start_pos + len(match.group()) + next_heading.start()
                return content[start_pos:end_pos].strip()
            else:
                return content[start_pos:].strip()
        
        return content
    
    def _smart_split_content(self, content: str, href: str) -> str:
        """Smart content splitting - fallback when exact anchor cannot be found"""
        # If content is very long, try splitting based on headings
        if len(content) > 10000:  # If content exceeds 10KB
            # Try to find all headings
            import re
            headings = list(re.finditer(r'<h[1-4][^>]*>(.*?)</h[1-4]>', content, re.IGNORECASE | re.DOTALL))
            
            if len(headings) > 1:
                # If multiple headings, return content between first and second heading
                start_pos = headings[0].start()
                end_pos = headings[1].start()
                return content[start_pos:end_pos].strip()
        
        # Default return original content
        return content
    
    def _extract_title_from_content(self, content: str) -> Optional[str]:
        """Extract title from HTML content"""
        # Try to extract h1, h2 heading tags
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
        """Split content into multiple chapters based on headings"""
        chapters = []
        
        # Try multiple heading patterns
        heading_patterns = [
            r'<h[1-3][^>]*>(.*?)</h[1-3]>',  # HTML heading tags
            r'^#+\s+(.+)$',  # Markdown headings
            r'^Chapter\s+\d+[:\s]*(.*)$',  # English chapter headings
            r'^\d+[\.]\s*(.+)$',  # Numbered headings
        ]
        
        # First try HTML heading tag splitting
        html_chapters = self._split_by_html_headings(content)
        if html_chapters:
            return html_chapters
        
        # If HTML splitting fails, try text pattern splitting
        text_chapters = self._split_by_text_patterns(content, heading_patterns)
        if text_chapters:
            return text_chapters
            
        # If all failed, return original content as single chapter
        print("⚠️  Unable to auto-split chapters, will export as single file")
        return [("Complete Content", content, "full_content")]
    
    def _split_by_html_headings(self, content: str) -> List[Tuple[str, str, str]]:
        """Split content based on HTML heading tags"""
        import re
        from html import unescape
        
        chapters = []
        
        # Find all h1-h3 headings
        heading_pattern = r'<h([1-3])[^>]*>(.*?)</h\1>'
        headings = list(re.finditer(heading_pattern, content, re.IGNORECASE | re.DOTALL))
        
        if len(headings) < 2:
            return []
        
        for i, heading in enumerate(headings):
            # Extract heading text
            title_html = heading.group(2)
            title = re.sub(r'<[^>]+>', '', title_html)
            title = unescape(title).strip()
            
            if not title:
                title = f"Chapter {i + 1}"
            
            # Determine chapter content range
            start_pos = heading.start()
            end_pos = headings[i + 1].start() if i + 1 < len(headings) else len(content)
            
            chapter_content = content[start_pos:end_pos].strip()
            
            if chapter_content:
                chapters.append((title, chapter_content, f"chapter_{i + 1}"))
        
        return chapters if len(chapters) > 1 else []
    
    def _split_by_text_patterns(self, content: str, patterns: List[str]) -> List[Tuple[str, str, str]]:
        """Split content based on text patterns"""
        import re
        
        # Remove HTML tags, convert to plain text
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
                
            # Check if heading line
            is_heading = False
            title = None
            
            for pattern in patterns:
                match = re.match(pattern, line, re.IGNORECASE)
                if match:
                    is_heading = True
                    title = match.group(1).strip() if match.groups() else line
                    break
            
            if is_heading and current_chapter:
                # Save previous chapter
                chapter_content = '\n'.join(current_chapter).strip()
                if chapter_content:
                    chapters.append((current_title or f"Chapter {len(chapters) + 1}", 
                                   chapter_content, f"chapter_{len(chapters) + 1}"))
                
                # Start new chapter
                current_chapter = [line]
                current_title = title
            else:
                current_chapter.append(line)
        
        # Save last chapter
        if current_chapter:
            chapter_content = '\n'.join(current_chapter).strip()
            if chapter_content:
                chapters.append((current_title or f"Chapter {len(chapters) + 1}", 
                               chapter_content, f"chapter_{len(chapters) + 1}"))
        
        return chapters if len(chapters) > 1 else []

    def _sanitize_filename(self, filename: str) -> str:
        """Clean filename, remove illegal characters"""
        # Remove or replace illegal characters
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        # Remove extra spaces and dots
        filename = re.sub(r'\s+', ' ', filename).strip()
        filename = filename.strip('.')
        # Limit length
        if len(filename) > 100:
            filename = filename[:100]
        return filename or "untitled"
    
    def export_chapters(self, output_dir: str, format_type: str = 'markdown') -> None:
        """
        Export all chapters
        
        Args:
            output_dir: Output directory
            format_type: Output format ('markdown' or 'txt')
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        chapters = self.get_chapters()
        
        if not chapters:
            print("⚠️  No chapter content found")
            return
        
        print(f"📚 Found {len(chapters)} chapters, starting export...")
        
        # Export image resources
        images_exported = self._export_images(output_path)
        if images_exported:
            print(f"🖼️  Exported {images_exported} image files")
        
        # Create temporary directory for pandoc conversion
        with tempfile.TemporaryDirectory() as temp_dir:
            self.temp_dir = temp_dir
            
            for i, (title, content, chapter_id) in enumerate(chapters, 1):
                try:
                    # Process image links in content
                    processed_content = self._process_image_links(content, format_type)
                    
                    self._export_single_chapter(
                        title, processed_content, i, output_path, format_type
                    )
                except Exception as e:
                    print(f"✗ Failed to export chapter '{title}': {e}")
                    continue
        
        print(f"✅ Export complete! Files saved in: {output_path}")
    
    def _export_images(self, output_path: Path) -> int:
        """Export all images from EPUB, maintaining original directory structure"""
        if not self.book:
            return 0
        
        exported_count = 0
        self.image_mapping = {}  # Store mapping from original path to new path
        
        for item in self.book.get_items():
            if item.get_type() == ebooklib.ITEM_IMAGE:
                try:
                    # Get original image path
                    original_path = item.get_name()
                    
                    # Create complete output path (maintain directory structure)
                    image_output_path = output_path / original_path
                    
                    # Ensure directory exists
                    image_output_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Save image
                    with open(image_output_path, 'wb') as f:
                        f.write(item.get_content())
                    
                    # Record mapping
                    self.image_mapping[original_path] = original_path
                    
                    exported_count += 1
                    print(f"  📷 Exported image: {original_path}")
                    
                except Exception as e:
                    print(f"  ✗ Failed to export image {item.get_name()}: {e}")
        
        return exported_count
    
    def _process_image_links(self, content: str, format_type: str) -> str:
        """Process image links in content"""
        import re
        
        if format_type.lower() != 'markdown':
            return content
        
        # Find all img tags
        img_pattern = r'<img[^>]*src=["\']([^"\']+)["\'][^>]*>'
        
        def replace_img_tag(match):
            img_tag = match.group(0)
            src = match.group(1)
            
            # Clean path (remove ../ etc)
            clean_src = src
            while clean_src.startswith('../'):
                clean_src = clean_src[3:]
            
            # Try to extract alt text
            alt_match = re.search(r'alt=["\']([^"\']*)["\']', img_tag, re.IGNORECASE)
            alt_text = alt_match.group(1) if alt_match else "Image"
            
            # Check if mapping exists
            if hasattr(self, 'image_mapping') and clean_src in self.image_mapping:
                image_path = self.image_mapping[clean_src]
            else:
                # If no mapping, use original path
                image_path = clean_src
            
            # Return Markdown format image link (using relative path)
            return f'![{alt_text}]({image_path})'
        
        # Replace all img tags
        processed_content = re.sub(img_pattern, replace_img_tag, content, flags=re.IGNORECASE)
        
        return processed_content
    
    def _export_single_chapter(self, title: str, content: str, index: int, 
                             output_path: Path, format_type: str) -> None:
        """Export single chapter"""
        # Clean title as filename
        safe_title = self._sanitize_filename(title)
        
        # Generate filename
        if format_type.lower() == 'markdown':
            filename = f"{index:02d}_{safe_title}.md"
            pandoc_format = 'markdown'
        else:
            filename = f"{index:02d}_{safe_title}.txt"
            pandoc_format = 'plain'
        
        output_file = output_path / filename
        
        try:
            # Use pandoc to convert HTML to target format
            converted_content = pypandoc.convert_text(
                content,
                pandoc_format,
                format='html',
                extra_args=['--wrap=none']  # Don't auto wrap
            )
            
            # Write to file
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(converted_content)
            
            print(f"✓ Exported: {filename}")
            
        except Exception as e:
            print(f"✗ Error converting chapter '{title}': {e}")
            # If pandoc conversion fails, try simple HTML tag cleaning
            self._fallback_export(content, output_file, title)
    
    def _fallback_export(self, content: str, output_file: Path, title: str) -> None:
        """Fallback export method (simple HTML tag cleaning)"""
        try:
            # Simple HTML tag cleaning
            import html
            
            # Remove HTML tags
            clean_content = re.sub(r'<[^>]+>', '', content)
            # Decode HTML entities
            clean_content = html.unescape(clean_content)
            # Clean extra whitespace
            clean_content = re.sub(r'\n\s*\n', '\n\n', clean_content)
            clean_content = clean_content.strip()
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(clean_content)
            
            print(f"✓ Exported (fallback method): {output_file.name}")
            
        except Exception as e:
            print(f"✗ Fallback export also failed: {e}")


@click.command()
@click.argument('epub_file', type=click.Path(exists=True))
@click.option('--output', '-o', default=None, 
              help='输出目录 (默认: EPUB文件同目录下的文件名文件夹)')
@click.option('--format', '-f', type=click.Choice(['markdown', 'txt']), 
              default='markdown', help='输出格式 (默认: markdown)')
def main(epub_file: str, output: str, format: str):
    """
    EPUB Chapter Exporter Tool
    
    Export EPUB files chapter by chapter to Markdown or TXT format
    
    Examples:
        python epub_exporter.py book.epub
        python epub_exporter.py book.epub -o ./chapters -f txt
    """
    try:
        print(f"🚀 开始处理 EPUB 文件: {epub_file}")
        
        # If no output directory specified, use EPUB filename (without extension) folder
        if not output:
            epub_path_obj = Path(epub_file)
            epub_name = epub_path_obj.stem  # Get filename without extension
            output = str(epub_path_obj.parent / epub_name)
            print(f"📁 输出目录: {output}")
        
        exporter = EpubExporter(epub_file)
        exporter.export_chapters(output, format)
        
    except Exception as e:
        print(f"❌ 错误: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()