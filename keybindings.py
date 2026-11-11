"""One-key local bindings and an exact Windows RegisterHotKey subscription."""
import ctypes
from ctypes import wintypes
import sys
from PySide6.QtCore import QObject, Signal, QAbstractNativeEventFilter, Qt
from PySide6.QtGui import QKeySequence

RESERVED = {'Esc','Escape','Return','Enter','Tab','Backtab','Space','/',
            'Ctrl+F','Ctrl+N','Ctrl+R','Ctrl+,','Ctrl+Left','Ctrl+Right','PgUp','PgDown'}

def normalize_key(value, global_key=False):
    if not isinstance(value,str):
        raise ValueError('Shortcut harus berupa teks.')
    value=value.strip()
    if not value:
        if global_key:
            raise ValueError('Shortcut launcher wajib diisi.')
        return ''
    sequence=QKeySequence.fromString(value,QKeySequence.SequenceFormat.PortableText)
    if sequence.count()!=1 or sequence.isEmpty():
        raise ValueError('Gunakan satu tombol atau satu kombinasi tombol.')
    combo=sequence[0]
    if combo.key() in (Qt.Key.Key_unknown,Qt.Key.Key_Control,Qt.Key.Key_Alt,Qt.Key.Key_Shift,Qt.Key.Key_Meta):
        raise ValueError('Pilih tombol lengkap, misalnya W atau Alt+Z.')
    text=sequence.toString(QKeySequence.SequenceFormat.PortableText)
    if global_key:
        mods=combo.keyboardModifiers()
        if not mods & (Qt.KeyboardModifier.ControlModifier|Qt.KeyboardModifier.AltModifier|Qt.KeyboardModifier.MetaModifier):
            raise ValueError('Shortcut global harus memakai Ctrl, Alt, atau Win, misalnya Alt+Z.')
        if combo.key()==Qt.Key.Key_F12:
            raise ValueError('F12 dicadangkan Windows. Pilih tombol lain.')
        if text in RESERVED:
            raise ValueError('Tombol ini dipakai navigasi AERI. Pilih shortcut global lain.')
    elif text in RESERVED:
        raise ValueError('Tombol ini dipakai navigasi launcher. Pilih tombol lain.')
    return text

def event_key(event):
    return QKeySequence(event.key()|event.modifiers().value).toString(QKeySequence.SequenceFormat.PortableText)

def validate_bindings(items):
    seen={}
    for item in items:
        key=normalize_key(item.get('hotkey',''))
        if key:
            if key in seen:
                raise ValueError(f'Shortcut {key} dipakai oleh {seen[key]} dan {item["name"]}.')
            seen[key]=item['name']
        item['hotkey']=key
    return items

def native_combination(value):
    value=normalize_key(value,global_key=True)
    combo=QKeySequence.fromString(value,QKeySequence.SequenceFormat.PortableText)[0]
    flags=0
    for qt,win in [(Qt.KeyboardModifier.AltModifier,1),(Qt.KeyboardModifier.ControlModifier,2),
                   (Qt.KeyboardModifier.ShiftModifier,4),(Qt.KeyboardModifier.MetaModifier,8)]:
        if combo.keyboardModifiers() & qt:
            flags|=win
    key=combo.key().value
    if 65<=key<=90 or 48<=key<=57:
        vk=key
    elif Qt.Key.Key_F1.value<=key<=Qt.Key.Key_F24.value:
        vk=0x70+key-Qt.Key.Key_F1.value
    else:
        common={Qt.Key.Key_Space.value:0x20,Qt.Key.Key_Home.value:0x24,Qt.Key.Key_End.value:0x23,
                Qt.Key.Key_Left.value:0x25,Qt.Key.Key_Up.value:0x26,Qt.Key.Key_Right.value:0x27,
                Qt.Key.Key_Down.value:0x28,Qt.Key.Key_PageUp.value:0x21,Qt.Key.Key_PageDown.value:0x22,
                Qt.Key.Key_Insert.value:0x2D,Qt.Key.Key_Delete.value:0x2E}
        vk=common.get(key)
        if vk is None and 33<=key<=126 and sys.platform=='win32':
            user=ctypes.WinDLL('user32')
            user.VkKeyScanW.argtypes=[wintypes.WCHAR]
            user.VkKeyScanW.restype=ctypes.c_short
            scan=user.VkKeyScanW(chr(key))
            if scan!=-1:
                vk=scan & 255
                if (scan>>8)&1:flags|=4
        if vk is None:
            raise ValueError('Tombol global ini belum didukung. Gunakan huruf, angka, atau tombol fungsi.')
    return flags|0x4000,vk

class _Filter(QAbstractNativeEventFilter):
    def __init__(self,owner):
        super().__init__()
        self.owner=owner
    def nativeEventFilter(self,event_type,message):
        if sys.platform=='win32':
            msg=wintypes.MSG.from_address(int(message))
            if msg.message==0x0312 and msg.wParam==self.owner.active_id:
                self.owner.activated.emit()
                return True,0
        return False,0

class GlobalHotkey(QObject):
    activated=Signal()
    def __init__(self,app,hwnd,user=None):
        super().__init__()
        self.app,self.hwnd=app,hwnd
        self.user=user or ctypes.WinDLL('user32',use_last_error=True)
        if user is None:
            self.user.RegisterHotKey.argtypes=[wintypes.HWND,ctypes.c_int,wintypes.UINT,wintypes.UINT]
            self.user.RegisterHotKey.restype=wintypes.BOOL
            self.user.UnregisterHotKey.argtypes=[wintypes.HWND,ctypes.c_int]
        self.active_id=None
        self.sequence=''
        self.filter=_Filter(self)
        app.installNativeEventFilter(self.filter)
        self.closed=False
    def replace(self,sequence,persist=lambda:None):
        sequence=normalize_key(sequence,global_key=True)
        mods,vk=native_combination(sequence)
        if sequence==self.sequence:
            persist()
            return
        candidate=0x5A01 if self.active_id!=0x5A01 else 0x5A02
        if not self.user.RegisterHotKey(self.hwnd,candidate,mods,vk):
            raise ValueError(f'{sequence} sedang dipakai aplikasi lain atau dicadangkan Windows. Pilih kombinasi lain.')
        try:
            persist()
        except Exception:
            self.user.UnregisterHotKey(self.hwnd,candidate)
            raise
        old=self.active_id
        self.active_id,self.sequence=candidate,sequence
        if old is not None:
            self.user.UnregisterHotKey(self.hwnd,old)
    def close(self):
        if self.closed:return
        self.closed=True
        if self.active_id is not None:
            self.user.UnregisterHotKey(self.hwnd,self.active_id)
        self.app.removeNativeEventFilter(self.filter)
        self.active_id=None
