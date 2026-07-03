import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinterdnd2 import TkinterDnD, DND_ALL
import os
import shutil
import threading
import re
import io
from PIL import Image
import imagehash
import rawpy

# ============================================================
# 常见相机 RAW 格式参考（仅用于 UI 展示，不影响匹配逻辑）
# ============================================================
COMMON_RAW_FORMATS = {
    'arw': 'Sony',
    'cr2': 'Canon', 'cr3': 'Canon',
    'nef': 'Nikon', 'nrw': 'Nikon',
    'orf': 'Olympus',
    'raf': 'Fujifilm',
    'rw2': 'Panasonic', 'raw': 'Panasonic',
    'dng': 'Adobe/通用',
    'pef': 'Pentax', 'ptx': 'Pentax',
    'srw': 'Samsung',
    'x3f': 'Sigma',
    'erf': 'Epson',
    'mos': 'Leaf',
    'iiq': 'Phase One',
    '3fr': 'Hasselblad', 'fff': 'Hasselblad',
    'rwl': 'Leica',
    'kdc': 'Kodak', 'dcr': 'Kodak', 'k25': 'Kodak',
    'mef': 'Mamiya',
    'mrw': 'Minolta',
    'bay': 'Casio',
    'cs1': 'Sinar',
    'sr2': 'Sony', 'srf': 'Sony',
}

RAW_FORMATS_TEXT = "常见 RAW 格式: " + ", ".join(
    f".{ext.upper()}({brand})" for ext, brand in sorted(COMMON_RAW_FORMATS.items())
)

# 感知哈希判定阈值（pHash 距离 <= 此值视为匹配）
PHASH_THRESHOLD = 10


def extract_preview_from_raw(raw_path):
    """
    从 RAW 文件中提取嵌入的预览图（通常是相机直出的 JPG）。
    返回 PIL.Image 或 None。
    """
    try:
        with rawpy.imread(raw_path) as raw:
            thumb = raw.extract_thumb()
            if thumb.format == rawpy.ThumbFormat.JPEG:
                return Image.open(io.BytesIO(thumb.data))
            elif thumb.format == rawpy.ThumbFormat.BITMAP:
                data = thumb.data
                if data.ndim == 3 and data.shape[2] in (3, 4):
                    mode = 'RGB' if data.shape[2] == 3 else 'RGBA'
                    return Image.fromarray(data, mode)
    except Exception:
        pass
    return None


def compute_phash(img, hash_size=16):
    """计算感知哈希（pHash），对轻微压缩/缩放有容错。"""
    try:
        return imagehash.phash(img, hash_size=hash_size)
    except Exception:
        return None


def verify_file_against_left(left_img, right_path):
    """
    校验单个右侧文件（图片或 RAW）是否与左侧图片对应同一张照片。

    返回: {
        'status': 'match' | 'mismatch' | 'uncertain',
        'method': 说明,
        'detail': 人类可读说明
    }
    """
    left_phash = compute_phash(left_img)
    if left_phash is None:
        return {
            'status': 'uncertain',
            'method': 'phash_failed',
            'detail': '左侧图片哈希计算失败'
        }

    right_ext = os.path.splitext(right_path)[1][1:].lower()

    # 策略 A：右侧是普通图片 → 直接打开比对
    if right_ext not in COMMON_RAW_FORMATS:
        try:
            right_img = Image.open(right_path)
            right_phash = compute_phash(right_img)
            if right_phash is None:
                return {
                    'status': 'uncertain',
                    'method': 'phash_failed',
                    'detail': f'{os.path.basename(right_path)} 哈希计算失败'
                }
            hamming = left_phash - right_phash
            if hamming <= PHASH_THRESHOLD:
                return {
                    'status': 'match',
                    'method': 'phash',
                    'detail': f'{os.path.basename(right_path)} 感知哈希距离={hamming} (≤{PHASH_THRESHOLD})'
                }
            else:
                return {
                    'status': 'mismatch',
                    'method': 'phash',
                    'detail': f'{os.path.basename(right_path)} 感知哈希距离={hamming} (>{PHASH_THRESHOLD})，不是同一张图'
                }
        except Exception as e:
            return {
                'status': 'uncertain',
                'method': 'open_failed',
                'detail': f'{os.path.basename(right_path)} 无法打开: {e}'
            }

    # 策略 B：右侧是 RAW → 提取嵌入预览做比对
    preview = extract_preview_from_raw(right_path)
    if preview is not None:
        preview_phash = compute_phash(preview)
        if preview_phash is not None:
            hamming = left_phash - preview_phash
            if hamming <= PHASH_THRESHOLD:
                return {
                    'status': 'match',
                    'method': 'phash_raw_preview',
                    'detail': f'{os.path.basename(right_path)} RAW嵌入预览哈希距离={hamming} (≤{PHASH_THRESHOLD})'
                }
            else:
                return {
                    'status': 'mismatch',
                    'method': 'phash_raw_preview',
                    'detail': f'{os.path.basename(right_path)} RAW嵌入预览哈希距离={hamming} (>{PHASH_THRESHOLD})，不是同一张图的RAW'
                }

    # RAW 没有可供提取的嵌入预览 → 无法校验
    return {
        'status': 'uncertain',
        'method': 'no_preview',
        'detail': f'{os.path.basename(right_path)} RAW无嵌入预览，靠文件名匹配'
    }


