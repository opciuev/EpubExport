#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EPUB 章节导出工具 - 图形用户界面
使用 tkinter 创建的现代化 GUI 界面
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import os
import sys
from pathlib import Path
from epub_exporter import EpubExporter
import queue
import time


class EpubExporterGUI:
    """EPUB 导出工具图形界面"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("EPUB 章节导出工具")
        self.root.geometry("800x600")
        self.root.minsize(600, 400)
        
        # 设置图标和样式
        self.setup_styles()
        
        # 变量
        self.epub_file_path = tk.StringVar()
        self.output_dir_path = tk.StringVar(value="")  # 默认为空
        self.export_format = tk.StringVar(value="markdown")
        self.progress_var = tk.DoubleVar()
        self.status_var = tk.StringVar(value="就绪")
        
        # 消息队列用于线程间通信
        self.message_queue = queue.Queue()
        
        # 创建界面
        self.create_widgets()
        
        # 启动消息处理
        self.process_queue()
        
    def setup_styles(self):
        """设置界面样式"""
        style = ttk.Style()
        
        # 设置主题
        try:
            style.theme_use('clam')
        except:
            pass
            
        # 自定义样式
        style.configure('Title.TLabel', font=('Arial', 16, 'bold'))
        style.configure('Heading.TLabel', font=('Arial', 12, 'bold'))
        style.configure('Success.TLabel', foreground='green')
        style.configure('Error.TLabel', foreground='red')
        
    def create_widgets(self):
        """创建界面组件"""
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # 标题
        title_label = ttk.Label(main_frame, text="📚 EPUB 章节导出工具", style='Title.TLabel')
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # 文件选择区域
        self.create_file_selection_area(main_frame, 1)
        
        # 输出设置区域
        self.create_output_settings_area(main_frame, 2)
        
        # 章节预览区域
        self.create_preview_area(main_frame, 3)
        
        # 控制按钮区域
        self.create_control_area(main_frame, 4)
        
        # 进度条和状态
        self.create_progress_area(main_frame, 5)
        
        # 日志输出区域
        self.create_log_area(main_frame, 6)
        
    def create_file_selection_area(self, parent, row):
        """创建文件选择区域"""
        # 文件选择框架
        file_frame = ttk.LabelFrame(parent, text="📁 选择 EPUB 文件", padding="10")
        file_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        file_frame.columnconfigure(1, weight=1)
        
        # EPUB 文件选择
        ttk.Label(file_frame, text="EPUB 文件:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        
        epub_entry = ttk.Entry(file_frame, textvariable=self.epub_file_path, width=50)
        epub_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 10))
        
        browse_btn = ttk.Button(file_frame, text="浏览...", command=self.browse_epub_file)
        browse_btn.grid(row=0, column=2)
        
    def create_output_settings_area(self, parent, row):
        """创建输出设置区域"""
        # 输出设置框架
        output_frame = ttk.LabelFrame(parent, text="⚙️ 输出设置", padding="10")
        output_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        output_frame.columnconfigure(1, weight=1)
        
        # 输出目录
        ttk.Label(output_frame, text="输出目录:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        
        output_entry = ttk.Entry(output_frame, textvariable=self.output_dir_path, width=50)
        output_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 10))
        
        output_browse_btn = ttk.Button(output_frame, text="浏览...", command=self.browse_output_dir)
        output_browse_btn.grid(row=0, column=2)
        
        # 输出格式
        ttk.Label(output_frame, text="输出格式:").grid(row=1, column=0, sticky=tk.W, padx=(0, 10), pady=(10, 0))
        
        format_frame = ttk.Frame(output_frame)
        format_frame.grid(row=1, column=1, sticky=tk.W, pady=(10, 0))
        
        ttk.Radiobutton(format_frame, text="Markdown (.md)", variable=self.export_format, 
                       value="markdown").pack(side=tk.LEFT, padx=(0, 20))
        ttk.Radiobutton(format_frame, text="纯文本 (.txt)", variable=self.export_format, 
                       value="txt").pack(side=tk.LEFT)
        
    def create_preview_area(self, parent, row):
        """创建章节预览区域"""
        # 预览框架
        preview_frame = ttk.LabelFrame(parent, text="👀 章节预览", padding="10")
        preview_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        preview_frame.columnconfigure(0, weight=1)
        preview_frame.rowconfigure(1, weight=1)
        
        # 预览控制
        preview_control_frame = ttk.Frame(preview_frame)
        preview_control_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.preview_btn = ttk.Button(preview_control_frame, text="🔍 预览章节", 
                                     command=self.preview_chapters)
        self.preview_btn.pack(side=tk.LEFT)
        
        self.chapter_count_label = ttk.Label(preview_control_frame, text="")
        self.chapter_count_label.pack(side=tk.LEFT, padx=(20, 0))
        
        # 章节列表
        self.create_chapter_list(preview_frame, 1)
        
        # 调试按钮
        debug_btn = ttk.Button(preview_control_frame, text="🔍 调试分析", 
                              command=self.debug_epub_structure)
        debug_btn.pack(side=tk.LEFT, padx=(10, 0))
        
    def create_chapter_list(self, parent, row):
        """创建章节列表"""
        # 创建框架来包含选择控制和列表
        list_frame = ttk.Frame(parent)
        list_frame.grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(1, weight=1)
        
        # 选择控制
        select_frame = ttk.Frame(list_frame)
        select_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        
        ttk.Button(select_frame, text="全选", command=self.select_all_chapters).pack(side=tk.LEFT)
        ttk.Button(select_frame, text="全不选", command=self.deselect_all_chapters).pack(side=tk.LEFT, padx=(5, 0))
        ttk.Button(select_frame, text="反选", command=self.invert_chapter_selection).pack(side=tk.LEFT, padx=(5, 0))
        
        # 创建 Treeview 用于显示章节
        columns = ('选择', '序号', '章节标题', '内容长度')
        self.chapter_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=8)
        
        # 设置列标题
        for col in columns:
            self.chapter_tree.heading(col, text=col)
            
        # 设置列宽
        self.chapter_tree.column('选择', width=50, anchor=tk.CENTER)
        self.chapter_tree.column('序号', width=60, anchor=tk.CENTER)
        self.chapter_tree.column('章节标题', width=250, anchor=tk.W)
        self.chapter_tree.column('内容长度', width=100, anchor=tk.CENTER)
        
        # 绑定双击事件来切换选择状态
        self.chapter_tree.bind('<Double-1>', self.toggle_chapter_selection)
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.chapter_tree.yview)
        self.chapter_tree.configure(yscrollcommand=scrollbar.set)
        
        # 布局
        self.chapter_tree.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=1, column=1, sticky=(tk.N, tk.S))
        
        # 存储章节选择状态
        self.chapter_selections = {}
        
    def create_control_area(self, parent, row):
        """创建控制按钮区域"""
        control_frame = ttk.Frame(parent)
        control_frame.grid(row=row, column=0, columnspan=3, pady=(10, 0))
        
        # 导出按钮
        self.export_btn = ttk.Button(control_frame, text="🚀 开始导出", 
                                    command=self.start_export, style='Accent.TButton')
        self.export_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # 停止按钮
        self.stop_btn = ttk.Button(control_frame, text="⏹️ 停止", 
                                  command=self.stop_export, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # 清除按钮
        clear_btn = ttk.Button(control_frame, text="🗑️ 清除", command=self.clear_all)
        clear_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # 关于按钮
        about_btn = ttk.Button(control_frame, text="ℹ️ 关于", command=self.show_about)
        about_btn.pack(side=tk.RIGHT)
        
    def create_progress_area(self, parent, row):
        """创建进度条和状态区域"""
        progress_frame = ttk.Frame(parent)
        progress_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(10, 0))
        progress_frame.columnconfigure(0, weight=1)
        
        # 进度条
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, 
                                          maximum=100, length=400)
        self.progress_bar.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 10))
        
        # 状态标签
        self.status_label = ttk.Label(progress_frame, textvariable=self.status_var)
        self.status_label.grid(row=0, column=1)
        
    def create_log_area(self, parent, row):
        """创建日志输出区域"""
        log_frame = ttk.LabelFrame(parent, text="📋 输出日志", padding="5")
        log_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(10, 0))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        # 日志文本框
        self.log_text = scrolledtext.ScrolledText(log_frame, height=8, wrap=tk.WORD)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置主框架的行权重
        parent.rowconfigure(row, weight=1)
        
    def browse_epub_file(self):
        """浏览选择 EPUB 文件"""
        # 确定初始目录
        initial_dir = None
        
        # 如果已经选择过文件，从该文件的目录开始
        current_epub = self.epub_file_path.get()
        if current_epub and Path(current_epub).exists():
            initial_dir = str(Path(current_epub).parent)
        
        # 如果设置了输出目录，也可以从那里开始
        elif self.output_dir_path.get():
            output_path = Path(self.output_dir_path.get())
            if output_path.exists():
                initial_dir = str(output_path)
            elif output_path.parent.exists():
                initial_dir = str(output_path.parent)
        
        # 打开文件选择对话框
        if initial_dir:
            file_path = filedialog.askopenfilename(
                title="选择 EPUB 文件",
                initialdir=initial_dir,
                filetypes=[("EPUB 文件", "*.epub"), ("所有文件", "*.*")]
            )
        else:
            file_path = filedialog.askopenfilename(
                title="选择 EPUB 文件",
                filetypes=[("EPUB 文件", "*.epub"), ("所有文件", "*.*")]
            )
        if file_path:
            self.epub_file_path.set(file_path)
            
            # 自动设置输出目录为 EPUB 文件同目录
            epub_dir = Path(file_path).parent
            if not self.output_dir_path.get():  # 只有当输出目录为空时才自动设置
                self.output_dir_path.set(str(epub_dir))
                self.log(f"已选择文件: {Path(file_path).name}")
                self.log(f"输出目录已设置为: {epub_dir}")
            else:
                self.log(f"已选择文件: {Path(file_path).name}")
            
    def browse_output_dir(self):
        """浏览选择输出目录"""
        # 确定初始目录
        initial_dir = None
        
        # 如果已经选择了 EPUB 文件，从该文件的目录开始
        epub_path = self.epub_file_path.get()
        if epub_path and Path(epub_path).exists():
            initial_dir = str(Path(epub_path).parent)
        
        # 如果已经设置了输出目录，从该目录开始
        elif self.output_dir_path.get():
            current_output = Path(self.output_dir_path.get())
            if current_output.exists():
                initial_dir = str(current_output)
            elif current_output.parent.exists():
                initial_dir = str(current_output.parent)
        
        # 打开文件夹选择对话框
        if initial_dir:
            dir_path = filedialog.askdirectory(title="选择输出目录", initialdir=initial_dir)
        else:
            dir_path = filedialog.askdirectory(title="选择输出目录")
            
        if dir_path:
            self.output_dir_path.set(dir_path)
            self.log(f"输出目录: {dir_path}")
            
    def preview_chapters(self):
        """预览章节"""
        epub_path = self.epub_file_path.get()
        if not epub_path:
            messagebox.showwarning("警告", "请先选择 EPUB 文件")
            return
            
        if not Path(epub_path).exists():
            messagebox.showerror("错误", "EPUB 文件不存在")
            return
            
        try:
            self.log("正在加载 EPUB 文件...")
            self.status_var.set("加载中...")
            
            # 在后台线程中加载章节
            threading.Thread(target=self._load_chapters_thread, 
                           args=(epub_path,), daemon=True).start()
            
        except Exception as e:
            self.log(f"预览失败: {e}")
            messagebox.showerror("错误", f"预览失败: {e}")
            
    def _load_chapters_thread(self, epub_path):
        """在后台线程中加载章节"""
        try:
            exporter = EpubExporter(epub_path)
            chapters = exporter.get_chapters()
            
            # 通过队列发送结果
            self.message_queue.put(('chapters_loaded', chapters))
            
        except Exception as e:
            self.message_queue.put(('error', f"加载章节失败: {e}"))
            
    def update_chapter_list(self, chapters):
        """更新章节列表显示"""
        # 清空现有项目
        for item in self.chapter_tree.get_children():
            self.chapter_tree.delete(item)
        
        # 重置选择状态
        self.chapter_selections = {}
        self.chapters_data = chapters  # 保存章节数据
            
        # 添加章节
        for i, (title, content, chapter_id) in enumerate(chapters, 1):
            content_length = f"{len(content):,} 字符"
            item_id = self.chapter_tree.insert('', 'end', values=("☐", i, title, content_length))
            self.chapter_selections[item_id] = False  # 默认未选择
            
        self.chapter_count_label.config(text=f"共找到 {len(chapters)} 个章节")
        self.log(f"预览完成，共 {len(chapters)} 个章节")
        self.status_var.set("预览完成")
    
    def toggle_chapter_selection(self, event):
        """切换章节选择状态"""
        item = self.chapter_tree.selection()[0] if self.chapter_tree.selection() else None
        if item:
            current_state = self.chapter_selections.get(item, False)
            new_state = not current_state
            self.chapter_selections[item] = new_state
            
            # 更新显示
            values = list(self.chapter_tree.item(item, 'values'))
            values[0] = "☑" if new_state else "☐"
            self.chapter_tree.item(item, values=values)
    
    def select_all_chapters(self):
        """全选章节"""
        for item in self.chapter_tree.get_children():
            self.chapter_selections[item] = True
            values = list(self.chapter_tree.item(item, 'values'))
            values[0] = "☑"
            self.chapter_tree.item(item, values=values)
    
    def deselect_all_chapters(self):
        """全不选章节"""
        for item in self.chapter_tree.get_children():
            self.chapter_selections[item] = False
            values = list(self.chapter_tree.item(item, 'values'))
            values[0] = "☐"
            self.chapter_tree.item(item, values=values)
    
    def invert_chapter_selection(self):
        """反选章节"""
        for item in self.chapter_tree.get_children():
            current_state = self.chapter_selections.get(item, False)
            new_state = not current_state
            self.chapter_selections[item] = new_state
            values = list(self.chapter_tree.item(item, 'values'))
            values[0] = "☑" if new_state else "☐"
            self.chapter_tree.item(item, values=values)
    
    def get_selected_chapters(self):
        """获取选中的章节"""
        selected_chapters = []
        for item in self.chapter_tree.get_children():
            if self.chapter_selections.get(item, False):
                values = self.chapter_tree.item(item, 'values')
                chapter_index = int(values[1]) - 1  # 转换为0基索引
                if hasattr(self, 'chapters_data') and chapter_index < len(self.chapters_data):
                    selected_chapters.append(self.chapters_data[chapter_index])
        return selected_chapters
    
    def debug_epub_structure(self):
        """调试 EPUB 结构"""
        epub_path = self.epub_file_path.get()
        if not epub_path:
            messagebox.showwarning("警告", "请先选择 EPUB 文件")
            return
            
        if not Path(epub_path).exists():
            messagebox.showerror("错误", "EPUB 文件不存在")
            return
            
        try:
            self.log("开始调试分析 EPUB 结构...")
            
            # 在后台线程中进行调试分析
            threading.Thread(target=self._debug_epub_thread, 
                           args=(epub_path,), daemon=True).start()
            
        except Exception as e:
            self.log(f"调试分析失败: {e}")
            messagebox.showerror("错误", f"调试分析失败: {e}")
    
    def _debug_epub_thread(self, epub_path):
        """在后台线程中进行调试分析"""
        try:
            exporter = EpubExporter(epub_path)
            
            # 获取章节并启用调试模式
            self.message_queue.put(('log', "正在进行详细的 EPUB 结构分析..."))
            chapters = exporter.get_chapters(debug=True)
            
            self.message_queue.put(('log', "调试分析完成！请查看终端输出获取详细信息。"))
            
        except Exception as e:
            self.message_queue.put(('error', f"调试分析失败: {e}"))
        
    def start_export(self):
        """开始导出"""
        epub_path = self.epub_file_path.get()
        output_dir = self.output_dir_path.get()
        export_format = self.export_format.get()
        
        # 验证输入
        if not epub_path:
            messagebox.showwarning("警告", "请先选择 EPUB 文件")
            return
            
        if not Path(epub_path).exists():
            messagebox.showerror("错误", "EPUB 文件不存在")
            return
            
        # 如果输出目录为空，使用 EPUB 文件同目录
        if not output_dir:
            output_dir = str(Path(epub_path).parent)
            self.output_dir_path.set(output_dir)
            self.log(f"使用默认输出目录: {output_dir}")
            
        # 更新界面状态
        self.export_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.progress_var.set(0)
        self.status_var.set("导出中...")
        
        # 清空日志
        self.log_text.delete(1.0, tk.END)
        self.log("开始导出...")
        
        # 在后台线程中执行导出
        self.export_thread = threading.Thread(
            target=self._export_thread,
            args=(epub_path, output_dir, export_format),
            daemon=True
        )
        self.export_thread.start()
        
    def _export_thread(self, epub_path, output_dir, export_format):
        """在后台线程中执行导出"""
        try:
            exporter = EpubExporter(epub_path)
            
            # 获取要导出的章节
            self.message_queue.put(('log', "正在解析 EPUB 文件..."))
            
            # 检查是否有选中的章节
            selected_chapters = self.get_selected_chapters()
            if selected_chapters:
                chapters = selected_chapters
                self.message_queue.put(('log', f"将导出选中的 {len(chapters)} 个章节"))
            else:
                # 如果没有选中任何章节，导出所有章节
                chapters = exporter.get_chapters()
                self.message_queue.put(('log', f"未选择特定章节，将导出所有 {len(chapters)} 个章节"))
            
            if not chapters:
                self.message_queue.put(('error', "未找到任何章节"))
                return
            
            # 创建输出目录
            Path(output_dir).mkdir(parents=True, exist_ok=True)
            
            # 导出图片资源
            self.message_queue.put(('log', "正在导出图片资源..."))
            try:
                images_exported = exporter._export_images(Path(output_dir))
                if images_exported > 0:
                    self.message_queue.put(('log', f"✅ 导出了 {images_exported} 个图片文件"))
                else:
                    self.message_queue.put(('log', "📷 未找到图片资源"))
            except Exception as e:
                self.message_queue.put(('log', f"⚠️ 图片导出失败: {e}"))
            
            # 导出每个章节
            for i, (title, content, chapter_id) in enumerate(chapters, 1):
                try:
                    # 更新进度
                    progress = (i / len(chapters)) * 100
                    self.message_queue.put(('progress', progress))
                    self.message_queue.put(('status', f"导出章节 {i}/{len(chapters)}: {title}"))
                    self.message_queue.put(('log', f"正在导出: {title}"))
                    
                    # 处理图片链接
                    processed_content = exporter._process_image_links(content, export_format)
                    
                    # 导出单个章节
                    exporter._export_single_chapter(title, processed_content, i, Path(output_dir), export_format)
                    
                except Exception as e:
                    self.message_queue.put(('log', f"导出章节 '{title}' 失败: {e}"))
                    
            # 导出完成
            self.message_queue.put(('export_complete', output_dir))
            
        except Exception as e:
            self.message_queue.put(('error', f"导出失败: {e}"))
            
    def stop_export(self):
        """停止导出"""
        self.status_var.set("正在停止...")
        self.log("用户取消导出")
        self.reset_ui_state()
        
    def reset_ui_state(self):
        """重置界面状态"""
        self.export_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.progress_var.set(0)
        self.status_var.set("就绪")
        
    def clear_all(self):
        """清除所有内容"""
        self.epub_file_path.set("")
        self.output_dir_path.set("")  # 清空输出目录
        self.export_format.set("markdown")
        
        # 清空章节列表
        for item in self.chapter_tree.get_children():
            self.chapter_tree.delete(item)
            
        self.chapter_count_label.config(text="")
        
        # 清空日志
        self.log_text.delete(1.0, tk.END)
        
        self.reset_ui_state()
        self.log("已清除所有内容")
        
    def show_about(self):
        """显示关于对话框"""
        about_text = """
