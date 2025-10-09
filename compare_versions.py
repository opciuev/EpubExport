#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
对比 EPUB 导出工具 v1 和 v2 的结果
用于验证新版本是否解决了内容变少的问题
"""

import sys
from pathlib import Path
from epub_exporter import EpubExporter  # v1
from epub_exporter_v2 import EpubExporterV2  # v2


def compare_extractors(epub_path: str):
    """对比两个版本的提取结果"""
    print(f"🔍 对比分析 EPUB 文件: {epub_path}")
    print("=" * 80)
    
    try:
        # 创建两个版本的导出器
        print("📚 初始化导出器...")
        exporter_v1 = EpubExporter(epub_path)
        exporter_v2 = EpubExporterV2(epub_path)
        
        # 获取章节（不启用调试模式，避免输出混乱）
        print("\n🔄 提取章节内容...")
        print("  v1 提取中...")
        chapters_v1 = exporter_v1.get_chapters(debug=False)
        
        print("  v2 提取中...")
        chapters_v2 = exporter_v2.get_chapters(debug=False)
        
        # 基本统计对比
        print(f"\n📊 基本统计对比:")
        print(f"{'指标':<20} {'v1':<15} {'v2':<15} {'差异':<15}")
        print("-" * 65)
        
        v1_count = len(chapters_v1)
        v2_count = len(chapters_v2)
        print(f"{'章节数量':<20} {v1_count:<15} {v2_count:<15} {v2_count - v1_count:+d}")
        
        v1_total_length = sum(len(content) for _, content, _ in chapters_v1)
        v2_total_length = sum(len(content) for _, content, _ in chapters_v2)
        print(f"{'总内容长度':<20} {v1_total_length:<15,} {v2_total_length:<15,} {v2_total_length - v1_total_length:+,}")
        
        if v1_total_length > 0:
            length_ratio = (v2_total_length / v1_total_length) * 100
            print(f"{'内容保留率':<20} {'100.0%':<15} {length_ratio:<15.1f}% {length_ratio - 100:+.1f}%")
        
        # 详细章节对比
        print(f"\n📋 详细章节对比:")
        print(f"{'序号':<4} {'版本':<4} {'章节标题':<40} {'内容长度':<12} {'章节ID':<20}")
        print("-" * 80)
        
        max_chapters = max(len(chapters_v1), len(chapters_v2))
        
        for i in range(max_chapters):
            # v1 章节
            if i < len(chapters_v1):
                title_v1, content_v1, id_v1 = chapters_v1[i]
                print(f"{i+1:<4} {'v1':<4} {title_v1[:40]:<40} {len(content_v1):<12,} {id_v1[:20]:<20}")
            else:
                print(f"{i+1:<4} {'v1':<4} {'(无)':<40} {'0':<12} {'(无)':<20}")
            
            # v2 章节
            if i < len(chapters_v2):
                title_v2, content_v2, id_v2 = chapters_v2[i]
                print(f"{'':<4} {'v2':<4} {title_v2[:40]:<40} {len(content_v2):<12,} {id_v2[:20]:<20}")
            else:
                print(f"{'':<4} {'v2':<4} {'(无)':<40} {'0':<12} {'(无)':<20}")
            
            # 如果两个版本都有这个章节，显示差异
            if i < len(chapters_v1) and i < len(chapters_v2):
                length_diff = len(chapters_v2[i][1]) - len(chapters_v1[i][1])
                if length_diff != 0:
                    print(f"{'':<4} {'差异':<4} {'':<40} {length_diff:+,} {'字符':<20}")
            
            print()  # 空行分隔
        
        # 内容重复检查
        print(f"\n🔄 内容重复检查:")
        
        # v1 重复检查
        v1_duplicates = find_duplicates(chapters_v1)
        if v1_duplicates:
            print(f"  v1 发现 {len(v1_duplicates)} 组重复内容:")
            for i, (indices, sample) in enumerate(v1_duplicates):
                print(f"    组 {i+1}: 章节 {', '.join(map(str, indices))} - {sample[:50]}...")
        else:
            print(f"  v1 未发现重复内容")
        
        # v2 重复检查
        v2_duplicates = find_duplicates(chapters_v2)
        if v2_duplicates:
            print(f"  v2 发现 {len(v2_duplicates)} 组重复内容:")
            for i, (indices, sample) in enumerate(v2_duplicates):
                print(f"    组 {i+1}: 章节 {', '.join(map(str, indices))} - {sample[:50]}...")
        else:
            print(f"  v2 未发现重复内容")
        
        # 异常章节检查
        print(f"\n⚠️  异常章节检查:")
        
        # 检查过短的章节
        short_threshold = 500
        v1_short = [(i+1, title, len(content)) for i, (title, content, _) in enumerate(chapters_v1) if len(content) < short_threshold]
        v2_short = [(i+1, title, len(content)) for i, (title, content, _) in enumerate(chapters_v2) if len(content) < short_threshold]
        
        print(f"  过短章节 (< {short_threshold} 字符):")
        print(f"    v1: {len(v1_short)} 个")
        for idx, title, length in v1_short:
            print(f"      {idx}. {title[:30]} ({length} 字符)")
        
        print(f"    v2: {len(v2_short)} 个")
        for idx, title, length in v2_short:
            print(f"      {idx}. {title[:30]} ({length} 字符)")
        
        # 检查过长的章节
        long_threshold = 100000
        v1_long = [(i+1, title, len(content)) for i, (title, content, _) in enumerate(chapters_v1) if len(content) > long_threshold]
        v2_long = [(i+1, title, len(content)) for i, (title, content, _) in enumerate(chapters_v2) if len(content) > long_threshold]
        
        print(f"  过长章节 (> {long_threshold:,} 字符):")
        print(f"    v1: {len(v1_long)} 个")
        for idx, title, length in v1_long:
            print(f"      {idx}. {title[:30]} ({length:,} 字符)")
        
        print(f"    v2: {len(v2_long)} 个")
        for idx, title, length in v2_long:
            print(f"      {idx}. {title[:30]} ({length:,} 字符)")
        
        # 总结
        print(f"\n📝 对比总结:")
        
        if v2_total_length > v1_total_length:
            improvement = ((v2_total_length - v1_total_length) / v1_total_length) * 100
            print(f"  ✅ v2 内容更多，增加了 {improvement:.1f}% 的内容")
        elif v2_total_length < v1_total_length:
            reduction = ((v1_total_length - v2_total_length) / v1_total_length) * 100
            print(f"  ⚠️  v2 内容减少了 {reduction:.1f}%")
        else:
            print(f"  ➡️  两版本内容总量相同")
        
        if len(v2_short) < len(v1_short):
            print(f"  ✅ v2 减少了 {len(v1_short) - len(v2_short)} 个过短章节")
        elif len(v2_short) > len(v1_short):
            print(f"  ⚠️  v2 增加了 {len(v2_short) - len(v1_short)} 个过短章节")
        
        if len(v2_duplicates) < len(v1_duplicates):
            print(f"  ✅ v2 减少了 {len(v1_duplicates) - len(v2_duplicates)} 组重复内容")
        elif len(v2_duplicates) > len(v1_duplicates):
            print(f"  ⚠️  v2 增加了 {len(v2_duplicates) - len(v1_duplicates)} 组重复内容")
        
        return True
        
    except Exception as e:
        print(f"❌ 对比失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def find_duplicates(chapters):
    """查找重复的章节内容"""
    content_groups = {}
    
    for i, (title, content, chapter_id) in enumerate(chapters):
        # 使用前1000字符的哈希来检测重复
        content_hash = hash(content[:1000])
        
        if content_hash in content_groups:
            content_groups[content_hash].append(i + 1)
        else:
            content_groups[content_hash] = [i + 1]
    
    # 返回有多个章节的组
    duplicates = []
    for content_hash, indices in content_groups.items():
        if len(indices) > 1:
            # 获取样本内容
            sample_content = chapters[indices[0] - 1][1][:100]
            duplicates.append((indices, sample_content))
    
    return duplicates


def main():
    """主函数"""
    if len(sys.argv) != 2:
        print("用法: python compare_versions.py <epub文件路径>")
        sys.exit(1)
    
    epub_path = sys.argv[1]
    
    if not Path(epub_path).exists():
        print(f"❌ 文件不存在: {epub_path}")
        sys.exit(1)
    
    success = compare_extractors(epub_path)
    
    if success:
        print(f"\n✅ 对比完成")
    else:
        print(f"\n❌ 对比失败")
        sys.exit(1)


if __name__ == "__main__":
    main()
