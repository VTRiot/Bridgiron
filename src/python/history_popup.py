# -*- coding: utf-8 -*-
"""
Bridgiron - 履歴ポップアップUI
"""

import sys
import tkinter as tk
from datetime import datetime
from pathlib import Path

# プロジェクトルート（アイコンパス用）
if getattr(sys, 'frozen', False):
    SCRIPT_DIR = Path(sys.executable).resolve().parent
    PROJECT_ROOT = SCRIPT_DIR
else:
    SCRIPT_DIR = Path(__file__).resolve().parent
    PROJECT_ROOT = SCRIPT_DIR.parent.parent


class HistoryPopup(tk.Toplevel):
    def __init__(self, parent, history, category: str, on_select_callback, get_text_func, popup_title: str):
        super().__init__(parent)
        self.history = history
        self.category = category
        self.on_select = on_select_callback
        self.get_text = get_text_func

        # アイコン設定
        try:
            icon_path = PROJECT_ROOT / 'images' / 'Icon05.ico'
            if icon_path.exists():
                self.iconbitmap(str(icon_path))
        except:
            pass  # アイコン設定失敗は無視

        # ウィンドウ設定
        self.title(popup_title)
        self.configure(bg='#2d2d2d')
        self.geometry("400x300")
        self.resizable(False, False)

        # リストフレーム
        self.list_frame = tk.Frame(self, bg='#2d2d2d')
        self.list_frame.pack(fill='both', expand=True, padx=10, pady=10)

        # スクロール可能なリスト
        self.canvas = tk.Canvas(self.list_frame, bg='#2d2d2d', highlightthickness=0)
        self.scrollbar = tk.Scrollbar(self.list_frame, orient='vertical', command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg='#2d2d2d')

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor='nw')
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        # Canvasの幅をフレームに合わせる
        self.canvas.bind('<Configure>', self._on_canvas_configure)

        # スクロールバーを右側に配置（先にpack）
        self.scrollbar.pack(side='right', fill='y')
        self.canvas.pack(side='left', fill='both', expand=True)

        # マウスホイールでスクロール（bind_allでグローバルに）
        self.canvas.bind_all('<MouseWheel>', self._on_mousewheel)
        # Linux用
        self.canvas.bind_all('<Button-4>', self._on_mousewheel_linux)
        self.canvas.bind_all('<Button-5>', self._on_mousewheel_linux)

        # 履歴アイテムを表示
        self._populate_list()

        # キーバインド
        self.bind('<Key>', self._on_key)
        self.bind('<Escape>', lambda e: self.destroy())

        # フォーカス
        self.focus_set()

    def _on_canvas_configure(self, event):
        """Canvasのリサイズ時にスクロール領域の幅を調整"""
        self.canvas.itemconfig(self.canvas_window, width=event.width)

    def _on_mousewheel(self, event):
        """マウスホイールでスクロール（Windows）"""
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _on_mousewheel_linux(self, event):
        """マウスホイールでスクロール（Linux）"""
        if event.num == 4:
            self.canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self.canvas.yview_scroll(1, "units")

    def destroy(self):
        """ウィンドウ破棄時にマウスホイールバインドを解除"""
        try:
            self.canvas.unbind_all('<MouseWheel>')
            self.canvas.unbind_all('<Button-4>')
            self.canvas.unbind_all('<Button-5>')
        except:
            pass
        super().destroy()

    def _populate_list(self):
        """履歴リストを表示"""
        items = self.history.get_list(self.category)

        if not items:
            label = tk.Label(
                self.scrollable_frame,
                text=self.get_text("no_history"),
                bg='#2d2d2d',
                fg='#888888',
                font=('Arial', 12)
            )
            label.pack(pady=20)
            return

        for i, item in enumerate(items[:50]):  # 最大50件表示
            frame = tk.Frame(self.scrollable_frame, bg='#3c3c3c')
            frame.pack(fill='x', pady=2)

            # 削除ボタン（固定幅要素を先にpack）
            del_btn = tk.Button(
                frame,
                text='x',
                command=lambda idx=i: self._delete_item(idx),
                bg='#3c3c3c',
                fg='#ff6b6b',
                relief='flat',
                font=('Arial', 10),
                cursor='hand2'
            )
            del_btn.pack(side='right')

            # 日時（固定幅要素）
            dt = datetime.fromisoformat(item["timestamp"])
            time_str = dt.strftime("%m/%d %H:%M")
            time_label = tk.Label(
                frame,
                text=time_str,
                bg='#3c3c3c',
                fg='#888888',
                font=('Arial', 9)
            )
            time_label.pack(side='right', padx=5)

            # プレビュー（可変幅要素を最後にpack）
            preview_label = tk.Label(
                frame,
                text=item["preview"],
                bg='#3c3c3c',
                fg='white',
                font=('Arial', 10),
                anchor='w'
            )
            preview_label.pack(side='left', fill='x', expand=True, padx=(10, 5))

            # クリックで選択
            for widget in [frame, preview_label, time_label]:
                widget.bind('<Button-1>', lambda e, idx=i: self._select_item(idx))
                widget.configure(cursor='hand2')

    def _select_item(self, index: int):
        """アイテムを選択してコピー"""
        content = self.history.get_content(self.category, index)
        if content:
            self.on_select(content)
        self.destroy()

    def _delete_item(self, index: int):
        """アイテムを削除"""
        self.history.delete(self.category, index)
        self.refresh()

    def refresh(self):
        """履歴リストを再読み込み"""
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        self._populate_list()

    def _on_key(self, event):
        """キーボードショートカット"""
        if event.char.isdigit() and event.char != '0':
            index = int(event.char) - 1
            items = self.history.get_list(self.category)
            if index < len(items):
                self._select_item(index)
