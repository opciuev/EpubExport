#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
研究 ebooklib 的标准 TOC 和 Spine 处理方法
"""

import sys
from pathlib import Path
from ebooklib import epub
import ebooklib

def research_epub_structure(epub_path: str):
    """研究EPUB文件的标准结构处理方法"""
    print(f"🔍 研究 EPUB 文件: {epub_path}")
    print("=" * 60)
    
    try:
        # 加载EPUB文件
        book = epub.read_epub(epub_path)
        print(f"✓ 成功加载 EPUB 文件")
        
        # 1. 研究基本信息
        print(f"\n📚 基本信息:")
        print(f"  标题: {book.get_metadata('DC', 'title')}")
        print(f"  作者: {book.get_metadata('DC', 'creator')}")
        print(f"  语言: {book.get_metadata('DC', 'language')}")
        
        # 2. 研究 TOC 结构
        print(f"\n📑 TOC (目录) 结构:")
        print(f"  TOC 类型: {type(book.toc)}")
        print(f"  TOC 长度: {len(book.toc) if book.toc else 0}")
        
        if book.toc:
            print(f"  TOC 内容:")
            for i, item in enumerate(book.toc):
                print(f"    {i}: {type(item)} - {item}")
                if hasattr(item, 'title'):
                    print(f"        标题: {item.title}")
                if hasattr(item, 'href'):
                    print(f"        链接: {item.href}")
        
        # 3. 研究 Spine 结构
        print(f"\n📄 Spine (阅读顺序) 结构:")
        print(f"  Spine 类型: {type(book.spine)}")
        print(f"  Spine 长度: {len(book.spine) if book.spine else 0}")
        
        if book.spine:
            print(f"  Spine 内容:")
            for i, (item_id, linear) in enumerate(book.spine):
                print(f"    {i}: ID={item_id}, Linear={linear}")
                # 获取对应的项目
                item = book.get_item_with_id(item_id)
                if item:
                    print(f"        文件名: {item.get_name()}")
                    print(f"        类型: {item.get_type()}")
                    if item.get_type() == ebooklib.ITEM_DOCUMENT:
                        content = item.get_content()
                        print(f"        内容长度: {len(content)} 字节")
        
        # 4. 研究所有文档项目
        print(f"\n📦 所有文档项目:")
        doc_items = list(book.get_items_of_type(ebooklib.ITEM_DOCUMENT))
        print(f"  文档项目数量: {len(doc_items)}")
        
        for i, item in enumerate(doc_items):
            print(f"    {i}: {item.get_id()} - {item.get_name()}")
            content = item.get_content()
            print(f"        内容长度: {len(content)} 字节")
        
        # 5. 研究 TOC 与实际内容的对应关系
        print(f"\n🔗 TOC 与内容的对应关系:")
        if book.toc:
            for i, toc_item in enumerate(book.toc):
                if hasattr(toc_item, 'href'):
                    href = toc_item.href
                    print(f"  TOC {i}: {toc_item.title} -> {href}")
                    
                    # 分析href
                    if '#' in href:
                        file_name, anchor = href.split('#', 1)
                        print(f"    文件: {file_name}, 锚点: {anchor}")
                    else:
                        file_name, anchor = href, None
                        print(f"    文件: {file_name}, 无锚点")
                    
                    # 查找对应的文档项目
                    matching_item = None
                    for item in doc_items:
                        if item.get_name() == file_name:
                            matching_item = item
                            break
                    
                    if matching_item:
                        content = matching_item.get_content().decode('utf-8')
                        print(f"    对应文档长度: {len(content)} 字符")
                        
                        # 如果有锚点，尝试分析
                        if anchor:
                            print(f"    锚点分析: {anchor}")
                            if anchor in content:
                                print(f"      ✓ 在内容中找到锚点")
                            else:
                                print(f"      ❌ 在内容中未找到锚点")
                    else:
                        print(f"    ❌ 未找到对应的文档项目")
        
        return True
        
    except Exception as e:
        print(f"❌ 研究失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主函数"""
    if len(sys.argv) != 2:
        print("用法: python research_ebooklib.py <epub文件路径>")
        sys.exit(1)
    
    epub_path = sys.argv[1]
    
    if not Path(epub_path).exists():
        print(f"❌ 文件不存在: {epub_path}")
        sys.exit(1)
    
    success = research_epub_structure(epub_path)
    
    if success:
        print(f"\n✅ 研究完成")
    else:
        print(f"\n❌ 研究失败")
        sys.exit(1)

if __name__ == "__main__":
    main()
