# -*- coding: utf-8 -*-
"""
Bridgiron - Claude Code 報告抽出
"""

import os
import json
from pathlib import Path


def get_log_dir(project_path):
    """
    プロジェクトパスからログディレクトリを取得

    Args:
        project_path: プロジェクトパス

    Returns:
        Path: ログディレクトリ（存在しない場合は None）
    """
    if not project_path:
        return None

    user_profile = os.environ.get("USERPROFILE", "")
    if not user_profile:
        return None

    path_normalized = project_path.replace("/", "\\").rstrip("\\")
    path_hash = path_normalized.replace(":", "-").replace("\\", "-").replace("/", "-").replace("_", "-")

    log_dir = Path(user_profile) / ".claude" / "projects" / path_hash

    if not log_dir.exists():
        return None

    return log_dir


def find_session_logs_by_mtime(log_dir):
    """
    ログディレクトリから .jsonl ファイルを mtime 順（降順）で取得

    Args:
        log_dir: ログディレクトリのパス

    Returns:
        list[Path]: .jsonl ファイルのリスト（新しい順）
    """
    if not log_dir or not log_dir.exists():
        return []

    jsonl_files = list(log_dir.glob("*.jsonl"))
    if not jsonl_files:
        return []

    # 更新日時で降順ソート
    return sorted(jsonl_files, key=lambda f: f.stat().st_mtime, reverse=True)


def extract_latest_assistant_message(jsonl_path):
    """
    JSONL ログファイルから assistant の最新メッセージを抽出

    Args:
        jsonl_path: .jsonl ファイルのパス

    Returns:
        str: assistant の最新メッセージ（見つからない場合は None）
    """
    if not jsonl_path or not jsonl_path.exists():
        return None

    try:
        with open(jsonl_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # 末尾から逆順に検索
        for line in reversed(lines):
            line = line.strip()
            if not line:
                continue

            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue

            if entry.get("type") == "assistant":
                message = entry.get("message", {})
                content = message.get("content", [])

                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        text = item.get("text", "")
                        if text:
                            return text  # 最新の text をそのまま返す

        return None

    except Exception:
        return None


def format_report_text(raw_text):
    """
    報告テキストを整形（現在は何もしない、将来の拡張用）

    Args:
        raw_text: 生のテキスト

    Returns:
        str: 整形後のテキスト
    """
    # 現在は整形処理なし（そのまま返す）
    return raw_text


def get_cc_report(project_path):
    """
    CC報告を取得するメイン関数

    Args:
        project_path: プロジェクトのパス

    Returns:
        tuple: (成功フラグ, メッセージまたはエラーコード)
            成功時: (True, 報告テキスト)
            失敗時: (False, エラーコード)
            エラーコード: "no_project", "no_log", "no_report"
    """
    # 1. ログディレクトリ取得
    log_dir = get_log_dir(project_path)
    if not log_dir:
        return (False, "no_log")

    # 2. mtime 順に .jsonl ファイルを取得
    jsonl_files = find_session_logs_by_mtime(log_dir)
    if not jsonl_files:
        return (False, "no_log")

    # 3. 順番に試して、text が取れたら返す
    for jsonl_file in jsonl_files:
        message = extract_latest_assistant_message(jsonl_file)
        if message:
            formatted = format_report_text(message)
            return (True, formatted)

    return (False, "no_report")
