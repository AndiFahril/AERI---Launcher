import sys
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence,QShortcut
from PySide6.QtWidgets import (QVBoxLayout,QHBoxLayout,QLabel,QFormLayout,QKeySequenceEdit,QCheckBox)
from widgets import GlassWindow,button
from keybindings import normalize_key

class SettingsDialog(GlassWindow):
    def __init__(self,owner):
        super().__init__(owner,dialog=True)
        self.owner=owner
        self.setWindowTitle('Pengaturan — AERI')
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setMinimumWidth(490)
        self.resize(520,320)
        layout=QVBoxLayout(self)
        layout.setContentsMargins(28,24,28,24)
        title=QHBoxLayout()
        label=QLabel('Pengaturan')
        label.setObjectName('dialogTitle')
        title.addWidget(label);title.addStretch();title.addWidget(button('×',self.close,'iconButton'))
        layout.addLayout(title)
        form=QFormLayout()
        form.setVerticalSpacing(12);form.setHorizontalSpacing(16)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignVCenter)
        self.hotkey=QKeySequenceEdit(QKeySequence(owner.preferences['global_hotkey']))
        self.hotkey.setAttribute(Qt.WidgetAttribute.WA_StyledBackground,True)
        self.hotkey.setMaximumSequenceLength(1)
        self.hotkey.setClearButtonEnabled(True)
        self.hotkey.setFixedHeight(40)
        self.hotkey.setAccessibleName('Shortcut global AERI')
        form.addRow('Tombol global',self.hotkey)
        self.startup=QCheckBox('Jalankan saat masuk Windows')
        self.startup.setChecked(owner.preferences.get('autostart',False))
        self.startup.setEnabled(bool(getattr(sys,'frozen',False)))
        if not self.startup.isEnabled():
            self.startup.setText('Jalankan saat masuk Windows (khusus EXE)')
            self.startup.setStyleSheet('QCheckBox:disabled { color: #97A29C; }')
            self.startup.setToolTip('Opsi ini tersedia ketika AERI dijalankan melalui AERI.exe.')
        form.addRow('',self.startup)
        layout.addLayout(form)
        note=QLabel('Shortcut global membuka AERI dari aplikasi lain. Launcher tetap siap melalui ikon di tray.')
        note.setObjectName('muted');note.setWordWrap(True);layout.addWidget(note)
        self.error=QLabel();self.error.setObjectName('error');self.error.setWordWrap(True)
        self.error.hide()
        layout.addWidget(self.error)
        self.hotkey.keySequenceChanged.connect(self.clear_error)
        self.startup.toggled.connect(self.clear_error)
        layout.addStretch()
        row=QHBoxLayout();row.addStretch()
        row.addWidget(button('Batal',self.close));row.addWidget(button('Simpan',self.save,'primary'))
        layout.addLayout(row)
        QShortcut(QKeySequence('Escape'),self,activated=self.close)
        QShortcut(QKeySequence('Ctrl+S'),self,activated=self.save)
    def clear_error(self,*args):
        self.error.clear();self.error.hide()
    def save(self):
        self.clear_error()
        try:
            key=normalize_key(self.hotkey.keySequence().toString(QKeySequence.SequenceFormat.PortableText),global_key=True)
            values={'global_hotkey':key,'autostart':self.startup.isChecked()}
            if self.owner.controller is None:
                raise ValueError('Pengaturan global tersedia saat aplikasi dijalankan melalui main.py atau EXE.')
            self.owner.controller.configure(values)
            self.owner.preferences=values
            self.close()
        except (ValueError,OSError) as exc:
            self.error.setText(str(exc))
            self.error.show()
