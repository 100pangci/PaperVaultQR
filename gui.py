import sys
import os
import threading
import subprocess
import queue
import tkinter as tk
from tkinter import filedialog, ttk

try:
    from ctypes import windll, wintypes, create_unicode_buffer
    have_ctypes = True
except Exception:
    have_ctypes = False


LOG_POLL_MS = 100


def run_subprocess_and_stream(cmd, log_q):
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    except Exception as e:
        log_q.put(f"ERROR: 启动命令失败: {e}\n")
        log_q.put("__DONE__")
        return

    for line in proc.stdout:
        log_q.put(line)
    proc.wait()
    if proc.returncode != 0:
        log_q.put(f"PROCESS EXITED WITH CODE {proc.returncode}\n")
    log_q.put("__DONE__")


def start_encode(path, lang, log_q):
    cmd = [sys.executable, os.path.join(os.path.dirname(__file__), 'auto_split_qr.py'), path]
    if lang and lang != 'auto':
        cmd += ['--lang', lang]
    run_subprocess_and_stream(cmd, log_q)


def start_decode(path, lang, log_q):
    # invoke scanner_decoder.decode_folder(path, lang=lang) via -c to capture output
    py_cmd = f"import scanner_decoder; scanner_decoder.decode_folder(r'{path}', lang='{lang}')"
    cmd = [sys.executable, "-c", py_cmd]
    run_subprocess_and_stream(cmd, log_q)


def register_native_drop(root, callback):
    if not have_ctypes or os.name != "nt":
        return False

    user32 = windll.user32
    shell32 = windll.shell32

    WM_DROPFILES = 0x0233
    GWL_WNDPROC = -4

    WNDPROC = windll.WINFUNCTYPE(wintypes.LRESULT, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)

    hwnd = root.winfo_id()
    user32.DragAcceptFiles(hwnd, True)

    orig_wndproc = user32.GetWindowLongPtrW(hwnd, GWL_WNDPROC)

    @WNDPROC
    def _wndproc(hWnd, msg, wParam, lParam):
        if msg == WM_DROPFILES:
            hDrop = wParam
            count = shell32.DragQueryFileW(hDrop, 0xFFFFFFFF, None, 0)
            for i in range(count):
                buf = create_unicode_buffer(260)
                shell32.DragQueryFileW(hDrop, i, buf, 260)
                path = buf.value
                root.after(10, callback, path)
            shell32.DragFinish(hDrop)
            return 0
        return user32.CallWindowProcW(orig_wndproc, hWnd, msg, wParam, lParam)

    user32.SetWindowLongPtrW(hwnd, GWL_WNDPROC, _wndproc)
    root._orig_wndproc = orig_wndproc
    root._new_wndproc = _wndproc
    return True


class GUI:
    def __init__(self, root):
        self.root = root
        root.title("PaperVaultQR — 拖拽文件/文件夹")
        root.geometry("640x420")

        lbl = tk.Label(root, text="将文件或文件夹拖拽到此窗口，或使用下面的按钮选择。", wraplength=620, justify="center")
        lbl.pack(pady=8)

        top_frame = tk.Frame(root)
        top_frame.pack(fill='x', padx=12)

        lang_label = tk.Label(top_frame, text="语言：")
        lang_label.pack(side='left')

        self.lang_var = tk.StringVar(value='auto')
        self.lang_combo = ttk.Combobox(top_frame, textvariable=self.lang_var, values=['auto', 'zh', 'en'], width=8, state='readonly')
        self.lang_combo.pack(side='left')

        btn_frame = tk.Frame(top_frame)
        btn_frame.pack(side='right')

        b1 = tk.Button(btn_frame, text="选择文件（编码）", command=self.choose_file)
        b1.grid(row=0, column=0, padx=6)
        b2 = tk.Button(btn_frame, text="选择文件夹（解码）", command=self.choose_folder)
        b2.grid(row=0, column=1, padx=6)

        self.status = tk.Label(root, text="等待操作...", fg="blue")
        self.status.pack(pady=6)

        self.progress = ttk.Progressbar(root, mode='indeterminate')
        self.progress.pack(fill='x', padx=12, pady=6)

        log_label = tk.Label(root, text="日志：")
        log_label.pack(anchor='w', padx=12)

        self.log = tk.Text(root, height=12, wrap='none')
        self.log.pack(fill='both', expand=True, padx=12, pady=(0,12))
        self.log.configure(state='disabled')

        self.log_q = queue.Queue()
        self._running = False

        info = tk.Label(root, text="注意：Windows 平台支持原生拖拽；其它平台可使用按钮选择。", fg="gray")
        info.pack(side="bottom", pady=6)

        registered = register_native_drop(root, lambda p: self.handle_path(p))
        if not registered:
            info.config(text="当前平台不支持原生拖拽，使用按钮选择文件或文件夹。")

        self.root.after(LOG_POLL_MS, self._poll_log)

    def _append_log(self, text):
        self.log.configure(state='normal')
        self.log.insert('end', text)
        self.log.see('end')
        self.log.configure(state='disabled')

    def _poll_log(self):
        try:
            while True:
                line = self.log_q.get_nowait()
                if line == '__DONE__':
                    self.progress.stop()
                    self._running = False
                    self.status.config(text='完成')
                else:
                    self._append_log(line)
        except queue.Empty:
            pass
        self.root.after(LOG_POLL_MS, self._poll_log)

    def choose_file(self):
        p = filedialog.askopenfilename(title="选择要编码的文件")
        if p:
            self.handle_path(p)

    def choose_folder(self):
        p = filedialog.askdirectory(title="选择包含扫描图片的文件夹（解码）")
        if p:
            self.handle_path(p)

    def handle_path(self, path):
        if self._running:
            self._append_log('另一个任务正在运行，请稍候...\n')
            return
        self._running = True
        self.log_q.queue.clear()
        self.log.configure(state='normal')
        self.log.delete('1.0', 'end')
        self.log.configure(state='disabled')

        lang = self.lang_var.get() or 'auto'
        self.status.config(text=f'处理中: {path}')
        self.progress.start()

        if os.path.isdir(path):
            t = threading.Thread(target=lambda: start_decode(path, lang, self.log_q), daemon=True)
            t.start()
        else:
            t = threading.Thread(target=lambda: start_encode(path, lang, self.log_q), daemon=True)
            t.start()


def main():
    root = tk.Tk()
    app = GUI(root)
    root.mainloop()


if __name__ == '__main__':
    main()
