#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EPUB 导出工具 GUI 启动器
"""

import sys
import os
from pathlib import Path

def main():
    """启动 GUI 应用"""
    try:
        # 添加当前目录到 Python 路径
        current_dir = Path(__file__).parent
        sys.path.insert(0, str(current_dir))
        
        # 导入并运行 GUI
        from epub_gui import main as gui_main
        gui_main()
        
    except ImportError as e:
        print(f"❌ 导入错误: {e}")
        print("\n请确保已安装所有依赖包:")
        print("pip install -r requirements.txt")
        input("\n按回车键退出...")
        
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        input("\n按回车键退出...")

if __name__ == "__main__":
    main()
