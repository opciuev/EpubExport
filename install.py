#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EPUB 导出工具安装脚本
自动检查和安装依赖
"""

import subprocess
import sys
import os
from pathlib import Path

def check_python_version():
    """检查 Python 版本"""
    if sys.version_info < (3, 6):
        print("错误: 需要 Python 3.6 或更高版本")
        print(f"当前版本: {sys.version}")
        return False
    print(f"成功: Python 版本: {sys.version.split()[0]}")
    return True

def check_pandoc():
    """检查 Pandoc 是否已安装"""
    try:
        result = subprocess.run(['pandoc', '--version'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            version_line = result.stdout.split('\n')[0]
            print(f"成功: {version_line}")
            return True
    except FileNotFoundError:
        pass
    
    print("错误: Pandoc 未安装")
    print("\n请安装 Pandoc:")
    print("  macOS:    brew install pandoc")
    print("  Ubuntu:   sudo apt-get install pandoc")
    print("  Windows:  从 https://pandoc.org/installing.html 下载")
    return False

def install_requirements():
    """安装 Python 依赖包"""
    requirements_file = Path(__file__).parent / "requirements.txt"
    
    if not requirements_file.exists():
        print("错误: requirements.txt 文件不存在")
        return False
    
    print("\n正在安装 Python 依赖包...")
    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "-r", str(requirements_file)
        ])
        print("成功: Python 依赖包安装完成")
        return True
    except subprocess.CalledProcessError as e:
        print(f"错误: 安装依赖包失败: {e}")
        return False

def test_imports():
    """测试导入关键模块"""
    modules = [
        ('ebooklib', 'EPUB 解析'),
        ('pypandoc', 'Pandoc 接口'),
        ('tkinter', 'GUI 界面'),
        ('click', '命令行界面')
    ]
    
    print("\n测试模块导入...")
    all_ok = True
    
    for module, description in modules:
        try:
            if module == 'tkinter':
                import tkinter
            else:
                __import__(module)
            print(f"成功: {module} ({description})")
        except ImportError as e:
            print(f"错误: {module} ({description}) - {e}")
            all_ok = False
    
    return all_ok

def main():
    """主安装流程"""
    print("EPUB 导出工具安装检查")
    print("=" * 50)
    
    # 检查 Python 版本
    if not check_python_version():
        return False
    
    # 检查 Pandoc
    pandoc_ok = check_pandoc()
    
    # 安装 Python 依赖
    deps_ok = install_requirements()
    
    # 测试导入
    imports_ok = test_imports()
    
    print("\n" + "=" * 50)
    
    if pandoc_ok and deps_ok and imports_ok:
        print("安装检查完成！所有依赖都已就绪")
        print("\n启动方式:")
        print("  图形界面: python run_gui.py")
        print("  命令行:   python epub_exporter.py --help")
        return True
    else:
        print("警告: 安装检查发现问题，请解决后重试")
        if not pandoc_ok:
            print("  - 需要安装 Pandoc")
        if not deps_ok:
            print("  - Python 依赖包安装失败")
        if not imports_ok:
            print("  - 模块导入测试失败")
        return False

if __name__ == "__main__":
    success = main()
    
    if not success:
        input("\n按回车键退出...")
        sys.exit(1)
