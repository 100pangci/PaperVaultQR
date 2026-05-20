import locale
import os
import queue
import sys
import io
import threading
from tkinter import filedialog
import customtkinter as ctk

import auto_split_qr
import scanner_decoder

APP_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_POLL_MS = 100

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

UI_TEXT = {
    "zh": {
        "title": "PaperVaultQR — 赛博冷存储",
        "subtitle": "使用右侧按钮选择文件进行物理备份或恢复操作。",
        "language": "界面语言",
        "choose_file": "编码文件 (转二维码)",
        "choose_folder": "解码恢复 (从图片)",
        "clear_log": "清空控制台",
        "status_ready": "🟢 系统就绪",
        "status_processing_file": "⚡ 正在生成打印切片...",
        "status_processing_folder": "⚡ 正在解析底层数据...",
        "status_done": "✅ 任务完成",
        "status_failed": "❌ 任务失败",
        "selected_none": "尚未选择目标路径",
        "log": "终端运行日志",
        "info_tip": "💡 请使用上方按钮选择要处理的文件或文件夹",
        "busy": "另一个任务正在运行，请稍候...\n",
        "file_dialog": "选择要进行物理备份的源文件",
        "folder_dialog": "选择包含扫描图片的文件夹",
        "invalid_path": "路径不存在：{path}",
    },
    "en": {
        "title": "PaperVaultQR — Cold Storage",
        "subtitle": "Use the buttons on the right for backup or recovery.",
        "language": "Language",
        "choose_file": "Encode File (to QR)",
        "choose_folder": "Decode Folder (from Image)",
        "clear_log": "Clear Console",
        "status_ready": "🟢 System Ready",
        "status_processing_file": "⚡ Generating print slices...",
        "status_processing_folder": "⚡ Parsing underlying data...",
        "status_done": "✅ Task Completed",
        "status_failed": "❌ Task Failed",
        "selected_none": "No target path selected",
        "log": "Terminal Execution Log",
        "info_tip": "💡 Please use the buttons above to select a file or folder",
        "busy": "Another task is running, please wait...\n",
        "file_dialog": "Select source file for physical backup",
        "folder_dialog": "Select folder containing scanned images",
        "invalid_path": "Path does not exist: {path}",
    },
}

def detect_lang(explicit_lang=None):
    if explicit_lang in {"zh", "en"}: return explicit_lang
    if os.name == "nt":
        try:
            import ctypes
            lang_id = ctypes.windll.kernel32.GetUserDefaultUILanguage()
            if (lang_id & 0x3FF) == 0x04: return "zh"
        except: pass
    try:
        if "zh" in (locale.getdefaultlocale()[0] or "").lower(): return "zh"
    except: pass
    return "en"

def tr(lang, key, **kwargs):
    return UI_TEXT[lang][key].format(**kwargs)

class QueueRedirector(io.StringIO):
    def __init__(self, log_q):
        super().__init__()
        self.log_q = log_q
    def write(self, text):
        self.log_q.put(text)
    def flush(self): pass

def run_task_in_thread(path, lang, log_q):
    old_stdout, old_stderr = sys.stdout, sys.stderr
    redirector = QueueRedirector(log_q)
    sys.stdout, sys.stderr = redirector, redirector
    try:
        if os.path.isdir(path): scanner_decoder.decode_folder(path, lang=lang)
        else: auto_split_qr.process_file(path, lang=lang)
    except Exception as e:
        print(f"ERROR: 发生未捕获的错误: {e}")
    finally:
        sys.stdout, sys.stderr = old_stdout, old_stderr
        log_q.put("__DONE__")

class ModernGUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.geometry("900x650")
        self.minsize(800, 600)
        
        self.lang_var = ctk.StringVar(value="auto")
        self.lang_var.trace_add("write", self.update_ui_texts)
        
        self.log_q = queue.Queue()
        self._running, self._task_failed = False, False
        self._status_key = "status_ready"
        self._selected_path = ""

        # --- 顶部区域 ---
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.pack(fill="x", padx=20, pady=(20, 10))
        
        self.title_label = ctk.CTkLabel(self.header_frame, text="", font=ctk.CTkFont(family="Microsoft YaHei UI", size=24, weight="bold"))
        self.title_label.pack(anchor="w")
        
        self.subtitle_label = ctk.CTkLabel(self.header_frame, text="", text_color="gray60", font=ctk.CTkFont(size=14))
        self.subtitle_label.pack(anchor="w", pady=(2, 0))

        # --- 工具栏区域 ---
        self.toolbar_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.toolbar_frame.pack(fill="x", padx=20, pady=(10, 15))
        
        self.lang_label = ctk.CTkLabel(self.toolbar_frame, text="", font=ctk.CTkFont(weight="bold"))
        self.lang_label.pack(side="left", padx=(0, 10))
        
        self.lang_combo = ctk.CTkOptionMenu(self.toolbar_frame, variable=self.lang_var, values=["auto", "zh", "en"], width=100)
        self.lang_combo.pack(side="left")

        self.clear_btn = ctk.CTkButton(self.toolbar_frame, text="", width=100, fg_color="transparent", border_width=1, text_color=("gray10", "#DCE4EE"), command=self.clear_log)
        self.clear_btn.pack(side="right", padx=(10, 0))
        
        self.folder_btn = ctk.CTkButton(self.toolbar_frame, text="", width=140, fg_color="#107C41", hover_color="#0B5D30", command=self.choose_folder)
        self.folder_btn.pack(side="right", padx=(10, 0))

        self.file_btn = ctk.CTkButton(self.toolbar_frame, text="", width=140, command=self.choose_file)
        self.file_btn.pack(side="right", padx=(10, 0))

        # --- 状态与进度卡片 ---
        self.status_card = ctk.CTkFrame(self, corner_radius=10)
        self.status_card.pack(fill="x", padx=20, pady=5)
        
        self.status_label = ctk.CTkLabel(self.status_card, text="", font=ctk.CTkFont(size=16, weight="bold"))
        self.status_label.pack(anchor="w", padx=20, pady=(15, 2))
        
        self.path_label = ctk.CTkLabel(self.status_card, text="", text_color="gray50", font=ctk.CTkFont(size=12))
        self.path_label.pack(anchor="w", padx=20, pady=(0, 10))
        
        self.progress = ctk.CTkProgressBar(self.status_card, height=4)
        self.progress.pack(fill="x", padx=20, pady=(0, 15))
        self.progress.set(0)

        # --- 日志区域 ---
        self.log_label = ctk.CTkLabel(self, text="", font=ctk.CTkFont(weight="bold"))
        self.log_label.pack(anchor="w", padx=20, pady=(15, 5))
        
        self.log_text = ctk.CTkTextbox(self, corner_radius=10, font=ctk.CTkFont(family="Consolas", size=13))
        self.log_text.pack(fill="both", expand=True, padx=20, pady=(0, 10))
        self.log_text.configure(state="disabled")

        # --- 底部信息 ---
        self.info_label = ctk.CTkLabel(self, text="", text_color="gray50", font=ctk.CTkFont(size=12))
        self.info_label.pack(side="left", padx=20, pady=(0, 10))

        self.update_ui_texts()
        self.after(LOG_POLL_MS, self._poll_log)

    def _ui_lang(self): return detect_lang(None if self.lang_var.get() == "auto" else self.lang_var.get())
    def _texts(self): return UI_TEXT[self._ui_lang()]

    def update_ui_texts(self, *args):
        t = self._texts()
        self.title(t["title"])
        self.title_label.configure(text=t["title"])
        self.subtitle_label.configure(text=t["subtitle"])
        self.lang_label.configure(text=t["language"])
        self.file_btn.configure(text=t["choose_file"])
        self.folder_btn.configure(text=t["choose_folder"])
        self.clear_btn.configure(text=t["clear_log"])
        self.log_label.configure(text=t["log"])
        self.info_label.configure(text=t["info_tip"])
        
        self.status_label.configure(text=t[self._status_key])
        self.path_label.configure(text=self._selected_path if self._selected_path else t["selected_none"])

    def _set_controls_enabled(self, enabled):
        state = "normal" if enabled else "disabled"
        self.lang_combo.configure(state=state)
        self.file_btn.configure(state=state)
        self.folder_btn.configure(state=state)
        self.clear_btn.configure(state=state)

    def clear_log(self):
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

    def _append_log(self, text):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", text)
        self.log_text.see("end")
        self.log_text.configure(state="disabled")
    
    def _set_status(self, key, is_error=False):
        self._status_key = key
        color = "#fa505a" if is_error else ("gray10", "#DCE4EE") 
        self.status_label.configure(text=self._texts()[key], text_color=color)

    def _poll_log(self):
        try:
            while True:
                line = self.log_q.get_nowait()
                if line == "__DONE__":
                    self.progress.stop()
                    self.progress.set(1.0)
                    self._running = False
                    self._set_controls_enabled(True)
                    self._set_status("status_failed" if self._task_failed else "status_done", self._task_failed)
                elif line.startswith("ERROR:") or line.startswith("❌"):
                    self._task_failed = True
                    self._append_log(line)
                else:
                    self._append_log(line)
        except queue.Empty:
            pass
        self.after(LOG_POLL_MS, self._poll_log)

    def choose_file(self):
        p = filedialog.askopenfilename(title=self._texts()["file_dialog"])
        if p: self.handle_path(p)

    def choose_folder(self):
        p = filedialog.askdirectory(title=self._texts()["folder_dialog"])
        if p: self.handle_path(p)

    def handle_path(self, path):
        path = os.path.abspath(os.fspath(path))
        t = self._texts()

        if not os.path.exists(path):
            self._task_failed = True
            self._set_status("status_failed", True)
            self.path_label.configure(text=tr(self._ui_lang(), "invalid_path", path=path))
            self._append_log(tr(self._ui_lang(), "invalid_path", path=path) + "\n")
            return

        if self._running:
            self._append_log(t["busy"])
            return

        self._selected_path = path
        self._task_failed = False
        self._set_status("status_processing_folder" if os.path.isdir(path) else "status_processing_file")
        self.path_label.configure(text=path)

        while not self.log_q.empty(): self.log_q.get_nowait()
        self.clear_log()
        self._set_controls_enabled(False)
        
        self.progress.configure(mode="determinate")
        self.progress.start()

        worker = threading.Thread(target=run_task_in_thread, args=(path, self._ui_lang(), self.log_q), daemon=True)
        self._running = True
        worker.start()

if __name__ == "__main__":
    app = ModernGUI()
    app.mainloop()