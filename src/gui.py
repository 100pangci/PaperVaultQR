import glob
import io
import locale
import os
import queue
import re
import sys
import threading
import webbrowser
from tkinter import filedialog

import customtkinter as ctk

from core import auto_split_qr, scanner_decoder
from i18n import normalize_lang
from i18n.ui_texts import (
    AUTO_LANGUAGE_VALUE,
    PROJECT_URL,
    build_language_options,
    get_gui_text,
    get_gui_texts,
)

APP_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_POLL_MS = 100
UI_FONT_FAMILY = "Microsoft YaHei UI"
DEFAULT_GUI_TEXTS = get_gui_texts("en_us")

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")


def ui_font(size=12, weight="normal"):
    return ctk.CTkFont(family=UI_FONT_FAMILY, size=size, weight=weight)


def detect_lang(explicit_lang=None):
    if explicit_lang and str(explicit_lang).strip().lower() != AUTO_LANGUAGE_VALUE:
        return normalize_lang(explicit_lang)

    if os.name == "nt":
        try:
            import ctypes

            lang_id = ctypes.windll.kernel32.GetUserDefaultUILanguage()
            locale_id = lang_id & 0x3FF
            if locale_id == 0x04:
                return "zh_cn"
            if locale_id == 0x11:
                return "ja_jp"
        except Exception:
            pass

    try:
        loc = (locale.getdefaultlocale()[0] or "").lower()
        if "zh" in loc:
            return "zh_cn"
        if "ja" in loc or "jp" in loc:
            return "ja_jp"
    except Exception:
        pass

    return "en_us"


class QueueRedirector(io.StringIO):
    def __init__(self, log_q):
        super().__init__()
        self.log_q = log_q

    def write(self, text):
        self.log_q.put(text)

    def flush(self):
        pass


def run_task_in_thread(path, lang, log_q):
    old_stdout, old_stderr = sys.stdout, sys.stderr
    redirector = QueueRedirector(log_q)
    sys.stdout, sys.stderr = redirector, redirector

    try:
        if os.path.isdir(path):
            scanner_decoder.decode_folder(path, lang=lang)
        else:
            auto_split_qr.process_file(path, lang=lang)
    except Exception as e:
        print(get_gui_text(lang, "unhandled_error", error=e))
    finally:
        sys.stdout, sys.stderr = old_stdout, old_stderr
        log_q.put("__DONE__")


class ModernGUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.geometry("900x650")
        self.minsize(800, 600)
        self.option_add("*Font", (UI_FONT_FAMILY, 12))

        self._language_options = build_language_options()
        self._language_label_to_code = {}
        for code, label in self._language_options:
            self._language_label_to_code[label] = code
            self._language_label_to_code[code] = code

        self.lang_var = ctk.StringVar(value=AUTO_LANGUAGE_VALUE)
        self.lang_var.trace_add("write", self.update_ui_texts)

        self.log_q = queue.Queue()
        self._running = False
        self._task_failed = False
        self._status_key = "status_ready"
        self._selected_path = ""
        self._progress_mode = None  # "encode" | "decode"
        self._progress_total = 0
        self._progress_current = 0

        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.pack(fill="x", padx=20, pady=(20, 10))

        self.title_label = ctk.CTkLabel(self.header_frame, text="", font=ui_font(24, "bold"))
        self.title_label.pack(anchor="w")

        self.subtitle_label = ctk.CTkLabel(
            self.header_frame,
            text="",
            text_color="gray60",
            font=ui_font(14),
        )
        self.subtitle_label.pack(anchor="w", pady=(2, 0))

        self.toolbar_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.toolbar_frame.pack(fill="x", padx=20, pady=(10, 15))

        self.lang_label = ctk.CTkLabel(self.toolbar_frame, text="", font=ui_font(12, "bold"))
        self.lang_label.pack(side="left", padx=(0, 10))

        self.lang_combo = ctk.CTkOptionMenu(
            self.toolbar_frame,
            variable=self.lang_var,
            values=[label for _, label in self._language_options],
            width=160,
        )
        self.lang_combo.pack(side="left")

        self.clear_btn = ctk.CTkButton(
            self.toolbar_frame,
            text="",
            width=100,
            fg_color="transparent",
            border_width=1,
            text_color=("gray10", "#DCE4EE"),
            font=ui_font(12),
            command=self.clear_log,
        )
        self.clear_btn.pack(side="right", padx=(10, 0))

        self.folder_btn = ctk.CTkButton(
            self.toolbar_frame,
            text="",
            width=140,
            fg_color="#107C41",
            hover_color="#0B5D30",
            font=ui_font(12, "bold"),
            command=self.choose_folder,
        )
        self.folder_btn.pack(side="right", padx=(10, 0))

        self.file_btn = ctk.CTkButton(
            self.toolbar_frame,
            text="",
            width=140,
            font=ui_font(12, "bold"),
            command=self.choose_file,
        )
        self.file_btn.pack(side="right", padx=(10, 0))

        self.status_card = ctk.CTkFrame(self, corner_radius=10)
        self.status_card.pack(fill="x", padx=20, pady=5)

        self.status_label = ctk.CTkLabel(self.status_card, text="", font=ui_font(16, "bold"))
        self.status_label.pack(anchor="w", padx=20, pady=(15, 2))

        self.path_label = ctk.CTkLabel(
            self.status_card,
            text="",
            text_color="gray50",
            font=ui_font(12),
        )
        self.path_label.pack(anchor="w", padx=20, pady=(0, 10))

        self.progress = ctk.CTkProgressBar(self.status_card, height=4)
        self.progress.pack(fill="x", padx=20, pady=(0, 15))
        self.progress.set(0)

        self.log_label = ctk.CTkLabel(self, text="", font=ui_font(12, "bold"))
        self.log_label.pack(anchor="w", padx=20, pady=(15, 5))

        self.log_text = ctk.CTkTextbox(self, corner_radius=10, font=ui_font(13))
        self.log_text.pack(fill="both", expand=True, padx=20, pady=(0, 10))
        self.log_text.configure(state="disabled")

        self.footer_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.footer_frame.pack(fill="x", padx=20, pady=(0, 10))

        self.info_label = ctk.CTkLabel(
            self.footer_frame,
            text="",
            text_color="gray50",
            font=ui_font(12),
        )
        self.info_label.pack(side="left")

        self.project_link_label = ctk.CTkLabel(
            self.footer_frame,
            text=PROJECT_URL,
            text_color="#1f6aa5",
            cursor="hand2",
            font=ui_font(12, "bold"),
        )
        self.project_link_label.pack(side="right")
        self.project_link_label.bind("<Button-1>", lambda e: self.open_project_link())

        self.update_ui_texts()
        self.after(LOG_POLL_MS, self._poll_log)

    def _selected_lang_code(self):
        selection = self.lang_var.get()
        if selection == AUTO_LANGUAGE_VALUE:
            return detect_lang(None)
        return self._language_label_to_code.get(selection, normalize_lang(selection))

    def _ui_lang(self):
        return self._selected_lang_code()

    def _texts(self):
        return get_gui_texts(self._ui_lang())

    def _text(self, key, default=""):
        texts = self._texts()
        if key in texts:
            return texts[key]
        if key in DEFAULT_GUI_TEXTS:
            return DEFAULT_GUI_TEXTS[key]
        return default if default else key

    def update_ui_texts(self, *args):
        self.title(self._text("title", "PaperVaultQR"))
        self.title_label.configure(text=self._text("title", "PaperVaultQR"))
        self.subtitle_label.configure(text=self._text("subtitle"))
        self.lang_label.configure(text=self._text("language"))
        self.file_btn.configure(text=self._text("choose_file"))
        self.folder_btn.configure(text=self._text("choose_folder"))
        self.clear_btn.configure(text=self._text("clear_log"))
        self.log_label.configure(text=self._text("log"))
        self.info_label.configure(text=self._text("info_tip"))
        self.project_link_label.configure(text=PROJECT_URL)
        self.status_label.configure(text=self._text(self._status_key))
        self.path_label.configure(
            text=self._selected_path if self._selected_path else self._text("selected_none")
        )

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

    def open_project_link(self):
        webbrowser.open_new_tab(PROJECT_URL)

    def _append_log(self, text):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", text)
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _set_status(self, key, is_error=False):
        self._status_key = key
        color = "#fa505a" if is_error else ("gray10", "#DCE4EE")
        self.status_label.configure(text=self._text(key), text_color=color)

    def _update_progress(self, current, total):
        if total <= 0:
            return
        percent = max(0.0, min(1.0, current / total))
        self.progress.set(percent)

    def _try_update_progress_from_log(self, line):
        encode_match = re.search(r"(?:处理进度|Progress)\s*:\s*(\d+)\s*/\s*(\d+)", line)
        if encode_match:
            current = int(encode_match.group(1))
            total = int(encode_match.group(2))
            self._progress_mode = "encode"
            self._progress_current = current
            self._progress_total = total
            self._update_progress(current, total)
            return

        if self._progress_mode == "decode" and re.search(
            r"(?:扫描图片|Scanning image)\s*:",
            line,
        ):
            if self._progress_total > 0:
                self._progress_current = min(
                    self._progress_current + 1,
                    self._progress_total,
                )
                self._update_progress(self._progress_current, self._progress_total)

    def _poll_log(self):
        try:
            while True:
                line = self.log_q.get_nowait()
                if line == "__DONE__":
                    self.progress.set(1.0)
                    self._running = False
                    self._set_controls_enabled(True)
                    self._set_status(
                        "status_failed" if self._task_failed else "status_done",
                        self._task_failed,
                    )
                elif line.startswith("ERROR:") or line.startswith("❌"):
                    self._task_failed = True
                    self._append_log(line)
                else:
                    self._try_update_progress_from_log(line)
                    self._append_log(line)
        except queue.Empty:
            pass
        self.after(LOG_POLL_MS, self._poll_log)

    def choose_file(self):
        p = filedialog.askopenfilename(title=self._text("file_dialog"))
        if p:
            self.handle_path(p)

    def choose_folder(self):
        p = filedialog.askdirectory(title=self._text("folder_dialog"))
        if p:
            self.handle_path(p)

    def handle_path(self, path):
        path = os.path.abspath(os.fspath(path))

        if not os.path.exists(path):
            self._task_failed = True
            self._set_status("status_failed", True)
            msg = get_gui_text(self._ui_lang(), "invalid_path", path=path)
            self.path_label.configure(text=msg)
            self._append_log(msg + "\n")
            return

        if self._running:
            self._append_log(self._text("busy"))
            return

        self._selected_path = path
        self._task_failed = False
        self._set_status(
            "status_processing_folder" if os.path.isdir(path) else "status_processing_file"
        )
        self.path_label.configure(text=path)

        while not self.log_q.empty():
            self.log_q.get_nowait()
        self.clear_log()
        self._set_controls_enabled(False)

        self.progress.configure(mode="determinate")

        if os.path.isdir(path):
            self._progress_mode = "decode"
            images = (
                glob.glob(os.path.join(path, "*.[pP][nN][gG]"))
                + glob.glob(os.path.join(path, "*.[jJ][pP][gG]"))
                + glob.glob(os.path.join(path, "*.[jJ][pP][eE][gG]"))
            )
            self._progress_total = len(images)
            self._progress_current = 0
            self.progress.set(0)
        else:
            self._progress_mode = "encode"
            self._progress_total = 0
            self._progress_current = 0
            self.progress.set(0)

        worker = threading.Thread(
            target=run_task_in_thread,
            args=(path, self._ui_lang(), self.log_q),
            daemon=True,
        )
        self._running = True
        worker.start()


if __name__ == "__main__":
    app = ModernGUI()
    app.mainloop()
