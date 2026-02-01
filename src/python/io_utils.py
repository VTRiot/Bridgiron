# -*- coding: utf-8 -*-
"""
Bridgiron - ファイルIO共通処理
"""

def read_file_with_encoding(filepath, encodings=None):
    """
    複数エンコーディングを試してファイルを読む

    Args:
        filepath: ファイルパス
        encodings: 試すエンコーディングのリスト（デフォルト: utf-8, utf-8-sig, cp932）

    Returns:
        str: ファイル内容（読み込み成功時）
        None: 読み込み失敗時
    """
    if encodings is None:
        encodings = ['utf-8-sig', 'utf-8', 'cp932']

    for enc in encodings:
        try:
            with open(filepath, 'r', encoding=enc) as f:
                return f.read()
        except (UnicodeDecodeError, UnicodeError):
            continue
        except FileNotFoundError:
            return None
        except Exception:
            continue
    return None


def read_file_lines_with_encoding(filepath, encodings=None):
    """
    複数エンコーディングを試してファイルを行リストで読む

    Args:
        filepath: ファイルパス
        encodings: 試すエンコーディングのリスト

    Returns:
        list: 行のリスト（読み込み成功時）
        None: 読み込み失敗時
    """
    content = read_file_with_encoding(filepath, encodings)
    if content is None:
        return None
    return content.splitlines()