class AutoExportApp(TkinterDnD.Tk):
    def __init__(self):
        super().__init__()
        self.title("文件匹配 by 留白")
        self.geometry("1200x900")

        self.base_files = {}
        self.match_files = {}
        self.current_context_widget = None

        self._create_ui()
        self._setup_dnd()
        self._create_context_menu()

    def _create_ui(self):
        """创建主界面"""
        main_frame = tk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        left_frame = tk.LabelFrame(main_frame, text="基准文件（拖放选中的图片，任意格式）")
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.left_list = tk.Listbox(left_frame, font=('微软雅黑', 10))
        self.left_list.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        right_frame = tk.LabelFrame(main_frame, text="匹配文件（拖放含 RAW 的文件夹）")
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        self.right_list = tk.Listbox(right_frame, font=('微软雅黑', 10))
        self.right_list.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        control_bar = tk.Frame(self)
        control_bar.pack(fill=tk.X, pady=5)

        ttk.Button(control_bar, text="一键导出所有匹配文件",
                   command=self._start_export).pack(side=tk.LEFT, padx=5)

        self.progress = ttk.Progressbar(control_bar, mode='determinate')
        self.progress.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        format_tip = tk.Label(self, text=RAW_FORMATS_TEXT,
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
            self.base_files.clear()
            self.left_list.delete(0, tk.END)
        elif self.current_context_widget == self.right_list:
            self.match_files.clear()
            self.right_list.delete(0, tk.END)

    def _delete_selected(self):
        """删除选中项"""
        if self.current_context_widget == self.left_list:
            for i in reversed(self.left_list.curselection()):
                name = self.left_list.get(i)
                stem = os.path.splitext(name)[0]
                self.base_files.pop(stem, None)
                self.left_list.delete(i)
        elif self.current_context_widget == self.right_list:
            for i in reversed(self.right_list.curselection()):
                name = self.right_list.get(i)
                stem = os.path.splitext(name)[0]
                if stem in self.match_files:
                    del self.match_files[stem]
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
        """处理文件夹"""
        if side == 'left':
            self.base_files.clear()
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

        if duplicate_count > 0:
            messagebox.showwarning("重复文件",
                                   f"在 {folder} 中发现：\n"
                                   f"总文件数：{total_files}\n"
                                   f"重复文件：{duplicate_count}\n"
                                   f"实际加载：{total_files - duplicate_count}"
                                   )

    def _process_single_file(self, path, side):
        """处理单个文件"""
        if side == 'left':
            self.base_files.clear()
        else:
            self.match_files.clear()

        if not self._add_file(path, side):
            messagebox.showwarning("重复文件", f"文件已存在：{os.path.basename(path)}")
        self._update_list(side)

    def _add_file(self, path, side):
        """添加文件（返回是否成功添加）"""
        filename = os.path.basename(path)
        stem, ext = os.path.splitext(filename)
        ext = ext[1:].lower() if ext else 'no_ext'

        if side == 'left':
            if stem in self.base_files:
                return False
            self.base_files[stem] = path
            return True
        else:
            if stem in self.match_files and ext in self.match_files[stem]:
                return False
            if stem not in self.match_files:
                self.match_files[stem] = {}
            self.match_files[stem][ext] = path
            return True

    def _update_list(self, side):
        """更新列表显示"""
        if side == 'left':
            self.left_list.delete(0, tk.END)
            for stem in sorted(self.base_files):
                fname = os.path.basename(self.base_files[stem])
                self.left_list.insert(tk.END, fname)
        else:
            self.right_list.delete(0, tk.END)
            for stem in sorted(self.match_files):
                for ext in sorted(self.match_files[stem]):
                    self.right_list.insert(tk.END, f"{stem}.{ext}")

    def _start_export(self):
        """启动导出流程"""
        if not self.base_files:
            messagebox.showwarning("警告", "请先在左侧添加基准文件")
            return

        matched_stems = [s for s in self.base_files if s in self.match_files]

        if not matched_stems:
            messagebox.showinfo("提示", "没有找到匹配文件（按文件名 stem 匹配）")
            return

        verify_results = []
        for stem in matched_stems:
            left_path = self.base_files[stem]
            try:
                left_img = Image.open(left_path)
            except Exception:
                continue

            right_dict = self.match_files[stem]
            for ext, r_path in right_dict.items():
                result = verify_file_against_left(left_img, r_path)
                result['stem'] = stem
                result['path'] = r_path
                result['filename'] = os.path.basename(r_path)
                verify_results.append(result)

        if not verify_results:
            messagebox.showinfo("提示", "没有可导出的文件")
            return

        match_list = [r for r in verify_results if r['status'] == 'match']
        mismatch_list = [r for r in verify_results if r['status'] == 'mismatch']
        uncertain_list = [r for r in verify_results if r['status'] == 'uncertain']

        lines = []
        lines.append(f"共 {len(matched_stems)} 个 stem，{len(verify_results)} 个右侧文件")
        lines.append(f"即将导出: {len(match_list)} 个通过校验的")
        lines.append("─" * 40)
        lines.append(f"[MATCH] 校验通过: {len(match_list)}")
        lines.append(f"[SKIP] 校验不匹配: {len(mismatch_list)} (将跳过)")
        lines.append(f"[SKIP] 无法校验: {len(uncertain_list)} (将跳过)")
        lines.append("")

        if mismatch_list:
            lines.append("[不匹配详情 - 这些文件将被跳过]")
            for r in mismatch_list:
                lines.append(f"  ! {r['filename']}: {r['detail']}")
            lines.append("")

        if uncertain_list:
            lines.append("[无法校验详情 - 这些文件将被跳过]")
            for r in uncertain_list:
                lines.append(f"  ? {r['filename']}: {r['detail']}")
            lines.append("")

        if match_list:
            lines.append("[匹配详情 - 前 5 个]")
            for r in match_list[:5]:
                lines.append(f"  OK {r['filename']}: {r['detail']}")
            if len(match_list) > 5:
                lines.append(f"  ... 还有 {len(match_list) - 5} 个")

        report = "\n".join(lines)

        if not match_list:
            messagebox.showwarning("警告",
                                   "所有文件校验均不匹配或无法校验！\n"
                                   "可能是 RAW 文件被替换/改名。\n请检查右侧文件夹内容。")
            return

        if not messagebox.askyesno("校验报告", report + "\n\n是否继续导出校验通过的文件？"):
            return

        dest = filedialog.askdirectory(title="选择导出目录")
        if not dest:
            return

        export_files = [r['path'] for r in match_list]

        if not export_files:
            messagebox.showinfo("提示", "没有可导出的文件")
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
