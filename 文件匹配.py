import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinterdnd2 import TkinterDnD, DND_ALL
import os
import shutil
import threading
import re

# ============================================================
# 左侧（基准文件）支持的图片格式
# ============================================================
LEFT_IMAGE_FORMATS = {
    # JPEG 系列
    'jpg': 'JPEG', 'jpeg': 'JPEG', 'jpe': 'JPEG',
    # PNG
    'png': 'PNG',
    # WebP
    'webp': 'WebP',
    # HEIC / HEIF (苹果/部分安卓)
    'heic': 'HEIC', 'heif': 'HEIF', 'hif': 'HEIF',
    # TIFF
    'tiff': 'TIFF', 'tif': 'TIFF',
    # BMP
    'bmp': 'BMP',
    # GIF
    'gif': 'GIF',
    # AVIF (下一代)
    'avif': 'AVIF',
    # JPEG 2000
    'jp2': 'JPEG2000', 'j2k': 'JPEG2000', 'jpx': 'JPEG2000',
    # 其他常见
    'ico': 'ICO', 'tga': 'TGA', 'pcx': 'PCX',
    'ppm': 'PPM', 'pgm': 'PGM', 'pbm': 'PBM',
    'srw': 'Samsung RAW',  # 部分工具识别为图片
}

# ============================================================
# 右侧（匹配文件）支持的 RAW 格式 + 图片格式
# ============================================================
RIGHT_RAW_FORMATS = {
    # Sony
    'arw': 'Sony', 'sr2': 'Sony', 'srf': 'Sony',
    # Canon
    'cr2': 'Canon', 'cr3': 'Canon', 'crw': 'Canon',
    # Nikon
    'nef': 'Nikon', 'nrw': 'Nikon',
    # Olympus
    'orf': 'Olympus',
    # Fujifilm
    'raf': 'Fujifilm',
    # Panasonic / Leica
    'rw2': 'Panasonic', 'raw': 'Panasonic',
    # Adobe 通用
    'dng': 'DNG',
    # Pentax
    'pef': 'Pentax', 'ptx': 'Pentax',
    # Samsung
    'srw': 'Samsung',
    # Sigma
    'x3f': 'Sigma',
    # Epson
    'erf': 'Epson',
    # Leaf
    'mos': 'Leaf',
    # Phase One
    'iiq': 'Phase One',
    # Hasselblad
    '3fr': 'Hasselblad', 'fff': 'Hasselblad',
    # Leica
    'rwl': 'Leica',
    # Kodak
    'kdc': 'Kodak', 'dcr': 'Kodak', 'k25': 'Kodak',
    # Mamiya
    'mef': 'Mamiya',
    # Minolta
    'mrw': 'Minolta',
    # Casio
    'bay': 'Casio',
    # Sinar
    'cs1': 'Sinar',
}

# 右侧也支持所有左侧图片格式（用于 JPG+RAW 同文件夹场景）
RIGHT_IMAGE_FORMATS = {**LEFT_IMAGE_FORMATS}
# 去掉 srw 重复定义（右侧 RAW 里已有）
RIGHT_IMAGE_FORMATS.pop('srw', None)

LEFT_FORMATS_TEXT = "左侧支持: " + ", ".join(
    f".{ext}" for ext in sorted(LEFT_IMAGE_FORMATS.keys())
)
RIGHT_FORMATS_TEXT = "右侧 RAW: " + ", ".join(
    f".{ext.upper()}({brand})" for ext, brand in sorted(RIGHT_RAW_FORMATS.items())
)


