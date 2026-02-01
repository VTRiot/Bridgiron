#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bridgiron - パターン設定GUIツール

ブックマークレットの生成と設定ファイルの管理を行う。
実行方法: python bridgiron_gui.py
"""

import tkinter as tk
from tkinter import ttk, messagebox
import os
import re
import json
import webbrowser
from datetime import datetime
import ctypes
import threading
import time
import pyperclip
from ctypes import wintypes, WINFUNCTYPE
from pathlib import Path
from io_utils import read_file_with_encoding
from winapi import (
    is_cli_active, get_cli_hwnd, is_process_active, is_window_valid,
    get_window_rect, get_monitor_work_area, is_window_maximized,
    get_foreground_window, get_window_parent
)
from cc_report import get_cc_report
from settings import Settings, SETTINGS_DIR, SETTINGS_FILE
from copy_history import CopyHistory, ClipboardWatcher
from history_popup import HistoryPopup

# ========================================
# 定数
# ========================================

VERSION = "1.13"

# プロジェクトルート（EXE実行時とスクリプト実行時で分岐）
import sys
import shutil
if getattr(sys, 'frozen', False):
    # EXEとして実行時（PyInstaller）
    SCRIPT_DIR = Path(sys.executable).resolve().parent
    PROJECT_ROOT = SCRIPT_DIR  # EXEはプロジェクトルートに配置
else:
    # スクリプトとして実行時
    SCRIPT_DIR = Path(__file__).resolve().parent
    PROJECT_ROOT = SCRIPT_DIR.parent.parent

# パス定義（インストール先）
INSTALL_CONFIG_DIR = PROJECT_ROOT / "_Config"
DOC_DIR = PROJECT_ROOT / "_DOC"
JS_DIR = PROJECT_ROOT / "src" / "js"

TEMPLATE_FILE = JS_DIR / "bookmarklet_gpt_extract.js"
README_FILE = DOC_DIR / "Readme.html"

# 設定ファイルの保存先（AppData）
def get_settings_dir():
    """設定ファイルの保存ディレクトリを取得"""
    if os.name == 'nt':  # Windows
        appdata = os.environ.get('APPDATA', '')
        if appdata:
            settings_dir = Path(appdata) / 'Bridgiron'
        else:
            # フォールバック: EXEと同じ場所
            settings_dir = PROJECT_ROOT / '_Config'
    else:
        # 非Windows（フォールバック）
        settings_dir = PROJECT_ROOT / '_Config'

    # ディレクトリがなければ作成
    settings_dir.mkdir(parents=True, exist_ok=True)
    return settings_dir

SETTINGS_DIR = get_settings_dir()

# 設定ファイルパス（AppData）
SETTINGS_FILE = SETTINGS_DIR / 'settings.txt'
KEYWORDS_FILE = SETTINGS_DIR / "keywords.txt"
PHRASES_FILE = SETTINGS_DIR / "phrases.txt"
DELIMITERS_FILE = SETTINGS_DIR / "delimiters.txt"

def ensure_config_files():
    """設定ファイルが AppData にあることを確認、なければインストール先からコピー（BOM付きUTF-8）"""
    config_files = ['settings.txt', 'keywords.txt', 'phrases.txt', 'delimiters.txt']

    for filename in config_files:
        dest_file = SETTINGS_DIR / filename
        if dest_file.exists():
            continue

        # インストール先の設定ファイル
        install_file = INSTALL_CONFIG_DIR / filename
        if install_file.exists():
            try:
                # 読み込み（複数エンコーディング対応）
                content = read_file_with_encoding(install_file)

                if content:
                    # BOM付きUTF-8で保存
                    with open(dest_file, 'w', encoding='utf-8-sig') as f:
                        f.write(content)
                    print(f"[DEBUG] Copied {filename} with UTF-8 BOM")
            except Exception as e:
                print(f"[DEBUG] Failed to copy {filename}: {e}")

def setup_debug_console():
    """デバッグモード時にコンソールウィンドウを作成"""
    if not getattr(sys, 'frozen', False):
        # スクリプト実行時は何もしない（既にコンソールがある）
        return

    # まずログファイルに出力（コンソールがなくても確認できる）
    log_dir = Path(os.environ.get('APPDATA', '.')) / 'Bridgiron'
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / 'debug_startup.log'
    settings_file = log_dir / 'settings.txt'

    with open(log_file, 'w', encoding='utf-8') as f:
        f.write(f"[DEBUG] setup_debug_console started\n")
        f.write(f"[DEBUG] settings_file = {settings_file}\n")
        f.write(f"[DEBUG] exists = {settings_file.exists()}\n")

        debug_mode = "0"
        if settings_file.exists():
            try:
                # 複数エンコーディングを試す
                content = read_file_with_encoding(settings_file)

                if content:
                    f.write(f"[DEBUG] Read settings file successfully\n")
                    for line in content.splitlines():
                        f.write(f"[DEBUG] Line: {line}\n")
                        if line.strip().startswith('F_DebugMode='):
                            debug_mode = line.strip().split('=', 1)[1].strip()
                            f.write(f"[DEBUG] Found F_DebugMode={debug_mode}\n")
                            break
                else:
                    f.write(f"[DEBUG] Failed to read settings file\n")
            except Exception as e:
                f.write(f"[DEBUG] Exception: {e}\n")

        f.write(f"[DEBUG] Final debug_mode = {debug_mode}\n")

    if debug_mode == "1":
        import ctypes
        ctypes.windll.kernel32.AllocConsole()
        sys.stdout = open('CONOUT$', 'w', encoding='utf-8')
        sys.stderr = sys.stdout
        print("[DEBUG] Debug console enabled")
        print(f"[DEBUG] PROJECT_ROOT: {PROJECT_ROOT}")
        print(f"[DEBUG] SETTINGS_FILE: {SETTINGS_FILE}")

# 起動時に設定ファイルを確保し、デバッグコンソールをセットアップ
ensure_config_files()
setup_debug_console()

# カスタム指示文
CUSTOM_INSTRUCTIONS = """Claude Codeに渡すプロンプトを出力する際は、以下のルールに従ってください：
- プロンプトの直前に「---SOP---」を1行で記載
- プロンプトの直後に「---EOP---」を1行で記載
- 1つの発言につき、SOP/EOPのペアは1つまでとする"""

# ========================================
# ダークモード配色
# ========================================

COLORS = {
    "bg": "#1e1e1e",
    "fg": "#e0e0e0",
    "btn_bg": "#3c3c3c",
    "btn_fg": "#ffffff",
    "accent": "#10a37f",
    "entry_bg": "#2d2d2d",
    "entry_fg": "#ffffff",
    "label_fg": "#a0a0a0",
    "border": "#404040",
    "menu_bg": "#2d2d2d",
    "menu_fg": "#e0e0e0",
}

# ========================================
# 言語リソース
# ========================================

LANG = {
    "ja": {
        "window_title": "Bridgiron",
        "menu_file": "ファイル",
        "menu_language": "言語",
        "menu_exit": "終了",
        "section_claudecode": "Claude Code",
        "label_project_path": "プロジェクトパス:",
        "label_cc_prefix": "枕文:",
        "default_cc_prefix": "Claude Codeの報告は下記。\n",
        "btn_copy_cc_report": "CC報告をコピー (Alt+C)",
        "label_mini_position": "ミニウィンドウ位置:",
        "mini_pos_cli": "CLIウィンドウ左下",
        "mini_pos_last": "最後の位置",
        "msg_no_project": "プロジェクトパスが見つかりません",
        "msg_no_log": "Claude Codeのログが見つかりません",
        "msg_no_report": "報告が見つかりませんでした",
        "section_bookmarklet": "ブックマークレット",
        "label_title": "タイトル:",
        "btn_copy_title": "タイトルをコピー",
        "btn_copy_code": "コードをコピー",
        "section_chatgpt": "ChatGPT設定",
        "btn_copy_instructions": "カスタム指示文をコピー",
        "section_config": "設定ファイル編集",
        "section_help": "ヘルプ",
        "btn_readme": "使い方を見る",
        "first_run_message": "まずはReadMeを見てね。",
        "msg_copied": "コピーしました",
        "msg_file_not_found": "ファイルが見つかりません: ",
        "msg_template_not_found": "テンプレートファイルが見つかりません",
        "select_project_folder": "プロジェクトフォルダを選択",
        "footer_version": "Bridgiron v{}",
        "history_gpt_to_cc": "GPT→CC",
        "history_cc_to_gpt": "CC→GPT",
        "history_title_gpt": "GPT→CC履歴",
        "history_title_cc": "CC→GPT履歴",
        "no_history": "履歴がありません",
        "copied_from_history": "履歴からコピーしました",
    },
    "en": {
        "window_title": "Bridgiron",
        "menu_file": "File",
        "menu_language": "Language",
        "menu_exit": "Exit",
        "section_claudecode": "Claude Code",
        "label_project_path": "Project Path:",
        "label_cc_prefix": "Prefix:",
        "default_cc_prefix": "Claude Code's report is below.\n",
        "btn_copy_cc_report": "Copy CC Report (Alt+C)",
        "label_mini_position": "Mini window position:",
        "mini_pos_cli": "CLI window bottom-left",
        "mini_pos_last": "Last position",
        "msg_no_project": "Project path not found",
        "msg_no_log": "Claude Code log not found",
        "msg_no_report": "Report not found",
        "section_bookmarklet": "Bookmarklet",
        "label_title": "Title:",
        "btn_copy_title": "Copy Title",
        "btn_copy_code": "Copy Code",
        "section_chatgpt": "ChatGPT Settings",
        "btn_copy_instructions": "Copy Custom Instructions",
        "section_config": "Edit Config Files",
        "section_help": "Help",
        "btn_readme": "Open Readme",
        "first_run_message": "First of all, please check the ReadMe!",
        "msg_copied": "Copied",
        "msg_file_not_found": "File not found: ",
        "msg_template_not_found": "Template file not found",
        "select_project_folder": "Select Project Folder",
        "footer_version": "Bridgiron v{}",
        "history_gpt_to_cc": "GPT→CC",
        "history_cc_to_gpt": "CC→GPT",
        "history_title_gpt": "GPT→CC History",
        "history_title_cc": "CC→GPT History",
        "no_history": "No history",
        "copied_from_history": "Copied from history",
    }
}

# ========================================
# ブックマークレット生成
# ========================================

def read_config_file(filepath):
    """設定ファイルを読み込んでリストで返す"""
    if not filepath.exists():
        return []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = [line.strip() for line in f if line.strip()]
            return lines
    except Exception:
        return []

def generate_bookmarklet():
    """ブックマークレットコードを生成する"""
    # テンプレート読み込み
    if not TEMPLATE_FILE.exists():
        return None

    with open(TEMPLATE_FILE, 'r', encoding='utf-8') as f:
        template = f.read()

    # 設定ファイル読み込み
    keywords = read_config_file(KEYWORDS_FILE)
    phrases = read_config_file(PHRASES_FILE)
    delimiters = read_config_file(DELIMITERS_FILE)

    # PATTERNS定数を生成
    def to_js_array(items):
        escaped = [item.replace('\\', '\\\\').replace('"', '\\"') for item in items]
        return '[' + ','.join(f'"{item}"' for item in escaped) + ']'

    new_patterns = f'''var PATTERNS={{startMarker:"---SOP---",endMarker:"---EOP---",phrases:{to_js_array(phrases)},delimiters:{to_js_array(delimiters)},keywords:{to_js_array(keywords)}}};'''

    # PATTERNS定義部分を置換
    # パターン: var PATTERNS = { ... }; を探して置換
    pattern = r'var PATTERNS\s*=\s*\{[^;]+\};'
    template = re.sub(pattern, new_patterns, template, flags=re.DOTALL)

    # 圧縮処理
    # コメント除去
    template = re.sub(r'/\*[\s\S]*?\*/', '', template)
    template = re.sub(r'//.*$', '', template, flags=re.MULTILINE)

    # 改行・余分な空白を除去
    template = re.sub(r'\s+', ' ', template)
    template = re.sub(r'\s*([{};,()=+\-*/<>!&|?:])\s*', r'\1', template)

    # 先頭・末尾の空白を除去
    template = template.strip()

    # javascript: プレフィックスを付与
    bookmarklet = 'javascript:' + template

    return bookmarklet

# ========================================
# ダークモードスタイル設定
# ========================================

def setup_dark_style(root):
    """ダークモードスタイルを設定"""
    root.configure(bg=COLORS["bg"])

    style = ttk.Style()

    # テーマを設定（clam が最もカスタマイズしやすい）
    style.theme_use('clam')

    # フレーム
    style.configure("TFrame", background=COLORS["bg"])

    # ラベルフレーム
    style.configure("TLabelframe", background=COLORS["bg"], bordercolor=COLORS["border"])
    style.configure("TLabelframe.Label", background=COLORS["bg"], foreground=COLORS["label_fg"])

    # ラベル
    style.configure("TLabel", background=COLORS["bg"], foreground=COLORS["fg"])

    # ボタン
    style.configure("TButton",
                    background=COLORS["btn_bg"],
                    foreground=COLORS["btn_fg"],
                    bordercolor=COLORS["border"],
                    focuscolor=COLORS["accent"])
    style.map("TButton",
              background=[("active", COLORS["accent"]), ("pressed", COLORS["accent"])],
              foreground=[("active", COLORS["btn_fg"]), ("pressed", COLORS["btn_fg"])])

    # 大きいボタン（CC報告用）
    style.configure("Large.TButton",
                    background=COLORS["accent"],
                    foreground=COLORS["btn_fg"],
                    bordercolor=COLORS["border"],
                    focuscolor=COLORS["accent"],
                    padding=(20, 15),
                    font=("", 11, "bold"))
    style.map("Large.TButton",
              background=[("active", "#0d8a6a"), ("pressed", "#0d8a6a")],
              foreground=[("active", COLORS["btn_fg"]), ("pressed", COLORS["btn_fg"])])

    # エントリー
    style.configure("TEntry",
                    fieldbackground=COLORS["entry_bg"],
                    foreground=COLORS["entry_fg"],
                    bordercolor=COLORS["border"],
                    insertcolor=COLORS["entry_fg"])

    # コンボボックス
    style.configure("TCombobox",
                    fieldbackground=COLORS["entry_bg"],
                    background=COLORS["entry_bg"],
                    foreground=COLORS["entry_fg"],
                    arrowcolor=COLORS["fg"],
                    bordercolor=COLORS["border"])
    style.map("TCombobox",
              fieldbackground=[("readonly", COLORS["entry_bg"])],
              selectbackground=[("readonly", COLORS["accent"])],
              selectforeground=[("readonly", COLORS["btn_fg"])])

    return style

# ========================================
# GUIアプリケーション
# ========================================

class BridgironApp:
    def __init__(self, root):
        self.root = root
        self.settings = Settings()

        # コピー履歴インスタンス
        self.copy_history = CopyHistory(SETTINGS_DIR / 'copy_history.json')

        # 履歴ポップアップの参照を保持
        self.history_popup_gpt = None
        self.history_popup_cc = None

        # クリップボード監視開始
        self.clipboard_watcher = ClipboardWatcher(
            on_detect_callback=self._on_gpt_prompt_detected
        )
        self.clipboard_watcher.start()

        # ダークモードスタイル設定
        self.style = setup_dark_style(root)

        # ウィンドウ設定
        self.root.title(LANG[self.settings.language]["window_title"])
        if self.settings.first_run == "1":
            # 初回起動時: メッセージ分の高さを追加
            self.root.geometry("600x690")
            self.root.minsize(500, 620)
            self.full_geometry = "600x690"
        else:
            # 2回目以降: 通常の高さ
            self.root.geometry("600x640")
            self.root.minsize(500, 570)
            self.full_geometry = "600x640"

        # ミニモード関連
        self.is_mini_mode = False
        self.last_mini_position = None
        self.hook = None
        self.last_cli_rect = None  # CLIの前回位置を記録
        self.last_cli_hwnd = None  # CLIのハンドルを保持
        self.tick_count = 0  # 統合メインループ用ティックカウンター

        # UIコンポーネント参照用
        self.ui_elements = {}

        # 言語選択バー作成
        self.create_language_bar()

        # メインフレーム
        self.main_frame = ttk.Frame(root, padding="10")
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # UI構築
        self.create_ui()

        # ミニモード用フレーム作成
        self.create_mini_frame()

        # ウィンドウクローズ時のクリーンアップ設定
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # 統合メインループを開始
        self.start_main_loop()

    def get_text(self, key):
        """現在の言語でテキストを取得"""
        return LANG[self.settings.language].get(key, key)

    def create_language_bar(self):
        """言語選択バーを作成"""
        top_frame = tk.Frame(self.root, bg=COLORS["bg"])
        top_frame.pack(fill=tk.X, padx=10, pady=(5, 0))

        # 言語選択コンボボックス（右寄せ）
        self.lang_combo = ttk.Combobox(top_frame, values=["日本語", "English"],
                                        state="readonly", width=10)
        # 現在の言語を設定
        if self.settings.language == "ja":
            self.lang_combo.set("日本語")
        else:
            self.lang_combo.set("English")
        self.lang_combo.pack(side=tk.RIGHT)
        self.lang_combo.bind("<<ComboboxSelected>>", self.on_language_change)

    def create_ui(self):
        """メインUIを構築"""
        self.current_row = 0
        self._create_section_claudecode()
        self._create_section_bookmarklet()
        self._create_section_chatgpt()
        self._create_section_config()
        self._create_section_help()
        self._create_footer()
        self.main_frame.columnconfigure(0, weight=1)

    def _create_section_claudecode(self):
        """Claude Code セクションを構築"""
        section_cc = ttk.LabelFrame(self.main_frame, text=self.get_text("section_claudecode"), padding="10")
        section_cc.grid(row=self.current_row, column=0, sticky="ew", pady=(0, 10))
        self.ui_elements["section_claudecode"] = section_cc
        self.current_row += 1

        # プロジェクトパス入力
        path_frame = tk.Frame(section_cc, bg=COLORS["bg"])
        path_frame.pack(fill=tk.X, pady=(0, 5))

        self.project_path_label = ttk.Label(path_frame, text=self.get_text("label_project_path"))
        self.project_path_label.pack(side=tk.LEFT)
        self.ui_elements["label_project_path"] = self.project_path_label

        # 参照ボタン（右端に配置するため先にpack）
        self.browse_btn = tk.Button(
            path_frame,
            text="...",
            command=self.browse_project_path,
            bg=COLORS["btn_bg"],
            fg=COLORS["btn_fg"],
            relief="flat",
            cursor="hand2",
            width=3
        )
        self.browse_btn.pack(side=tk.RIGHT, padx=(5, 0))

        # 入力欄（参照ボタンの左側）
        self.project_path_entry = ttk.Entry(path_frame, width=50)
        self.project_path_entry.insert(0, self.settings.project_path)
        self.project_path_entry.pack(side=tk.LEFT, padx=(5, 0), fill=tk.X, expand=True)
        self.project_path_entry.bind("<FocusOut>", self.on_project_path_change)

        # 枕文入力
        prefix_frame = ttk.Frame(section_cc)
        prefix_frame.pack(fill=tk.X, pady=(0, 10))

        self.cc_prefix_label = ttk.Label(prefix_frame, text=self.get_text("label_cc_prefix"))
        self.cc_prefix_label.pack(side=tk.LEFT)
        self.ui_elements["label_cc_prefix"] = self.cc_prefix_label

        self.cc_prefix_entry = ttk.Entry(prefix_frame, width=50)
        self.cc_prefix_entry.insert(0, self.settings.cc_prefix.replace("\n", "\\n"))
        self.cc_prefix_entry.pack(side=tk.LEFT, padx=(5, 0), fill=tk.X, expand=True)
        self.cc_prefix_entry.bind("<FocusOut>", self.on_cc_prefix_change)

        # ミニウィンドウ位置設定
        mini_pos_frame = ttk.Frame(section_cc)
        mini_pos_frame.pack(fill=tk.X, pady=(0, 10))

        self.mini_pos_label = ttk.Label(mini_pos_frame, text=self.get_text("label_mini_position"))
        self.mini_pos_label.pack(side=tk.LEFT)
        self.ui_elements["label_mini_position"] = self.mini_pos_label

        self.mini_pos_combo = ttk.Combobox(mini_pos_frame,
                                            values=[self.get_text("mini_pos_cli"),
                                                    self.get_text("mini_pos_last")],
                                            state="readonly", width=20)
        # 現在の設定を反映
        if self.settings.mini_window_position == "last_position":
            self.mini_pos_combo.set(self.get_text("mini_pos_last"))
        else:
            self.mini_pos_combo.set(self.get_text("mini_pos_cli"))
        self.mini_pos_combo.pack(side=tk.LEFT, padx=(5, 0))
        self.mini_pos_combo.bind("<<ComboboxSelected>>", self.on_mini_pos_change)

        # 大きいボタン（幅いっぱい）
        self.btn_copy_cc_report = ttk.Button(section_cc, text=self.get_text("btn_copy_cc_report"),
                                              style="Large.TButton",
                                              command=self.copy_cc_report)
        self.btn_copy_cc_report.pack(fill=tk.X, pady=(5, 0))
        self.ui_elements["btn_copy_cc_report"] = self.btn_copy_cc_report

        # 履歴ボタン用フレーム（左右分割）
        history_btn_frame = tk.Frame(section_cc, bg='#2d2d2d')
        history_btn_frame.pack(fill='x', pady=(5, 0))

        # 左：GPT→CC履歴ボタン
        self.history_gpt_btn = tk.Button(
            history_btn_frame,
            text=self.get_text("history_gpt_to_cc"),
            command=lambda: self.show_history_popup("gpt_to_cc"),
            bg='#ff69b4',
            fg='white',
            activebackground='#ff1493',
            activeforeground='white',
            font=('Arial', 9),
            relief='flat',
            cursor='hand2'
        )
        self.history_gpt_btn.pack(side='left', fill='x', expand=True, padx=(0, 2))

        # 右：CC→GPT履歴ボタン
        self.history_cc_btn = tk.Button(
            history_btn_frame,
            text=self.get_text("history_cc_to_gpt"),
            command=lambda: self.show_history_popup("cc_to_gpt"),
            bg='#9370db',
            fg='white',
            activebackground='#7b68ee',
            activeforeground='white',
            font=('Arial', 9),
            relief='flat',
            cursor='hand2'
        )
        self.history_cc_btn.pack(side='left', fill='x', expand=True, padx=(2, 0))

        # キーボードショートカット Alt+C
        self.root.bind("<Alt-c>", lambda e: self.copy_cc_report())

    def _create_section_bookmarklet(self):
        """ブックマークレット セクションを構築"""
        section_bm = ttk.LabelFrame(self.main_frame, text=self.get_text("section_bookmarklet"), padding="10")
        section_bm.grid(row=self.current_row, column=0, sticky="ew", pady=(0, 10))
        self.ui_elements["section_bookmarklet"] = section_bm
        self.current_row += 1

        # タイトル入力
        title_frame = ttk.Frame(section_bm)
        title_frame.pack(fill=tk.X, pady=(0, 5))

        self.title_label = ttk.Label(title_frame, text=self.get_text("label_title"))
        self.title_label.pack(side=tk.LEFT)
        self.ui_elements["label_title"] = self.title_label

        self.title_entry = ttk.Entry(title_frame, width=40)
        self.title_entry.insert(0, self.settings.bookmarklet_title)
        self.title_entry.pack(side=tk.LEFT, padx=(5, 0), fill=tk.X, expand=True)
        self.title_entry.bind("<FocusOut>", self.on_title_change)

        # ボタン
        btn_frame_bm = ttk.Frame(section_bm)
        btn_frame_bm.pack(fill=tk.X)

        self.btn_copy_title = ttk.Button(btn_frame_bm, text=self.get_text("btn_copy_title"),
                                          command=self.copy_title)
        self.btn_copy_title.pack(side=tk.LEFT, padx=(0, 5))
        self.ui_elements["btn_copy_title"] = self.btn_copy_title

        self.btn_copy_code = ttk.Button(btn_frame_bm, text=self.get_text("btn_copy_code"),
                                         command=self.copy_code)
        self.btn_copy_code.pack(side=tk.LEFT)
        self.ui_elements["btn_copy_code"] = self.btn_copy_code

    def _create_section_chatgpt(self):
        """ChatGPT設定 セクションを構築"""
        section_gpt = ttk.LabelFrame(self.main_frame, text=self.get_text("section_chatgpt"), padding="10")
        section_gpt.grid(row=self.current_row, column=0, sticky="ew", pady=(0, 10))
        self.ui_elements["section_chatgpt"] = section_gpt
        self.current_row += 1

        self.btn_copy_instructions = ttk.Button(section_gpt, text=self.get_text("btn_copy_instructions"),
                                                 command=self.copy_instructions)
        self.btn_copy_instructions.pack(anchor=tk.W)
        self.ui_elements["btn_copy_instructions"] = self.btn_copy_instructions

    def _create_section_config(self):
        """設定ファイル編集 セクションを構築"""
        section_cfg = ttk.LabelFrame(self.main_frame, text=self.get_text("section_config"), padding="10")
        section_cfg.grid(row=self.current_row, column=0, sticky="ew", pady=(0, 10))
        self.ui_elements["section_config"] = section_cfg
        self.current_row += 1

        btn_frame_cfg = tk.Frame(section_cfg, bg=COLORS["bg"])
        btn_frame_cfg.pack(fill=tk.X)

        # keywords.txt, phrases.txt, delimiters.txt ボタン（左側）
        tk.Button(btn_frame_cfg, text="keywords.txt",
                  command=lambda: self.open_file(KEYWORDS_FILE),
                  bg=COLORS["btn_bg"], fg=COLORS["btn_fg"],
                  relief="flat", cursor="hand2").pack(side=tk.LEFT, padx=(0, 5))
        tk.Button(btn_frame_cfg, text="phrases.txt",
                  command=lambda: self.open_file(PHRASES_FILE),
                  bg=COLORS["btn_bg"], fg=COLORS["btn_fg"],
                  relief="flat", cursor="hand2").pack(side=tk.LEFT, padx=(0, 5))
        tk.Button(btn_frame_cfg, text="delimiters.txt",
                  command=lambda: self.open_file(DELIMITERS_FILE),
                  bg=COLORS["btn_bg"], fg=COLORS["btn_fg"],
                  relief="flat", cursor="hand2").pack(side=tk.LEFT, padx=(0, 5))

        # 区切り線
        tk.Label(btn_frame_cfg, text="|", bg=COLORS["bg"], fg="#666666",
                 font=("Arial", 12)).pack(side=tk.LEFT, padx=10)

        # settings.txt ボタン（右端）
        tk.Button(btn_frame_cfg, text="settings.txt",
                  command=lambda: self.open_file(SETTINGS_FILE),
                  bg=COLORS["btn_bg"], fg=COLORS["btn_fg"],
                  relief="flat", cursor="hand2").pack(side=tk.LEFT)

    def _create_section_help(self):
        """ヘルプ セクションを構築"""
        section_help = ttk.LabelFrame(self.main_frame, text=self.get_text("section_help"), padding="10")
        section_help.grid(row=self.current_row, column=0, sticky="ew", pady=(0, 10))
        self.ui_elements["section_help"] = section_help
        self.current_row += 1

        # 初回起動メッセージ（first_run=1の時のみ表示）
        self.first_run_label = tk.Label(
            section_help,
            text=self.get_text("first_run_message"),
            bg=COLORS["bg"],
            fg="#ffcc00",  # 黄色で目立たせる
            font=("Arial", 10, "bold")
        )
        if self.settings.first_run == "1":
            self.first_run_label.pack(anchor=tk.W, pady=(0, 5))
        self.ui_elements["first_run_label"] = self.first_run_label

        # ReadMeボタン（tk.Buttonで色変更可能に）
        self.btn_readme = tk.Button(
            section_help,
            text=self.get_text("btn_readme"),
            command=self.open_readme,
            bg="#e63946" if self.settings.first_run == "1" else COLORS["btn_bg"],
            fg="white",
            font=("Arial", 9, "bold"),
            relief="flat",
            cursor="hand2",
            activebackground="#cc0000" if self.settings.first_run == "1" else "#4a4a4a",
            activeforeground="white"
        )
        self.btn_readme.pack(anchor=tk.W)
        self.ui_elements["btn_readme"] = self.btn_readme

    def _create_footer(self):
        """フッターを構築"""
        footer = ttk.Label(self.main_frame, text=self.get_text("footer_version").format(VERSION))
        footer.grid(row=self.current_row, column=0, sticky="e", pady=(10, 0))
        self.ui_elements["footer_version"] = footer

    def on_language_change(self, event=None):
        """言語選択コンボボックスの変更時"""
        selected = self.lang_combo.get()
        lang_code = "ja" if selected == "日本語" else "en"

        if lang_code == self.settings.language:
            return

        self.settings.language = lang_code
        self.settings.save()
        self.update_ui_texts()

    def update_ui_texts(self):
        """UIテキストを更新"""
        # セクションラベル更新
        self.ui_elements["section_claudecode"].config(text=self.get_text("section_claudecode"))
        self.ui_elements["section_bookmarklet"].config(text=self.get_text("section_bookmarklet"))
        self.ui_elements["section_chatgpt"].config(text=self.get_text("section_chatgpt"))
        self.ui_elements["section_config"].config(text=self.get_text("section_config"))
        self.ui_elements["section_help"].config(text=self.get_text("section_help"))

        # Claude Code セクション
        self.project_path_label.config(text=self.get_text("label_project_path"))
        self.cc_prefix_label.config(text=self.get_text("label_cc_prefix"))
        self.mini_pos_label.config(text=self.get_text("label_mini_position"))
        # ミニウィンドウ位置コンボボックスの値を更新
        current_pos = self.settings.mini_window_position
        self.mini_pos_combo.config(values=[self.get_text("mini_pos_cli"),
                                           self.get_text("mini_pos_last")])
        if current_pos == "last_position":
            self.mini_pos_combo.set(self.get_text("mini_pos_last"))
        else:
            self.mini_pos_combo.set(self.get_text("mini_pos_cli"))
        self.btn_copy_cc_report.config(text=self.get_text("btn_copy_cc_report"))

        # ブックマークレット セクション
        self.title_label.config(text=self.get_text("label_title"))
        self.btn_copy_title.config(text=self.get_text("btn_copy_title"))
        self.btn_copy_code.config(text=self.get_text("btn_copy_code"))

        # ChatGPT設定 セクション
        self.btn_copy_instructions.config(text=self.get_text("btn_copy_instructions"))

        # ヘルプ セクション
        self.first_run_label.config(text=self.get_text("first_run_message"))
        self.btn_readme.config(text=self.get_text("btn_readme"))

        # フッター更新
        self.ui_elements["footer_version"].config(text=self.get_text("footer_version").format(VERSION))

        # 履歴ボタン
        if hasattr(self, "history_gpt_btn"):
            self.history_gpt_btn.config(text=self.get_text("history_gpt_to_cc"))
        if hasattr(self, "history_cc_btn"):
            self.history_cc_btn.config(text=self.get_text("history_cc_to_gpt"))

        # ミニモード用ボタン
        if hasattr(self, "mini_btn"):
            self.mini_btn.config(text=self.get_text("btn_copy_cc_report"))

    def on_title_change(self, event=None):
        """タイトル変更時の処理"""
        new_title = self.title_entry.get().strip()
        if new_title and new_title != self.settings.bookmarklet_title:
            self.settings.bookmarklet_title = new_title
            self.settings.save()

    def copy_title(self):
        """タイトルをクリップボードにコピー"""
        title = self.title_entry.get().strip()
        if title:
            self.root.clipboard_clear()
            self.root.clipboard_append(title)
            self.show_notification(self.get_text("msg_copied"))

    def copy_code(self):
        """ブックマークレットコードをクリップボードにコピー"""
        code = generate_bookmarklet()
        if code:
            self.root.clipboard_clear()
            self.root.clipboard_append(code)
            self.show_notification(self.get_text("msg_copied"))
        else:
            self.show_notification(self.get_text("msg_template_not_found"))

    def copy_instructions(self):
        """カスタム指示文をクリップボードにコピー"""
        self.root.clipboard_clear()
        self.root.clipboard_append(CUSTOM_INSTRUCTIONS)
        self.show_notification(self.get_text("msg_copied"))

    def browse_project_path(self):
        """フォルダ選択ダイアログを開く"""
        from tkinter import filedialog

        # 現在の値の親フォルダを初期ディレクトリにする
        current_path = self.project_path_entry.get()
        if current_path and Path(current_path).exists():
            parent_dir = Path(current_path).parent
            initial_dir = str(parent_dir) if parent_dir.exists() else current_path
        else:
            initial_dir = "C:\\"

        folder = filedialog.askdirectory(
            initialdir=initial_dir,
            title=self.get_text("select_project_folder")
        )

        if folder:
            # パスを正規化（/ を \ に変換）
            folder = folder.replace('/', '\\')

            # 入力欄を更新
            self.project_path_entry.delete(0, tk.END)
            self.project_path_entry.insert(0, folder)

            # 設定を保存
            self.settings.project_path = folder
            self.settings.save()

    def on_project_path_change(self, event=None):
        """プロジェクトパス変更時の処理"""
        new_path = self.project_path_entry.get().strip()
        if new_path and new_path != self.settings.project_path:
            self.settings.project_path = new_path
            self.settings.save()

    def on_cc_prefix_change(self, event=None):
        """枕文変更時の処理"""
        new_prefix = self.cc_prefix_entry.get()
        # \n をエスケープ解除
        new_prefix = new_prefix.replace("\\n", "\n")
        if new_prefix != self.settings.cc_prefix:
            self.settings.cc_prefix = new_prefix
            self.settings.save()

    def copy_cc_report(self):
        """Claude Codeの完了報告をクリップボードにコピー"""
        project_path = self.project_path_entry.get().strip()

        # プロジェクトパスの検証
        if not project_path or not Path(project_path).exists():
            self.show_notification(self.get_text("msg_no_project"))
            return

        # CC報告を取得
        success, result = get_cc_report(project_path)

        if not success:
            # エラーコードに対応するメッセージを表示
            error_messages = {
                "no_log": self.get_text("msg_no_log"),
                "no_report": self.get_text("msg_no_report"),
            }
            self.show_notification(error_messages.get(result, self.get_text("msg_no_report")))
            return

        # 枕文を取得（入力欄から）
        prefix = self.cc_prefix_entry.get().replace("\\n", "\n")
        full_text = prefix + result

        # 枕文 + 報告本文をクリップボードにコピー
        self.root.clipboard_clear()
        self.root.clipboard_append(full_text)

        # 履歴に追加（プレビュー用に枕文を除去）
        self.copy_history.add("cc_to_gpt", full_text, prefix_to_remove=prefix)

        # 履歴ポップアップが開いていたらリフレッシュ
        if self.history_popup_cc and self.history_popup_cc.winfo_exists():
            self.history_popup_cc.refresh()

        # 設定を保存
        self.settings.project_path = project_path
        self.settings.cc_prefix = prefix
        self.settings.save()

        self.show_notification(self.get_text("msg_copied"))

    def open_file(self, filepath):
        """ファイルを関連付けられたエディタで開く"""
        if filepath.exists():
            os.startfile(str(filepath))
        else:
            self.show_notification(self.get_text("msg_file_not_found") + filepath.name)

    def open_readme(self):
        """言語設定に応じたReadmeをブラウザで開く"""
        # 言語に応じてファイルを選択
        if self.settings.language == 'en':
            readme_file = 'Readme_en.html'
        else:
            readme_file = 'Readme.html'

        readme_path = DOC_DIR / readme_file

        # フォールバック：指定言語のファイルがなければ日本語版
        if not readme_path.exists():
            readme_path = DOC_DIR / 'Readme.html'

        if readme_path.exists():
            webbrowser.open(str(readme_path))

            # 初回起動フラグを更新
            if self.settings.first_run == "1":
                self.settings.first_run = "0"
                self.settings.save()

                # ボタンの色を通常色に戻す
                self.btn_readme.config(
                    bg=COLORS["btn_bg"],
                    activebackground="#4a4a4a"
                )

                # 初回メッセージを非表示
                self.first_run_label.pack_forget()
        else:
            self.show_notification(self.get_text("msg_file_not_found") + readme_file)

    def show_history_popup(self, category: str):
        """履歴ポップアップを表示（トグル動作）"""

        # カテゴリに応じた参照を取得
        if category == "gpt_to_cc":
            popup_ref = self.history_popup_gpt
        else:
            popup_ref = self.history_popup_cc

        # 既に開いている場合は閉じる
        if popup_ref is not None:
            try:
                if popup_ref.winfo_exists():
                    popup_ref.destroy()
                    # 参照をクリア
                    if category == "gpt_to_cc":
                        self.history_popup_gpt = None
                    else:
                        self.history_popup_cc = None
                    return
            except:
                pass

        # 新しいポップアップを作成
        def on_select(content):
            self.root.clipboard_clear()
            self.root.clipboard_append(content)
            self.show_notification(self.get_text("copied_from_history"))

        # タイトルを言語設定に応じて変更
        if category == "gpt_to_cc":
            popup_title = self.get_text("history_title_gpt")
        else:
            popup_title = self.get_text("history_title_cc")

        popup = HistoryPopup(self.root, self.copy_history, category, on_select, self.get_text, popup_title)

        # 参照を保持
        if category == "gpt_to_cc":
            self.history_popup_gpt = popup
        else:
            self.history_popup_cc = popup

        # ウィンドウが閉じられた時に参照をクリア
        def on_popup_close():
            if category == "gpt_to_cc":
                self.history_popup_gpt = None
            else:
                self.history_popup_cc = None
            popup.destroy()

        popup.protocol("WM_DELETE_WINDOW", on_popup_close)

    def show_notification(self, message):
        """通知を表示（簡易的にタイトルバーに表示）"""
        original_title = self.root.title()
        self.root.title(message)
        self.root.after(2000, lambda: self.root.title(original_title))

    def on_mini_pos_change(self, event=None):
        """ミニウィンドウ位置設定の変更時"""
        selected = self.mini_pos_combo.get()
        if selected == self.get_text("mini_pos_last"):
            self.settings.mini_window_position = "last_position"
        else:
            self.settings.mini_window_position = "cli_bottom_left"
        self.settings.save()

    def create_mini_frame(self):
        """ミニモード用のフレームを作成"""
        self.mini_frame = tk.Frame(self.root, bg=COLORS["bg"])

        # 水平レイアウト用のフレーム
        btn_container = tk.Frame(self.mini_frame, bg=COLORS["bg"])
        btn_container.pack(fill="both", expand=True, padx=2, pady=2)

        # CC報告ボタン（左側、幅を広めに）
        self.mini_btn = tk.Button(
            btn_container,
            text=self.get_text("btn_copy_cc_report"),
            command=self.copy_cc_report,
            bg=COLORS["accent"],
            fg="white",
            font=("Arial", 9, "bold"),
            relief="flat",
            cursor="hand2",
            activebackground="#0d8a6a",
            activeforeground="white"
        )
        self.mini_btn.pack(side="left", fill="both", expand=True, padx=(2, 0), pady=2)

        # ミニモード用履歴ボタン用フレーム（縦並び）
        mini_history_frame = tk.Frame(btn_container, bg=COLORS["bg"])
        mini_history_frame.pack(side="left", fill="y", padx=(2, 0), pady=2)

        # 上：GPT→CC履歴ボタン
        self.mini_history_gpt_btn = tk.Button(
            mini_history_frame,
            text="G",
            command=lambda: self.show_history_popup("gpt_to_cc"),
            bg='#ff69b4',
            fg='white',
            font=("Arial", 8),
            relief="flat",
            cursor="hand2",
            width=2,
            height=1,
            pady=0,
            activebackground='#ff1493',
            activeforeground='white'
        )
        self.mini_history_gpt_btn.pack(side="top", fill="both", expand=True, pady=(0, 1))

        # 下：CC→GPT履歴ボタン
        self.mini_history_cc_btn = tk.Button(
            mini_history_frame,
            text="C",
            command=lambda: self.show_history_popup("cc_to_gpt"),
            bg='#9370db',
            fg='white',
            font=("Arial", 8),
            relief="flat",
            cursor="hand2",
            width=2,
            height=1,
            pady=0,
            activebackground='#7b68ee',
            activeforeground='white'
        )
        self.mini_history_cc_btn.pack(side="top", fill="both", expand=True, pady=(1, 0))

        # フルモード復帰ボタン（右側、小さめ）
        self.mini_expand_btn = tk.Button(
            btn_container,
            text="↑",
            command=self.switch_to_full_mode,
            bg="#444444",
            fg="white",
            font=("Arial", 10, "bold"),
            relief="flat",
            cursor="hand2",
            width=3,
            activebackground="#666666",
            activeforeground="white"
        )
        self.mini_expand_btn.pack(side="right", fill="y", padx=(0, 2), pady=2)

        # フレームクリックでもフルモードに戻る
        self.mini_frame.bind("<Button-1>", self.on_mini_click)
        btn_container.bind("<Button-1>", self.on_mini_click)

    def on_mini_click(self, event):
        """ミニウィンドウのフレーム部分クリック時、フルモードに戻る"""
        # ボタンクリックは無視（buttonのcommandで処理される）
        if event.widget in [self.mini_btn, self.mini_history_gpt_btn, self.mini_history_cc_btn, self.mini_expand_btn]:
            return
        print("[DEBUG] on_mini_click: switching to full mode")
        self.switch_to_full_mode()

    def is_powershell_active(self):
        """アクティブウィンドウがPowerShell（またはWindows Terminal）かどうか判定"""
        return is_cli_active()

    def _get_cli_hwnd(self):
        """CLIウィンドウ（PowerShell/Windows Terminal）のハンドルを取得"""
        hwnd = get_cli_hwnd(self.last_cli_hwnd)
        if hwnd and hwnd != self.last_cli_hwnd:
            self.last_cli_hwnd = hwnd
        return hwnd

    def set_topmost(self, enable: bool):
        """ウィンドウの常に手前表示を切り替え"""
        try:
            self.root.attributes('-topmost', enable)
            if not enable:
                # 最前面を解除した後、明示的にウィンドウを下げる
                self.root.lower()
            print(f"[DEBUG] set_topmost({enable}) via tkinter")
        except Exception as e:
            print(f"[DEBUG] set_topmost error: {e}")

    def start_main_loop(self):
        """統合メインループを開始"""
        self._main_tick()

    def _main_tick(self):
        """100ms間隔の統合ティック処理"""
        self.tick_count += 1

        # 毎回実行（100ms間隔）
        self._check_foreground_flag_task()

        # 2回に1回実行（200ms間隔）
        if self.tick_count % 2 == 0:
            self._track_cli_position_task()

        # 次のティックをスケジュール
        self.root.after(100, self._main_tick)

    def _track_cli_position_task(self):
        """CLI位置追跡（旧_track_cli_position）"""
        if not self.is_mini_mode:
            return

        try:
            cli_hwnd = self._get_cli_hwnd()
            if cli_hwnd:
                current_rect = get_window_rect(cli_hwnd)

                # 位置が変わったら追従
                if current_rect and self.last_cli_rect != current_rect:
                    self.last_cli_rect = current_rect
                    print(f"[DEBUG] CLI position changed, updating mini window position")
                    self.set_mini_position()
        except Exception as e:
            print(f"[DEBUG] CLI tracking error: {e}")

    def setup_foreground_hook(self):
        """フォアグラウンドウィンドウ変更のフックを設定"""
        # ==================================================
        # Windows固有の処理
        # 将来、他のOSに対応する場合はこのセクションを
        # OS別に分岐またはプラグイン化する
        # ==================================================

        EVENT_SYSTEM_FOREGROUND = 0x0003
        WINEVENT_OUTOFCONTEXT = 0x0000

        # フラグ初期化
        self.foreground_changed = False

        # コールバック関数の型定義
        WinEventProcType = WINFUNCTYPE(
            None,
            wintypes.HANDLE,
            wintypes.DWORD,
            wintypes.HWND,
            wintypes.LONG,
            wintypes.LONG,
            wintypes.DWORD,
            wintypes.DWORD
        )

        # コールバック関数（フラグを立てるだけ、tkinter操作は一切しない）
        def win_event_callback(hWinEventHook, event, hwnd, idObject, idChild, dwEventThread, dwmsEventTime):
            self.foreground_changed = True  # フラグを立てるだけ

        # コールバックを保持（ガベージコレクション防止）
        self.win_event_callback = WinEventProcType(win_event_callback)

        user32 = ctypes.windll.user32
        self.hook = user32.SetWinEventHook(
            EVENT_SYSTEM_FOREGROUND,
            EVENT_SYSTEM_FOREGROUND,
            0,
            self.win_event_callback,
            0,
            0,
            WINEVENT_OUTOFCONTEXT
        )

        if self.hook:
            print("[DEBUG] Windows Hook installed successfully")
        else:
            print("[DEBUG] Failed to install Windows Hook")

    def _check_foreground_flag_task(self):
        """フォアグラウンドフラグチェック（旧check_foreground_flag）"""
        try:
            if self.foreground_changed:
                self.foreground_changed = False  # フラグをクリア
                self.on_foreground_changed()     # 実際の処理（メインスレッドで安全に実行）
        except Exception as e:
            print(f"[DEBUG] Error in _check_foreground_flag_task: {e}")

    def on_foreground_changed(self):
        """フォアグラウンドウィンドウが変更された時の処理"""
        try:
            is_ps_active = self.is_powershell_active()
            is_self_active = self.is_self_active()

            print(f"[DEBUG] on_foreground_changed: is_ps_active={is_ps_active}, is_self_active={is_self_active}, is_mini_mode={self.is_mini_mode}")

            # 自分自身がアクティブな場合は何もしない（ボタンクリック時など）
            if is_self_active:
                print("[DEBUG] Self is active, skipping")
                return

            if is_ps_active:
                # CLIがアクティブ → ミニモード、常に手前ON
                if not self.is_mini_mode:
                    print("[DEBUG] PowerShell is active, switching to mini mode")
                    self.switch_to_mini_mode()
                self.set_topmost(True)
                print("[DEBUG] set_topmost(True) called for CLI active")
            else:
                # その他のアプリがアクティブ → 常に手前OFF
                self.set_topmost(False)
        except Exception as e:
            print(f"[DEBUG] Error in on_foreground_changed: {e}")

    def is_self_active(self):
        """自分自身（Bridgiron）がアクティブかどうかを判定"""
        try:
            foreground = get_foreground_window()

            # 方法1: hwnd直接比較
            my_hwnd = self.root.winfo_id()
            if foreground == my_hwnd:
                return True

            # 方法2: 親ウィンドウを取得して比較
            parent = get_window_parent(my_hwnd)
            if parent and foreground == parent:
                return True

            # 方法3: プロセスIDで比較（同じプロセスなら自分自身）
            return is_process_active(os.getpid())

        except Exception as e:
            print(f"[DEBUG] Error in is_self_active: {e}")
            return False

    def cleanup_hook(self):
        """フックを解除"""
        if self.hook:
            user32 = ctypes.windll.user32
            user32.UnhookWinEvent(self.hook)
            self.hook = None
            print("[DEBUG] Windows Hook uninstalled")

    def on_closing(self):
        """ウィンドウを閉じる時の処理"""
        self.clipboard_watcher.stop()
        self.cleanup_hook()
        self.root.destroy()

    def _on_gpt_prompt_detected(self, content: str):
        """GPT→CCプロンプトを検知した時のコールバック"""
        self.copy_history.add("gpt_to_cc", content)

        # 履歴ポップアップが開いていたらリフレッシュ
        if self.history_popup_gpt and self.history_popup_gpt.winfo_exists():
            self.history_popup_gpt.refresh()

    def switch_to_mini_mode(self):
        """ミニモードに切り替え"""
        if self.is_mini_mode:
            return

        print("[DEBUG] switch_to_mini_mode called")
        self.is_mini_mode = True

        # 現在のジオメトリを保存
        self.last_full_geometry = self.root.geometry()

        # 現在の位置を保存（last_position用）
        self.last_mini_position = (self.root.winfo_x(), self.root.winfo_y())

        # 言語選択バーを非表示
        for widget in self.root.winfo_children():
            if widget != self.mini_frame:
                widget.pack_forget()

        # ミニフレームを表示
        self.mini_frame.pack(fill="both", expand=True)

        # 位置とサイズを設定（set_topmostはon_foreground_changed側で呼ばれる）
        self.set_mini_position()

    def switch_to_full_mode(self):
        """フルモードに戻る"""
        if not self.is_mini_mode:
            return
        print("[DEBUG] switch_to_full_mode called")

        self.is_mini_mode = False

        # 最前面解除（lower()は呼ばない）
        self.root.attributes('-topmost', False)

        # ミニフレーム非表示
        self.mini_frame.pack_forget()

        # サイズ制限解除
        if self.settings.first_run == "1":
            self.root.minsize(500, 620)
        else:
            self.root.minsize(500, 570)
        self.root.maxsize(0, 0)

        # 言語選択バーを再表示
        self.create_language_bar()

        # メインフレームを再表示
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # ウィンドウサイズ復元
        if hasattr(self, "last_full_geometry"):
            self.root.geometry(self.last_full_geometry)
        else:
            if self.settings.first_run == "1":
                self.root.geometry("600x690")
            else:
                self.root.geometry("600x640")

        # ウィンドウを前面に持ってくる
        self.root.lift()
        self.root.focus_force()

        print("[DEBUG] switch_to_full_mode completed")

    def set_mini_position(self):
        """ミニウィンドウの位置を設定（マルチモニター対応）"""
        print("[DEBUG] set_mini_position called")

        mini_width, mini_height = 220, 60

        if self.settings.mini_window_position == "last_position" and self.last_mini_position:
            x, y = self.last_mini_position
            print(f"[DEBUG] set_mini_position: using last_position x={x}, y={y}")
        else:
            x, y = self._calc_mini_position_from_cli(mini_width, mini_height)

        # ミニサイズを固定
        self.root.minsize(mini_width, mini_height)
        self.root.maxsize(mini_width, mini_height)
        self.root.geometry(f"{mini_width}x{mini_height}+{x}+{y}")

        # last_position 用に保存
        self.last_mini_position = (x, y)

    def _calc_mini_position_from_cli(self, mini_width, mini_height):
        """CLI位置からミニウィンドウの座標を計算"""
        try:
            # アクティブウィンドウ（CLI）の情報を取得
            hwnd = get_foreground_window()
            cli_rect = get_window_rect(hwnd)

            if not cli_rect:
                raise Exception("Could not get window rect")

            cli_left, cli_top, cli_right, cli_bottom = cli_rect
            cli_width = cli_right - cli_left
            cli_height = cli_bottom - cli_top

            print(f"[DEBUG] _calc_mini_position: cli_rect=({cli_left},{cli_top},{cli_right},{cli_bottom})")
            print(f"[DEBUG] _calc_mini_position: cli_size={cli_width}x{cli_height}")

            # CLIウィンドウがあるモニターの情報を取得
            work_area = get_monitor_work_area(hwnd)

            if not work_area:
                raise Exception("Could not get monitor work area")

            work_left, work_top, work_right, work_bottom = work_area

            print(f"[DEBUG] _calc_mini_position: monitor_work=({work_left},{work_top},{work_right},{work_bottom})")

            # 最大化判定（Windows API 使用）
            is_maximized = is_window_maximized(hwnd)

            print(f"[DEBUG] _calc_mini_position: is_maximized={is_maximized}")

            if is_maximized:
                # 最大化時: モニターの右下（作業領域内）
                margin = 50
                x = work_right - mini_width - margin
                y = work_bottom - mini_height - margin
            else:
                # 通常時: CLIウィンドウの左下（外側）
                margin = 10
                x = cli_left
                y = cli_bottom + margin

                # 画面外にはみ出す場合は調整
                if y + mini_height > work_bottom:
                    y = work_bottom - mini_height - margin
                if x < work_left:
                    x = work_left + margin
                if x + mini_width > work_right:
                    x = work_right - mini_width - margin

            print(f"[DEBUG] _calc_mini_position: final x={x}, y={y}")
            return (x, y)

        except Exception as e:
            print(f"[DEBUG] _calc_mini_position exception: {e}")
            return self._get_default_mini_position(mini_height)

    def _get_default_mini_position(self, mini_height):
        """エラー時のデフォルト位置を返す（メインディスプレイ左下）"""
        x = 10
        y = self.root.winfo_screenheight() - mini_height - 60
        return (x, y)

# ========================================
# メイン
# ========================================

def main():
    root = tk.Tk()

    # ウィンドウアイコンを設定
    try:
        icon_path_ico = PROJECT_ROOT / "images" / "Icon05.ico"
        if icon_path_ico.exists():
            root.iconbitmap(str(icon_path_ico))
    except Exception as e:
        print(f"[DEBUG] Failed to set window icon: {e}")

    app = BridgironApp(root)

    # Windows タイトルバーのダークモード対応
    root.update()
    try:
        import ctypes
        hwnd = ctypes.windll.user32.GetParent(root.winfo_id())
        DWMWA_USE_IMMERSIVE_DARK_MODE = 20
        value = ctypes.c_int(2)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd,
            DWMWA_USE_IMMERSIVE_DARK_MODE,
            ctypes.byref(value),
            ctypes.sizeof(value)
        )
    except Exception:
        pass  # Windows以外または古いWindowsでは無視

    # GUI準備完了後にWindows Hookを設定
    app.setup_foreground_hook()

    root.mainloop()

if __name__ == "__main__":
    main()
