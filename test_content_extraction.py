#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试内容提取改进的脚本
用于验证根据书签分隔内容后是否还会出现内容变少的问题
"""

import sys
from pathlib import Path
from epub_exporter import EpubExporter

def test_content_extraction(epub_path: str):
    """测试内容提取功能"""
    print(f"🧪 测试 EPUB 文件: {epub_path}")
    print("=" * 60)
    
    try:
        # 创建导出器
        exporter = EpubExporter(epub_path)
        
        # 获取章节（启用调试模式）
        print("\n📖 获取章节信息（调试模式）:")
        chapters = exporter.get_chapters(debug=True)
        
        print(f"\n📊 章节统计:")
        print(f"总章节数: {len(chapters)}")
        
        total_content_length = 0
        for i, (title, content, chapter_id) in enumerate(chapters, 1):
            content_length = len(content)
            total_content_length += content_length
            print(f"  {i:2d}. {title[:50]:<50} | {content_length:>8,} 字符")
        
        print(f"\n总内容长度: {total_content_length:,} 字符")
        
        # 检查是否有异常短的章节
        print(f"\n🔍 内容长度分析:")
        short_chapters = []
        long_chapters = []
        
        for i, (title, content, chapter_id) in enumerate(chapters, 1):
            content_length = len(content)
            if content_length < 1000:  # 少于1000字符的章节
                short_chapters.append((i, title, content_length))
            elif content_length > 50000:  # 超过50000字符的章节
                long_chapters.append((i, title, content_length))
        
        if short_chapters:
            print(f"⚠️  发现 {len(short_chapters)} 个可能过短的章节:")
            for i, title, length in short_chapters:
                print(f"    {i:2d}. {title[:40]:<40} | {length:>6,} 字符")
        
        if long_chapters:
            print(f"📚 发现 {len(long_chapters)} 个较长的章节:")
            for i, title, length in long_chapters:
                print(f"    {i:2d}. {title[:40]:<40} | {length:>6,} 字符")
        
        if not short_chapters and not long_chapters:
            print("✅ 所有章节长度都在合理范围内")
        
        # 检查内容重复
        print(f"\n🔄 检查内容重复:")
        content_hashes = {}
        duplicate_chapters = []
        
        for i, (title, content, chapter_id) in enumerate(chapters, 1):
            content_hash = hash(content[:1000])  # 使用前1000字符的哈希
            if content_hash in content_hashes:
                duplicate_chapters.append((i, title, content_hashes[content_hash]))
            else:
                content_hashes[content_hash] = (i, title)
        
        if duplicate_chapters:
            print(f"⚠️  发现 {len(duplicate_chapters)} 个可能重复的章节:")
            for i, title, (orig_i, orig_title) in duplicate_chapters:
                print(f"    {i:2d}. {title[:30]:<30} 与 {orig_i:2d}. {orig_title[:30]:<30} 相似")
        else:
            print("✅ 未发现重复内容")
            
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主函数"""
    if len(sys.argv) != 2:
        print("用法: python test_content_extraction.py <epub文件路径>")
        sys.exit(1)
    
    epub_path = sys.argv[1]
    
    if not Path(epub_path).exists():
        print(f"❌ 文件不存在: {epub_path}")
        sys.exit(1)
    
    success = test_content_extraction(epub_path)
    
    if success:
        print(f"\n✅ 测试完成")
    else:
        print(f"\n❌ 测试失败")
        sys.exit(1)

if __name__ == "__main__":
    main()
