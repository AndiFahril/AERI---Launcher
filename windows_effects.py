from __future__ import annotations
import ctypes
from ctypes import wintypes
import sys
ACRYLIC_TINT = (20, 22, 24)
ACRYLIC_OPACITY = 20

def enable_windows_acrylic(hwnd: int, tint=ACRYLIC_TINT, opacity=ACRYLIC_OPACITY) -> bool:
    """Acrylic best-effort; mengembalikan False jika Windows menolak."""
    if sys.platform != "win32":
        return False
    try:
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        dwm = ctypes.WinDLL('dwmapi', use_last_error=True)

        class Blur(ctypes.Structure):
            _fields_ = [('flags', wintypes.DWORD), ('enable', wintypes.BOOL),
                        ('region', wintypes.HRGN), ('transition', wintypes.BOOL)]

        class Margins(ctypes.Structure):
            _fields_ = [('left', ctypes.c_int), ('right', ctypes.c_int),
                        ('top', ctypes.c_int), ('bottom', ctypes.c_int)]

        dwm.DwmEnableBlurBehindWindow.argtypes = [wintypes.HWND, ctypes.POINTER(Blur)]
        dwm.DwmEnableBlurBehindWindow.restype = ctypes.c_long
        dwm.DwmExtendFrameIntoClientArea.argtypes = [wintypes.HWND, ctypes.POINTER(Margins)]
        dwm.DwmExtendFrameIntoClientArea.restype = ctypes.c_long
        # Establish the alpha-capable DWM client surface first. This call alone
        # is not the blur implementation on Windows 10/11; accent policy is below.
        blur = Blur(1, True, None, False)
        if dwm.DwmEnableBlurBehindWindow(hwnd, ctypes.byref(blur)) < 0:
            return False
        margins = Margins(-1, -1, -1, -1)
        if dwm.DwmExtendFrameIntoClientArea(hwnd, ctypes.byref(margins)) < 0:
            return False

        class ACCENT_POLICY(ctypes.Structure):
            _fields_ = [
                ("AccentState", ctypes.c_int),
                ("AccentFlags", ctypes.c_int),
                ("GradientColor", ctypes.c_uint32),
                ("AnimationId", ctypes.c_int),
            ]

        class WINDOWCOMPOSITIONATTRIBDATA(ctypes.Structure):
            _fields_ = [
                ("Attribute", ctypes.c_int),
                ("Data", ctypes.c_void_p),
                ("SizeOfData", ctypes.c_size_t),
            ]

        r, g, b = tint
        gradient = (opacity << 24) | (b << 16) | (g << 8) | r  # AABBGGRR

        set_composition = user32.SetWindowCompositionAttribute
        set_composition.argtypes = [
            wintypes.HWND,
            ctypes.POINTER(WINDOWCOMPOSITIONATTRIBDATA),
        ]
        set_composition.restype = wintypes.BOOL

        # 4 = ACRYLICBLURBEHIND, lalu 3 = BLURBEHIND sebagai cadangan.
        for state in (4, 3):
            accent = ACCENT_POLICY(state, 0, gradient, 0)
            data = WINDOWCOMPOSITIONATTRIBDATA(
                19, ctypes.cast(ctypes.pointer(accent), ctypes.c_void_p),
                ctypes.sizeof(accent),
            )
            if set_composition(hwnd, ctypes.byref(data)):
                return True
        return False
    except (AttributeError, OSError, ValueError, ctypes.ArgumentError):
        return False
