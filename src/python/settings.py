# -*- coding: utf-8 -*-
"""
Bridgiron - 設定管理
"""

import os
import sys
from pathlib import Path
from io_utils import read_file_with_encoding

# プロジェクトルート（EXE実行時とスクリプト実行時で分岐）
if getattr(sys, 'frozen', False):
    SCRIPT_DIR = Path(sys.executable).resolve().parent
    PROJECT_ROOT = SCRIPT_DIR
else:
    SCRIPT_DIR = Path(__file__).resolve().parent
    PROJECT_ROOT = SCRIPT_DIR.parent.parent

# 設定ファイルの保存先（AppData）
def get_settings_dir():
    """設定ファイルの保存ディレクトリを取得"""
    if os.name == 'nt':  # Windows
        appdata = os.environ.get('APPDATA', '')
        if appdata:
            settings_dir = Path(appdata) / 'Bridgiron'
        else:
            settings_dir = PROJECT_ROOT / '_Config'
    else:
        settings_dir = PROJECT_ROOT / '_Config'

    settings_dir.mkdir(parents=True, exist_ok=True)
    return settings_dir

SETTINGS_DIR = get_settings_dir()
SETTINGS_FILE = SETTINGS_DIR / 'settings.txt'

# サポートされる言語
SUPPORTED_LANGUAGES = ["ja", "en"]

# デフォルト値
DEFAULT_CC_PREFIX = "Claude Codeの報告は下記。\n"


class Settings:
    def __init__(self):
        self.language = "ja"
        self.bookmarklet_title = "CopyPrompt GPT2CC"
        self.project_path = str(PROJECT_ROOT)
        self.cc_prefix = DEFAULT_CC_PREFIX
        self.mini_window_position = "cli_bottom_left"
        self.first_run = "1"
        self.debug_mode = "0"  # 隠し機能: F_DebugMode=1 でコンソール表示
        self.load()

    def load(self):
        """設定ファイルを読み込む"""
        print(f"[DEBUG] Settings.load() called")
        print(f"[DEBUG] Settings file path: {SETTINGS_FILE}")
        print(f"[DEBUG] Settings file exists: {SETTINGS_FILE.exists()}")

        if not SETTINGS_FILE.exists():
            print(f"[DEBUG] Settings file does not exist")
            return

        try:
            # UTF-8 で読み込み、失敗したら他のエンコーディングを試す
            content = read_file_with_encoding(SETTINGS_FILE)

            if content is None:
                print(f"[DEBUG] Could not read settings file with any encoding")
                return

            print(f"[DEBUG] Successfully read settings file")

            # パース処理
            for line in content.splitlines():
                line = line.strip()
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    print(f"[DEBUG] Parsed: {key}={value}")

                    if key == 'language':
                        self.language = value if value in SUPPORTED_LANGUAGES else "ja"
                    elif key == 'bookmarklet_title':
                        self.bookmarklet_title = value
                    elif key == 'project_path':
                        if value:  # 空でない場合のみ
                            self.project_path = value
                    elif key == 'cc_prefix':
                        self.cc_prefix = value.replace('\\n', '\n')
                    elif key == 'mini_window_position':
                        self.mini_window_position = value
                    elif key == 'first_run':
                        self.first_run = value
                    elif key == 'F_DebugMode':
                        self.debug_mode = value

            print(f"[DEBUG] Loaded project_path: {self.project_path}")
            print(f"[DEBUG] Loaded debug_mode: {self.debug_mode}")

        except Exception as e:
            print(f"[DEBUG] Exception in Settings.load(): {e}")
            import traceback
            traceback.print_exc()

    def save(self):
        """設定ファイルを保存する（UTF-8 BOM付き）"""
        try:
            SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
            with open(SETTINGS_FILE, 'w', encoding='utf-8-sig') as f:
                f.write(f"language={self.language}\n")
                f.write(f"bookmarklet_title={self.bookmarklet_title}\n")
                f.write(f"project_path={self.project_path}\n")
                # \n をエスケープして保存
                f.write(f"cc_prefix={self.cc_prefix.replace(chr(10), '\\n')}\n")
                f.write(f"mini_window_position={self.mini_window_position}\n")
                f.write(f"first_run={self.first_run}\n")
        except Exception as e:
            print(f"[DEBUG] Failed to save settings: {e}")