class AutoExportApp(TkinterDnD.Tk):
    def __init__(self):
        super().__init__()
        self.title("文件匹配 by 留白")
        self.geometry("1200x800")
        
        # 数据存储
        self.base_names = set()       # 左侧基准文件名集合
        self.match_files = {}         # 右侧文件 {基准名: {扩展名: 路径}}
        self.current_context_widget = None
        
        # 界面初始化
        self._create_ui()
        self._setup_dnd()
        self._create_context_menu()
        
    def _create_ui(self):
        """创建主界面"""
        main_frame = tk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 左侧面板
        left_frame = tk.LabelFrame(main_frame, text="基准文件（拖放选中的图片文件夹）")
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.left_list = tk.Listbox(left_frame, font=('微软雅黑', 10))
        self.left_list.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 右侧面板
        right_frame = tk.LabelFrame(main_frame, text="匹配文件（拖放含 RAW 的文件夹）")
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        self.right_list = tk.Listbox(right_frame, font=('微软雅黑', 10))
        self.right_list.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 底部控制栏
        control_bar = tk.Frame(self)
        control_bar.pack(fill=tk.X, pady=5)

        ttk.Button(control_bar, text="一键导出所有匹配文件",
                 command=self._start_export).pack(side=tk.LEFT, padx=5)

        self.progress = ttk.Progressbar(control_bar, mode='determinate')
        self.progress.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        # 格式提示栏
        format_tip = tk.Label(self, text=LEFT_FORMATS_TEXT + "  |  " + RIGHT_FORMATS_TEXT,
                              font=('微软雅黑', 8), fg='gray',
                              wraplength=1180, anchor='w', justify='left')
        format_tip.pack(fill=tk.X, padx=10, pady=(0, 5))
        
    def _setup_dnd(self):
        """配置拖放功能"""
        for listbox in [self.left_list, self.right_list]:
            listbox.drop_target_register(DND_ALL)
            listbox.dnd_bind('<<Drop>>', self._handle_drop)
            
    def _create_context_menu(self):
        """创建右键菜单"""
        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label="清空本列表", command=self._clear_current_list)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="删除选中项", command=self._delete_selected)
        
        self.left_list.bind("<Button-3>", self._show_context_menu)
        self.right_list.bind("<Button-3>", self._show_context_menu)
        
    def _show_context_menu(self, event):
        """显示右键菜单"""
        self.current_context_widget = event.widget
        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()
            
    def _clear_current_list(self):
        """清空当前列表"""
        if self.current_context_widget == self.left_list:
            self.base_names.clear()
            self.left_list.delete(0, tk.END)
        elif self.current_context_widget == self.right_list:
            self.match_files.clear()
            self.right_list.delete(0, tk.END)
            
    def _delete_selected(self):
        """删除选中项"""
        if self.current_context_widget == self.left_list:
            for i in reversed(self.left_list.curselection()):
                name = self.left_list.get(i).split('.')[0]
                self.base_names.discard(name)
                self.left_list.delete(i)
        elif self.current_context_widget == self.right_list:
            selected_names = {self.right_list.get(i).split('.')[0] for i in self.right_list.curselection()}
            for name in selected_names:
                if name in self.match_files:
                    del self.match_files[name]
            self._update_list('right')

    def _handle_drop(self, event):
        """处理拖放事件"""
        widget = event.widget
        side = 'left' if widget == self.left_list else 'right'
        
        paths = self._parse_drop_data(event.data)
        for path in paths:
            path = os.path.normpath(path)
            if os.path.isdir(path):
                self._process_folder(path, side)
            elif os.path.isfile(path):
                self._process_single_file(path, side)
                
    def _parse_drop_data(self, data):
        """解析拖放路径"""
        if data.startswith('{') and data.endswith('}'):
            return [data[1:-1]]
        return [x.strip('{}') for x in re.findall(r'{.*?}', data)] if '{' in data else data.split()
    
    def _process_folder(self, folder, side):
        """处理文件夹（新增重复检测）"""
        # 清空现有数据
        if side == 'left':
            self.base_names.clear()
        else:
            self.match_files.clear()
        
        total_files = 0
        duplicate_count = 0
        
        for root, _, files in os.walk(folder):
            for f in files:
                total_files += 1
                path = os.path.join(root, f)
                if not self._add_file(path, side):
                    duplicate_count += 1
        
        self._update_list(side)
        
        # 仅在检测到重复时提示
        if duplicate_count > 0:
            messagebox.showwarning("重复文件", 
                f"在 {folder} 中发现：\n"
                f"总文件数：{total_files}\n"
                f"重复文件：{duplicate_count}\n"
                f"实际加载：{total_files - duplicate_count}"
            )
        
    def _process_single_file(self, path, side):
        """处理单个文件（新增重复检测）"""
        if side == 'left':
            self.base_names.clear()
        else:
            self.match_files.clear()
            
        if not self._add_file(path, side):
            messagebox.showwarning("重复文件", f"文件已存在：{os.path.basename(path)}")
        self._update_list(side)
            
    def _add_file(self, path, side):
        """添加文件（返回是否成功添加）"""
        filename = os.path.basename(path)
        name, ext = os.path.splitext(filename)
        ext = ext[1:].lower() if ext else 'no_ext'

        if side == 'left':
            # 左侧：只接受主流图片格式（不含 RAW）
            if ext not in LEFT_IMAGE_FORMATS:
                return False
            if name in self.base_names:
                return False
            self.base_names.add(name)
            return True
        else:
            # 右侧：接受所有图片格式 + 所有 RAW 格式
            all_right_formats = {**RIGHT_IMAGE_FORMATS, **RIGHT_RAW_FORMATS}
            if ext not in all_right_formats:
                return False
            if name in self.match_files and ext in self.match_files[name]:
                return False
            if name not in self.match_files:
                self.match_files[name] = {}
            self.match_files[name][ext] = path
            return True
    
    def _update_list(self, side):
        """更新列表显示"""
        if side == 'left':
            self.left_list.delete(0, tk.END)
            for name in sorted(self.base_names):
                self.left_list.insert(tk.END, f"{name}.jpg")
        else:
            self.right_list.delete(0, tk.END)
            for name in sorted(self.match_files):
                for ext in self.match_files[name]:
                    self.right_list.insert(tk.END, f"{name}.{ext}")
    
    def _start_export(self):
        """启动导出流程"""
        if not self.base_names:
            messagebox.showwarning("警告", "请先在左侧添加基准文件")
            return
        
        export_files = []
        for name in self.base_names:
            if matches := self.match_files.get(name):
                export_files.extend(matches.values())
        
        if not export_files:
            messagebox.showinfo("提示", "没有找到匹配文件")
            return
        
        dest = filedialog.askdirectory(title="选择导出目录")
        if not dest:
            return
        
        threading.Thread(
            target=self._export_files,
            args=(export_files, dest),
            daemon=True
        ).start()
    
    def _export_files(self, files, dest):
        """执行导出操作"""
        self.progress['maximum'] = len(files)
        self.progress['value'] = 0
        
        success = 0
        for idx, src in enumerate(files, 1):
            try:
                dst = os.path.join(dest, os.path.basename(src))
                shutil.copy2(src, dst)
                success += 1
            except Exception as e:
                print(f"导出失败：{src} -> {str(e)}")
            finally:
                self.progress['value'] = idx
                self.update_idletasks()
        
        messagebox.showinfo("完成", 
            f"成功导出 {success}/{len(files)} 个文件\n"
            f"目标目录：{dest}"
        )

if __name__ == "__main__":
    app = AutoExportApp()
    app.mainloop()