# -*- coding: utf-8 -*-
"""
Bridgiron - Windows API 操作
"""

import ctypes
from ctypes import wintypes

# Windows API 定数
PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010
MONITOR_DEFAULTTONEAREST = 2

# CLI対象プロセス
CLI_PROCESS_NAMES = ["powershell.exe", "pwsh.exe", "windowsterminal.exe"]

# Windows API モジュール
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
psapi = ctypes.windll.psapi


class MONITORINFO(ctypes.Structure):
    """モニター情報構造体"""
    _fields_ = [
        ("cbSize", ctypes.c_ulong),
        ("rcMonitor", wintypes.RECT),
        ("rcWork", wintypes.RECT),
        ("dwFlags", ctypes.c_ulong)
    ]


def get_foreground_window():
    """フォアグラウンドウィンドウのハンドルを取得"""
    return user32.GetForegroundWindow()


def get_window_process_name(hwnd):
    """
    ウィンドウハンドルからプロセス名を取得

    Args:
        hwnd: ウィンドウハンドル

    Returns:
        str: プロセス名（小文字）、取得失敗時はNone
    """
    try:
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))

        process = kernel32.OpenProcess(
            PROCESS_QUERY_INFORMATION | PROCESS_VM_READ,
            False,
            pid.value
        )

        if process:
            exe_name = (ctypes.c_char * 260)()
            psapi.GetModuleBaseNameA(process, None, exe_name, 260)
            kernel32.CloseHandle(process)
            return exe_name.value.decode("utf-8", errors="ignore").lower()

        return None
    except Exception:
        return None


def is_cli_active():
    """
    PowerShell または Windows Terminal がアクティブか判定

    Returns:
        bool: CLI がアクティブなら True
    """
    try:
        hwnd = get_foreground_window()
        process_name = get_window_process_name(hwnd)

        if process_name:
            result = process_name in CLI_PROCESS_NAMES
            print(f"[DEBUG] is_cli_active: process_name={process_name}, result={result}")
            return result

        print("[DEBUG] is_cli_active: could not get process name")
        return False
    except Exception as e:
        print(f"[DEBUG] is_cli_active exception: {e}")
        return False


def get_cli_hwnd(last_hwnd=None):
    """
    アクティブな CLI ウィンドウのハンドルを取得

    Args:
        last_hwnd: 前回取得したCLIハンドル（フォールバック用）

    Returns:
        int: CLI ウィンドウハンドル、見つからなければ None
    """
    try:
        hwnd = get_foreground_window()
        process_name = get_window_process_name(hwnd)

        if process_name and process_name in CLI_PROCESS_NAMES:
            return hwnd

        # フォアグラウンドがCLIでなくても、前回のCLIハンドルがあればそれを返す
        if last_hwnd and is_window_valid(last_hwnd):
            return last_hwnd

        return None
    except Exception as e:
        print(f"[DEBUG] get_cli_hwnd exception: {e}")
        return None


def is_window_valid(hwnd):
    """ウィンドウハンドルが有効か確認"""
    return bool(user32.IsWindow(hwnd))


def is_process_active(pid):
    """
    指定したプロセスIDがフォアグラウンドか判定

    Args:
        pid: プロセスID

    Returns:
        bool: 指定PIDがフォアグラウンドなら True
    """
    try:
        foreground = get_foreground_window()
        foreground_pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(foreground, ctypes.byref(foreground_pid))

        result = foreground_pid.value == pid
        if result:
            print(f"[DEBUG] is_process_active: True (PID: {pid})")
        return result
    except Exception as e:
        print(f"[DEBUG] is_process_active exception: {e}")
        return False


def get_window_rect(hwnd):
    """
    ウィンドウの位置とサイズを取得

    Args:
        hwnd: ウィンドウハンドル

    Returns:
        tuple: (left, top, right, bottom) または None
    """
    try:
        rect = wintypes.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(rect))
        return (rect.left, rect.top, rect.right, rect.bottom)
    except Exception:
        return None


def get_monitor_work_area(hwnd):
    """
    ウィンドウが存在するモニターの作業領域を取得

    Args:
        hwnd: ウィンドウハンドル

    Returns:
        tuple: (left, top, right, bottom) または None
    """
    try:
        hmonitor = user32.MonitorFromWindow(hwnd, MONITOR_DEFAULTTONEAREST)

        monitor_info = MONITORINFO()
        monitor_info.cbSize = ctypes.sizeof(MONITORINFO)
        user32.GetMonitorInfoW(hmonitor, ctypes.byref(monitor_info))

        work = monitor_info.rcWork
        return (work.left, work.top, work.right, work.bottom)
    except Exception:
        return None


def is_window_maximized(hwnd):
    """
    ウィンドウが最大化されているか判定

    Args:
        hwnd: ウィンドウハンドル

    Returns:
        bool: 最大化されていれば True
    """
    try:
        return bool(user32.IsZoomed(hwnd))
    except Exception:
        return False


def get_window_parent(hwnd):
    """親ウィンドウのハンドルを取得"""
    try:
        return user32.GetParent(hwnd)
    except Exception:
        return None