EPUB 章节导出工具 v1.0

功能特性:
• 智能解析 EPUB 文件结构
• 按章节导出为 Markdown 或 TXT 格式
• 支持中文内容和文件名
• 现代化图形用户界面

技术栈:
• Python 3.x
• tkinter (GUI)
• ebooklib (EPUB 解析)
• pypandoc (格式转换)

开发者: AI Assistant
许可证: MIT License
        """
        messagebox.showinfo("关于", about_text.strip())
        
    def log(self, message):
        """添加日志消息"""
        timestamp = time.strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}\n"
        
        self.log_text.insert(tk.END, log_message)
        self.log_text.see(tk.END)
        self.root.update_idletasks()
        
    def process_queue(self):
        """处理消息队列"""
        try:
            while True:
                message_type, data = self.message_queue.get_nowait()
                
                if message_type == 'chapters_loaded':
                    self.update_chapter_list(data)
                elif message_type == 'log':
                    self.log(data)
                elif message_type == 'progress':
                    self.progress_var.set(data)
                elif message_type == 'status':
                    self.status_var.set(data)
                elif message_type == 'error':
                    self.log(f"错误: {data}")
                    messagebox.showerror("错误", data)
                    self.reset_ui_state()
                elif message_type == 'export_complete':
                    self.log("✅ 导出完成！")
                    self.status_var.set("导出完成")
                    self.reset_ui_state()
                    messagebox.showinfo("完成", f"导出完成！\n文件保存在: {data}")
                    
        except queue.Empty:
            pass
            
        # 每100ms检查一次队列
        self.root.after(100, self.process_queue)


def main():
    """主函数"""
    # 检查依赖
    try:
        import ebooklib
        import pypandoc
    except ImportError as e:
        messagebox.showerror("依赖错误", 
                           f"缺少必要的依赖包: {e}\n\n请运行: pip install -r requirements.txt")
        return
        
    # 创建主窗口
    root = tk.Tk()
    
    # 设置窗口图标（如果有的话）
    try:
        # 可以在这里设置自定义图标
        pass
    except:
        pass
        
    # 创建应用
    app = EpubExporterGUI(root)
    
    # 运行主循环
    root.mainloop()


if __name__ == "__main__":
    main()
