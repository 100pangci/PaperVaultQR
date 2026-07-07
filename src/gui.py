import io
import locale
import os
import queue
import sys
import threading
import webbrowser
from tkinter import filedialog

import customtkinter as ctk
from PIL import Image, ImageTk

from core import auto_split_qr, scanner_decoder
from core.auto_split_qr import QrLayoutConfig
from i18n import normalize_lang
from app_version import get_app_version
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


def resource_path(*parts):
    base_dir = getattr(sys, "_MEIPASS", APP_DIR)
    return os.path.join(base_dir, *parts)


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


def run_task_in_thread(paths, lang, log_q, config: QrLayoutConfig | None = None):
    old_stdout, old_stderr = sys.stdout, sys.stderr
    redirector = QueueRedirector(log_q)
    sys.stdout, sys.stderr = redirector, redirector

    try:
        if isinstance(paths, (str, os.PathLike)):
            targets = [paths]
        else:
            targets = list(paths)

        for path in targets:
            log_q.put(f"__FILE_START__::{path}")
            if os.path.isdir(path):
                scanner_decoder.decode_folder(path, lang=lang)
            else:
                auto_split_qr.process_file(path, lang=lang, config=config)
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
        self.default_qr_config = auto_split_qr.DEFAULT_CONFIG
        self.qr_error_choices = list(auto_split_qr.QR_ERROR_CHOICES)
        self.config_chunk_size_var = ctk.StringVar(value=str(self.default_qr_config.chunk_size))
        self.config_qr_error_var = ctk.StringVar(value=self.default_qr_config.qr_error)
        self.config_qr_width_var = ctk.StringVar(value=str(self.default_qr_config.qr_width_cm))
        self.config_font_size_var = ctk.StringVar(value=str(self.default_qr_config.font_size_label))
        self.config_cols_var = ctk.StringVar(value=str(self.default_qr_config.cols_per_page))
        self.config_margin_var = ctk.StringVar(value=str(self.default_qr_config.page_margin))
        self._running = False
        self._task_failed = False
        self._status_key = "status_ready"
        self._selected_path = ""
        self._selected_paths = []
        self._progress_mode = None  # "encode" | "decode"
        self._progress_total = 0
        self._progress_current = 0

        self._window_icon_mode = None
        self._window_icons = {}
        self._window_icon_paths = {}
        self._load_window_icons()
        self._update_window_icon()
        self.after(1000, self._sync_window_icon)

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

        self.settings_card = ctk.CTkFrame(self, corner_radius=10)
        self.settings_card.pack(fill="x", padx=20, pady=(5, 5))

        self.settings_title = ctk.CTkLabel(self.settings_card, text="", font=ui_font(14, "bold"))
        self.settings_title.grid(row=0, column=0, columnspan=6, sticky="w", padx=15, pady=(10, 8))

        self.setting_chunk_label = ctk.CTkLabel(self.settings_card, text="")
        self.setting_chunk_label.grid(row=1, column=0, sticky="w", padx=(15, 6), pady=(0, 8))
        self.setting_chunk_entry = ctk.CTkEntry(self.settings_card, width=90, textvariable=self.config_chunk_size_var)
        self.setting_chunk_entry.grid(row=1, column=1, sticky="w", pady=(0, 8))

        self.setting_error_label = ctk.CTkLabel(self.settings_card, text="")
        self.setting_error_label.grid(row=1, column=2, sticky="w", padx=(10, 6), pady=(0, 8))
        self.setting_error_menu = ctk.CTkOptionMenu(
            self.settings_card,
            variable=self.config_qr_error_var,
            values=self.qr_error_choices,
            width=90,
        )
        self.setting_error_menu.grid(row=1, column=3, sticky="w", pady=(0, 8))

        self.setting_width_label = ctk.CTkLabel(self.settings_card, text="")
        self.setting_width_label.grid(row=1, column=4, sticky="w", padx=(10, 6), pady=(0, 8))
        self.setting_width_entry = ctk.CTkEntry(self.settings_card, width=90, textvariable=self.config_qr_width_var)
        self.setting_width_entry.grid(row=1, column=5, sticky="w", padx=(0, 15), pady=(0, 8))

        self.setting_font_label = ctk.CTkLabel(self.settings_card, text="")
        self.setting_font_label.grid(row=2, column=0, sticky="w", padx=(15, 6), pady=(0, 10))
        self.setting_font_entry = ctk.CTkEntry(self.settings_card, width=90, textvariable=self.config_font_size_var)
        self.setting_font_entry.grid(row=2, column=1, sticky="w", pady=(0, 10))

        self.setting_cols_label = ctk.CTkLabel(self.settings_card, text="")
        self.setting_cols_label.grid(row=2, column=2, sticky="w", padx=(10, 6), pady=(0, 10))
        self.setting_cols_entry = ctk.CTkEntry(self.settings_card, width=90, textvariable=self.config_cols_var)
        self.setting_cols_entry.grid(row=2, column=3, sticky="w", pady=(0, 10))

        self.setting_margin_label = ctk.CTkLabel(self.settings_card, text="")
        self.setting_margin_label.grid(row=2, column=4, sticky="w", padx=(10, 6), pady=(0, 10))
        self.setting_margin_entry = ctk.CTkEntry(self.settings_card, width=90, textvariable=self.config_margin_var)
        self.setting_margin_entry.grid(row=2, column=5, sticky="w", padx=(0, 15), pady=(0, 10))

        # 第三行：冗余纠错
        self.setting_rs_label = ctk.CTkLabel(self.settings_card, text="")
        self.setting_rs_label.grid(row=3, column=0, sticky="w", padx=(15, 6), pady=(0, 10))

        self.config_rs_strength_var = ctk.StringVar(value="0")
        self.setting_rs_entry = ctk.CTkEntry(
            self.settings_card, width=90, textvariable=self.config_rs_strength_var
        )
        self.setting_rs_entry.grid(row=3, column=1, columnspan=5, sticky="w", padx=(0, 15), pady=(0, 10))
        self._set_rs_entry(self.default_qr_config.enable_redundancy, self.default_qr_config.rs_block_ratio)

        self.set_default_btn = ctk.CTkButton(
            self.settings_card,
            text="",
            width=120,
            fg_color="transparent",
            border_width=1,
            text_color=("gray10", "#DCE4EE"),
            font=ui_font(12),
            command=self.reset_qr_config_to_default,
        )
        self.set_default_btn.grid(row=5, column=0, sticky="w", padx=15, pady=(0, 10))

        # 初始化控件状态
        self.update_redundancy_ui()

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

    def _load_window_icons(self):
        self._window_icons = {}
        self._window_icon_paths = {}
        icon_defs = {
            "Light": {"png": "icon_dark.png", "ico": "icon_dark.ico"},
            "Dark": {"png": "icon_white.png", "ico": "icon_white.ico"},
        }
        sizes = (16, 24, 32, 48, 64, 128)
        for mode, files in icon_defs.items():
            png_path = resource_path("icon", files["png"])
            ico_path = resource_path("icon", files["ico"])
            self._window_icon_paths[mode] = {"png": png_path, "ico": ico_path}
            try:
                source = Image.open(png_path).convert("RGBA")
                square = min(source.size)
                left = (source.width - square) // 2
                top = (source.height - square) // 2
                source = source.crop((left, top, left + square, top + square))
                self._window_icons[mode] = [
                    ImageTk.PhotoImage(
                        source.resize((size, size), Image.Resampling.LANCZOS)
                    )
                    for size in sizes
                ]
            except Exception:
                self._window_icons[mode] = []

    def _update_window_icon(self):
        mode = ctk.get_appearance_mode().strip().lower()
        mode = "Dark" if mode == "dark" else "Light"
        if mode == self._window_icon_mode:
            return
        self._window_icon_mode = mode

        paths = self._window_icon_paths.get(mode, {})
        if os.name == "nt":
            ico_path = paths.get("ico", "")
            if ico_path and os.path.exists(ico_path):
                try:
                    self.iconbitmap(ico_path)
                    return
                except Exception:
                    pass

        icons = self._window_icons.get(mode, [])
        if icons:
            try:
                self.iconphoto(True, *icons)
            except Exception:
                pass

    def _sync_window_icon(self):
        self._update_window_icon()
        self.after(1000, self._sync_window_icon)

    def update_ui_texts(self, *args):
        base_title = self._text("title", "PaperVaultQR")
        self.title(f"{base_title} — {get_app_version()}")
        self.title_label.configure(text=base_title)
        self.subtitle_label.configure(text=self._text("subtitle"))
        self.lang_label.configure(text=self._text("language"))
        self.file_btn.configure(text=self._text("choose_file"))
        self.folder_btn.configure(text=self._text("choose_folder"))
        self.clear_btn.configure(text=self._text("clear_log"))
        self.log_label.configure(text=self._text("log"))
        self.info_label.configure(text=self._text("info_tip"))
        self.settings_title.configure(text=self._text("settings_title"))
        self.setting_chunk_label.configure(text=self._text("setting_chunk_size"))
        self.setting_error_label.configure(text=self._text("setting_qr_error"))
        self.setting_width_label.configure(text=self._text("setting_qr_width"))
        self.setting_font_label.configure(text=self._text("setting_font_size"))
        self.setting_cols_label.configure(text=self._text("setting_cols_per_page"))
        self.setting_margin_label.configure(text=self._text("setting_page_margin"))
        self.setting_rs_label.configure(text=self._text("setting_rs_strength"))
        self.set_default_btn.configure(text=self._text("set_default"))
        self.project_link_label.configure(text=PROJECT_URL)
        self.status_label.configure(text=self._text(self._status_key))
        self.path_label.configure(
            text=self._selected_path if self._selected_path else self._text("selected_none")
        )

        self.update_redundancy_ui()

    def _set_controls_enabled(self, enabled):
        state = "normal" if enabled else "disabled"
        self.lang_combo.configure(state=state)
        self.file_btn.configure(state=state)
        self.folder_btn.configure(state=state)
        self.clear_btn.configure(state=state)
        self.setting_chunk_entry.configure(state=state)
        self.setting_error_menu.configure(state=state)
        self.setting_width_entry.configure(state=state)
        self.setting_font_entry.configure(state=state)
        self.setting_cols_entry.configure(state=state)
        self.setting_margin_entry.configure(state=state)
        self.setting_rs_entry.configure(state=state)
        self.set_default_btn.configure(state=state)

    def _set_rs_entry(self, enabled: bool, ratio: float):
        self.config_rs_strength_var.set(str(int(round(ratio * 100)) if enabled else "0"))

    def update_redundancy_ui(self):
        pass

    def clear_log(self):
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

    def _format_selected_paths(self, paths):
        if not paths:
            return ""

        if len(paths) == 1:
            return paths[0]

        display_names = [os.path.basename(p) or p for p in paths[:3]]
        summary = ", ".join(display_names)
        remaining = len(paths) - len(display_names)
        if remaining > 0:
            summary += f" ... (+{remaining})"
        return summary

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

    def _poll_log(self):
        try:
            while True:
                line = self.log_q.get_nowait()

                # 去除换行符，防止解析异常
                clean_line = line.strip()

                if clean_line == "__DONE__":
                    if not self._task_failed:
                        self.progress.set(1.0)
                    self._running = False
                    self._set_controls_enabled(True)
                    self._set_status(
                        "status_failed" if self._task_failed else "status_done",
                        self._task_failed,
                    )
                    self.path_label.configure(
                        text=self._selected_path if self._selected_path else self._text("selected_none")
                    )

                elif clean_line.startswith("__FILE_START__::"):
                    current_path = clean_line.split("::", 1)[1]
                    self.progress.set(0)
                    self._progress_mode = None
                    self._progress_total = 0
                    self._progress_current = 0
                    self.path_label.configure(text=current_path)

                # 🌟 新增：拦截底层发来的纯净进度指令，绝不打印到屏幕上！
                elif clean_line.startswith("__PROGRESS__::"):
                    parts = clean_line.split("::")
                    if len(parts) >= 3:
                        current = int(parts[1])
                        total_str = parts[2]
                        if total_str != "?":  # 忽略未知总数的进度条更新
                            self._update_progress(current, int(total_str))

                elif clean_line.startswith("ERROR:") or clean_line.startswith("❌"):
                    self._task_failed = True
                    self._append_log(line)  # 注意：这里保留原始 line 以保留换行符

                else:
                    # 只有真正的业务文本，才会走到这里显示在 GUI 上
                    self._append_log(line)

        except queue.Empty:
            pass
        self.after(LOG_POLL_MS, self._poll_log)

    def reset_qr_config_to_default(self):
        cfg = self.default_qr_config
        self.config_chunk_size_var.set(str(cfg.chunk_size))
        self.config_qr_error_var.set(cfg.qr_error)
        self.config_qr_width_var.set(str(cfg.qr_width_cm))
        self.config_font_size_var.set(str(cfg.font_size_label))
        self.config_cols_var.set(str(cfg.cols_per_page))
        self.config_margin_var.set(str(cfg.page_margin))
        self._set_rs_entry(cfg.enable_redundancy, cfg.rs_block_ratio)

    def _build_qr_config_from_ui(self) -> QrLayoutConfig | None:
        lang = self._ui_lang()
        try:
            chunk_size = int(self.config_chunk_size_var.get().strip())
            qr_error = self.config_qr_error_var.get().strip().upper()
            qr_width_cm = float(self.config_qr_width_var.get().strip())
            font_size_label = int(self.config_font_size_var.get().strip())
            cols_per_page = int(self.config_cols_var.get().strip())
            page_margin = float(self.config_margin_var.get().strip())
        except ValueError:
            msg = self._text("invalid_config_number")
            self._task_failed = True
            self._set_status("status_failed", True)
            self._append_log(msg + "\n")
            self.path_label.configure(text=msg)
            return None

        if chunk_size <= 0 or qr_width_cm <= 0 or font_size_label <= 0 or cols_per_page <= 0 or page_margin < 0:
            msg = self._text("invalid_config_range")
            self._task_failed = True
            self._set_status("status_failed", True)
            self._append_log(msg + "\n")
            self.path_label.configure(text=msg)
            return None

        if qr_error not in self.qr_error_choices:
            msg = get_gui_text(
                lang,
                "invalid_config_qr_error",
                choices=", ".join(self.qr_error_choices),
            )
            self._task_failed = True
            self._set_status("status_failed", True)
            self._append_log(msg + "\n")
            self.path_label.configure(text=msg)
            return None

        rs_str = self.config_rs_strength_var.get().strip()
        try:
            rs_pct = int(rs_str)
        except ValueError:
            rs_pct = 0
        rs_pct = max(0, min(100, rs_pct))

        return QrLayoutConfig(
            chunk_size=chunk_size,
            qr_error=qr_error,
            qr_width_cm=qr_width_cm,
            font_size_label=font_size_label,
            cols_per_page=cols_per_page,
            page_margin=page_margin,
            enable_redundancy=rs_pct > 0,
            rs_block_ratio=rs_pct / 100.0,
        )

    def choose_file(self):
        p = filedialog.askopenfilenames(title=self._text("file_dialog"))
        if p:
            self.handle_path(p)

    def choose_folder(self):
        p = filedialog.askdirectory(title=self._text("folder_dialog"))
        if p:
            self.handle_path(p)

    def handle_path(self, path):
        if isinstance(path, (str, os.PathLike)):
            paths = [os.path.abspath(os.fspath(path))]
        else:
            paths = [os.path.abspath(os.fspath(p)) for p in path if p]

        if not paths:
            return

        if self._running:
            self._append_log(self._text("busy"))
            return

        for selected_path in paths:
            if not os.path.exists(selected_path):
                self._task_failed = True
                self._set_status("status_failed", True)
                msg = get_gui_text(self._ui_lang(), "invalid_path", path=selected_path)
                self.path_label.configure(text=msg)
                self._append_log(msg + "\n")
                return

        self._selected_paths = paths
        self._selected_path = self._format_selected_paths(paths)
        self._task_failed = False
        self._set_status(
            "status_processing_folder"
            if len(paths) == 1 and os.path.isdir(paths[0])
            else "status_processing_file"
        )
        self.path_label.configure(text=self._selected_path if self._selected_path else self._text("selected_none"))

        while not self.log_q.empty():
            self.log_q.get_nowait()
        self.clear_log()
        self._set_controls_enabled(False)

        self.progress.configure(mode="determinate")
        self._progress_mode = "encode"
        self._progress_total = 0
        self._progress_current = 0
        self.progress.set(0)

        config = self._build_qr_config_from_ui()
        if config is None:
            self._set_controls_enabled(True)
            return

        worker = threading.Thread(
            target=run_task_in_thread,
            args=(paths, self._ui_lang(), self.log_q, config),
            daemon=True,
        )
        self._running = True
        worker.start()


if __name__ == "__main__":
    app = ModernGUI()
    app.mainloop()
