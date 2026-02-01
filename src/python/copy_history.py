# -*- coding: utf-8 -*-
"""
Bridgiron - コピー履歴管理
"""

import json
import threading
import time
from datetime import datetime
from pathlib import Path
import pyperclip


class CopyHistory:
    MAX_ENTRIES = 50
    PREVIEW_LENGTH = 30

    def __init__(self, history_file: Path):
        self.history_file = history_file
        self.data = self._load()

    def _load(self):
        """履歴ファイルを読み込み"""
        if self.history_file.exists():
            try:
                with open(self.history_file, 'r', encoding='utf-8-sig') as f:
                    return json.load(f)
            except:
                pass
        return {"gpt_to_cc": [], "cc_to_gpt": []}

    def _save(self):
        """履歴ファイルを保存"""
        with open(self.history_file, 'w', encoding='utf-8-sig') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def _make_preview(self, content: str) -> str:
        """プレビュー文字列を生成"""
        preview = content.replace('\n', ' ').replace('\r', '')
        return preview[:self.PREVIEW_LENGTH]

    def add(self, category: str, content: str, prefix_to_remove: str = ""):
        """履歴を追加

        Args:
            category: 'gpt_to_cc' or 'cc_to_gpt'
            content: コピーする全文
            prefix_to_remove: プレビューから除去する枕文（オプション）
        """
        # プレビュー用のコンテンツ（枕文を除去）
        preview_content = content
        if prefix_to_remove and content.startswith(prefix_to_remove):
            preview_content = content[len(prefix_to_remove):].lstrip('\r\n')

        entry = {
            "timestamp": datetime.now().isoformat(),
            "preview": self._make_preview(preview_content),
            "content": content  # 全文は枕文込みで保存
        }
        self.data[category].insert(0, entry)
        if len(self.data[category]) > self.MAX_ENTRIES:
            self.data[category] = self.data[category][:self.MAX_ENTRIES]
        self._save()

    def get_list(self, category: str) -> list:
        """プレビューリストを取得"""
        return [
            {
                "index": i,
                "timestamp": entry["timestamp"],
                "preview": entry["preview"]
            }
            for i, entry in enumerate(self.data[category])
        ]

    def get_content(self, category: str, index: int) -> str:
        """指定インデックスの全文を取得"""
        if 0 <= index < len(self.data[category]):
            return self.data[category][index]["content"]
        return ""

    def delete(self, category: str, index: int):
        """指定インデックスの履歴を削除"""
        if 0 <= index < len(self.data[category]):
            del self.data[category][index]
            self._save()


class ClipboardWatcher:
    """クリップボードを監視し、識別子パターンを検知"""

    IDENTIFIER = '[BRIDGIRON_GPT2CC]'  # 改行なしで定義

    def __init__(self, on_detect_callback, interval=1.0):
        self.on_detect = on_detect_callback
        self.interval = interval
        self.running = False
        self.thread = None
        self.last_content = ""

    def start(self):
        """監視開始"""
        if self.running:
            return
        self.running = True
        try:
            self.last_content = pyperclip.paste()
        except:
            self.last_content = ""
        self.thread = threading.Thread(target=self._watch_loop, daemon=True)
        self.thread.start()
        print("[DEBUG] ClipboardWatcher started")

    def stop(self):
        """監視停止"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)
        print("[DEBUG] ClipboardWatcher stopped")

    def _watch_loop(self):
        """監視ループ"""
        while self.running:
            try:
                current = pyperclip.paste()
                # 内容が変わったかチェック
                if current != self.last_content:
                    print(f"[DEBUG] Clipboard changed, length={len(current)}")
                    print(f"[DEBUG] Starts with identifier: {current.startswith(self.IDENTIFIER)}")

                    if current.startswith(self.IDENTIFIER):
                        # 識別子の後の改行もスキップ
                        content = current[len(self.IDENTIFIER):].lstrip('\r\n')
                        print(f"[DEBUG] Extracted content length: {len(content)}")
                        if content:
                            # 履歴に追加
                            self.on_detect(content)
                            print("[DEBUG] Added to history")
                            # 識別子なしで再コピー（実際に使う時用）
                            pyperclip.copy(content)
                            print("[DEBUG] Re-copied without identifier")
                    self.last_content = pyperclip.paste()
            except Exception as e:
                print(f"[DEBUG] ClipboardWatcher error: {e}")
            time.sleep(self.interval)
