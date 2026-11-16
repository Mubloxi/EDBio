"""Foreground-only Elite Dangerous bio-signal overlay."""

import ctypes
import os
import sys
from ctypes import wintypes

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget


_GAME_EXECUTABLES = {"elitedangerous64.exe", "elitedangerous.exe"}
_PROCESS_QUERY_LIMITED_INFORMATION = 0x1000


def foreground_game_rect():
    """Return the Elite Dangerous foreground window rectangle, or None."""
    if sys.platform != "win32":
        return None

    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    user32.GetForegroundWindow.restype = wintypes.HWND
    user32.GetWindowThreadProcessId.argtypes = [
        wintypes.HWND, ctypes.POINTER(wintypes.DWORD)
    ]
    user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    kernel32.OpenProcess.argtypes = [
        wintypes.DWORD, wintypes.BOOL, wintypes.DWORD
    ]
    kernel32.QueryFullProcessImageNameW.argtypes = [
        wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR,
        ctypes.POINTER(wintypes.DWORD),
    ]
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return None

    process_id = wintypes.DWORD()
    if not user32.GetWindowThreadProcessId(hwnd, ctypes.byref(process_id)):
        return None

    kernel32.OpenProcess.restype = wintypes.HANDLE
    handle = kernel32.OpenProcess(
        _PROCESS_QUERY_LIMITED_INFORMATION, False, process_id.value
    )
    if not handle:
        return None

    try:
        image_path = ctypes.create_unicode_buffer(32768)
        path_length = wintypes.DWORD(len(image_path))
        if not kernel32.QueryFullProcessImageNameW(
            handle, 0, image_path, ctypes.byref(path_length)
        ):
            return None
        if os.path.basename(image_path.value).casefold() not in _GAME_EXECUTABLES:
            return None
    finally:
        kernel32.CloseHandle(handle)

    rect = wintypes.RECT()
    if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        return None
    return rect.left, rect.top, rect.right, rect.bottom


class BioOverlay(QWidget):
    def __init__(self, enabled=False, parent=None):
        flags = (
            Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
            | Qt.WindowTransparentForInput | Qt.WindowDoesNotAcceptFocus
        )
        super().__init__(parent, flags)
        self._enabled = False
        self._body = ""
        self._signal_count = 0
        self._genera = []

        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setFocusPolicy(Qt.NoFocus)
        self.setFixedSize(560, 118)

        surface = QFrame(self)
        surface.setObjectName("overlaySurface")
        surface.setStyleSheet(
            "QFrame#overlaySurface {"
            "background-color: rgba(28, 30, 32, 238);"
            "border: 1px solid #ff9900;"
            "}"
            "QLabel#overlayTitle { color: #ff9900; font-size: 18px; font-weight: bold; }"
            "QLabel#overlayDetail { color: #ffffff; font-size: 13px; }"
        )
        layout = QVBoxLayout(surface)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(4)

        self.title = QLabel("BIOLOGICAL SIGNALS DETECTED")
        self.title.setObjectName("overlayTitle")
        self.detail = QLabel()
        self.detail.setObjectName("overlayDetail")
        self.detail.setWordWrap(True)
        layout.addWidget(self.title)
        layout.addWidget(self.detail)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(surface)

        self._timer = QTimer(self)
        self._timer.setInterval(300)
        self._timer.timeout.connect(self._update_visibility)
        self.set_enabled(enabled)

    def set_enabled(self, enabled):
        self._enabled = bool(enabled)
        if self._enabled:
            self._timer.start()
            self._update_visibility()
        else:
            self._timer.stop()
            self.hide()

    def show_detection(self, body, signal_count, genera=None):
        self._body = body or "Unknown body"
        self._signal_count = signal_count
        self._genera = list(genera or [])
        self.detail.setText(self._detail_text())
        self._update_visibility()

    def _detail_text(self):
        body_line = f"{self._body}  |  {self._signal_count} biological signal(s)"
        if self._genera:
            return f"{body_line}\nDetected genera: {', '.join(self._genera)}"
        return f"{body_line}\nUse the Detailed Surface Scanner to identify genera."

    def _update_visibility(self):
        rect = foreground_game_rect() if self._enabled else None
        if rect is None or not self._body:
            self.hide()
            return

        left, top, right, _ = rect
        x = left + max(0, (right - left - self.width()) // 2)
        self.move(x, top + 24)
        self.show()
        self.raise_()
