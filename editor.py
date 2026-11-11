from __future__ import annotations
import re, uuid
from pathlib import Path
from urllib.parse import urlparse
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QShortcut, QKeySequence
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QComboBox, QPlainTextEdit, QFormLayout, QScrollArea, QFrame,
    QFileDialog, QMessageBox, QCompleter, QKeySequenceEdit)
from storage import (app_directory, bundled_file, expand_path, resolve_executable,
    resolve_local_path, save_items)
from widgets import GlassWindow, button, shortcut_icon,normalized_icon
from keybindings import normalize_key
from app_picker import AppPicker

class Editor(GlassWindow):
    def __init__(self, owner, item=None):
        super().__init__(owner, dialog=True)
        self.setWindowTitle('Edit shortcut — AERI' if item else 'Tambah shortcut — AERI')
        self.owner = owner
        self.original = item
        self.icon_policy=(item or {}).get('icon','auto')
        self.picker=None
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setMinimumWidth(480)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28,24,28,24)
        header = QHBoxLayout()
        title = QLabel('Edit shortcut' if item else 'Tambah shortcut')
        title.setObjectName('dialogTitle')
        header.addWidget(title)
        header.addStretch()
        header.addWidget(button('×', self.close, 'iconButton'))
        layout.addLayout(header)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        host = QWidget()
        host.setObjectName('content')
        form = QFormLayout(host)
        form.setVerticalSpacing(12);form.setHorizontalSpacing(16)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignVCenter)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        value = item or {'type': 'app', 'category': 'Pribadi'}
        self.name = QLineEdit(value.get('name', ''))
        self.kind = QComboBox()
        for label, data in [('Aplikasi', 'app'), ('Folder', 'folder'), ('Website', 'website')]:
            self.kind.addItem(label, data)
        self.kind.setCurrentIndex(max(0, self.kind.findData(value.get('type', 'app'))))
        self.path = QLineEdit(value.get('path', ''))
        self.category = QLineEdit(value.get('category', ''))
        completer = QCompleter(sorted({entry['category'] for entry in owner.items}), self.category)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.category.setCompleter(completer)
        self.args = QPlainTextEdit('\n'.join(value.get('args', [])))
        self.args.setPlaceholderText('Satu argumen per baris, misalnya:\n--profile-directory=Profile 1')
        self.args.setFixedHeight(75)
        self.icon_path = QLineEdit(value.get('icon_path', ''))
        self.hotkey = QKeySequenceEdit(QKeySequence(value.get('hotkey','')))
        self.hotkey.setAttribute(Qt.WidgetAttribute.WA_StyledBackground,True)
        self.hotkey.setMaximumSequenceLength(1)
        self.hotkey.setClearButtonEnabled(True)
        for field in (self.name,self.kind,self.path,self.category,self.icon_path,self.hotkey):
            field.setFixedHeight(40)
        form.addRow('Nama', self.name)
        form.addRow('Jenis', self.kind)
        self.installed=button('Pilih aplikasi terpasang…',self.pick_installed)
        self.installed.setFixedHeight(40);form.addRow('',self.installed)
        form.addRow('Tombol cepat',self.hotkey)
        for label, field, callback in [('Lokasi / URL', self.path, self.browse_target),
                                       ('Ikon khusus', self.icon_path, self.browse_icon)]:
            row = QHBoxLayout()
            row.addWidget(field)
            browse=button('Pilih…',callback);browse.setFixedSize(64,40)
            row.setSpacing(8);row.addWidget(browse)
            form.addRow(label, row)
        form.addRow('Kategori', self.category)
        form.addRow('Argumen', self.args)
        self.preview = QLabel()
        self.preview.setMinimumHeight(48)
        self.preview.setAlignment(Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignVCenter)
        form.addRow('Pratinjau', self.preview)
        note = QLabel('Aplikasi web Chrome: pilih shortcut .lnk agar tetap terbuka sebagai aplikasi.\nTombol cepat aktif saat launcher terbuka. Ikon khusus bersifat opsional.')
        note.setObjectName('muted')
        note.setWordWrap(True)
        form.addRow(note)
        scroll.setWidget(host)
        layout.addWidget(scroll, 1)
        self.error = QLabel()
        self.error.setObjectName('error')
        self.error.setWordWrap(True)
        layout.addWidget(self.error)
        footer = QHBoxLayout()
        if item is not None:
            footer.addWidget(button('Hapus', self.delete, 'danger'))
        footer.addStretch()
        footer.addWidget(button('Batal', self.close))
        footer.addWidget(button('Simpan', self.save, 'primary'))
        layout.addLayout(footer)
        self.icon_path.textChanged.connect(self.preview_icon)
        self.path.textChanged.connect(self.preview_icon)
        self.kind.currentIndexChanged.connect(self.preview_icon)
        self.kind.currentIndexChanged.connect(self.update_kind)
        self.update_kind()
        QShortcut(QKeySequence('Ctrl+S'), self, activated=self.save)
        self.resize(640, min(700, QApplication.primaryScreen().availableGeometry().height() - 40))
        self.preview_icon()

    def update_kind(self):
        kind = self.kind.currentData()
        self.path.setPlaceholderText({'app': 'Pilih file .exe atau shortcut .lnk',
                                     'folder': 'Pilih folder', 'website': 'https://contoh.com'}[kind])
        self.args.setEnabled(kind == 'app')
        self.installed.setEnabled(kind=='app')

    def pick_installed(self):
        self.picker=AppPicker(self);self.picker.picked.connect(self.use_installed)
        self.picker.show();self.picker.move(self.frameGeometry().center()-self.picker.rect().center())

    def use_installed(self,item):
        self.icon_policy=item.get('icon','auto')
        self.name.setText(item['name']);self.kind.setCurrentIndex(self.kind.findData('app'))
        self.path.setText(item['path']);self.args.setPlainText('\n'.join(item.get('args',[])))
        self.icon_path.setText(item.get('icon_path',''));self.category.setText(item.get('category','Aplikasi'))

    def preview_icon(self):
        image = shortcut_icon({'type': self.kind.currentData(), 'path': self.path.text(),
                               'icon_path': self.icon_path.text()})
        self.preview.clear()
        if image.isNull():
            self.preview.setText('Ikon belum tersedia · menggunakan inisial nama')
        else:
            self.preview.setPixmap(normalized_icon(image,dpr=self.devicePixelRatioF()))

    def browse_target(self):
        if self.kind.currentData() == 'website':
            self.path.setPlaceholderText('https://contoh.com')
            self.path.setFocus()
            return
        if self.kind.currentData() == 'folder':
            path = QFileDialog.getExistingDirectory(self, 'Pilih folder')
        else:
            path, _ = QFileDialog.getOpenFileName(self, 'Pilih aplikasi atau shortcut', '',
                                                 'Aplikasi (*.exe *.lnk *.url);;Semua file (*)')
        if path:
            self.path.setText(path)
            if not self.name.text().strip():
                self.name.setText(Path(path).stem)

    def browse_icon(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Pilih ikon', '', 'Gambar (*.png *.ico *.jpg *.jpeg *.webp)')
        if path:
            self.icon_path.setText(path)

    def save(self):
        imported_icon = None
        try:
            if not self.owner.loaded:
                raise ValueError('Muat ulang konfigurasi yang valid sebelum menyimpan shortcut.')
            item = dict(self.original or {})
            item.update(name=self.name.text().strip(), type=self.kind.currentData(),
                        path=self.path.text().strip(), category=self.category.text().strip(),
                        args=[line for line in self.args.toPlainText().splitlines() if line.strip()],
                        icon_path=self.icon_path.text().strip())
            item['hotkey']=normalize_key(self.hotkey.keySequence().toString(QKeySequence.SequenceFormat.PortableText))
            if item['hotkey'] and item['hotkey']==self.owner.preferences['global_hotkey']:
                raise ValueError('Tombol ini dipakai untuk membuka launcher. Pilih tombol aplikasi yang lain.')
            if item['hotkey']:
                for existing in self.owner.items:
                    if existing is not self.original and normalize_key(existing.get('hotkey',''))==item['hotkey']:
                        raise ValueError(f'Tombol {item["hotkey"]} sudah dipakai oleh {existing["name"]}.')
            if not all(item[key] for key in ('name', 'path', 'category')):
                raise ValueError('Nama, lokasi, dan kategori wajib diisi.')
            if item['type'] == 'website':
                url = urlparse(item['path'])
                if url.scheme not in {'http', 'https'} or not url.netloc:
                    raise ValueError('Masukkan URL http:// atau https:// yang valid.')
            elif item['type'] == 'folder':
                if not resolve_local_path(item['path']).is_dir():
                    raise ValueError('Folder tidak ditemukan.')
            elif not item['path'].endswith(':') and not resolve_executable(item['path']):
                raise ValueError('Aplikasi tidak ditemukan. Gunakan tombol Pilih….')
            if item['type'] != 'app':
                item['args'] = []
            if item['type'] == 'app' and item['path'].endswith(':') and not re.fullmatch(r'[a-zA-Z][a-zA-Z0-9+.-]{1,}:', item['path']):
                raise ValueError('Protokol aplikasi tidak valid.')
            if Path(item['path']).suffix.lower() in {'.lnk', '.url'} and item['args']:
                raise ValueError('Atur argumen di shortcut Windows, atau pilih target .exe.')
            if item['icon_path'] and item['icon_path'] != (self.original or {}).get('icon_path'):
                source = Path(expand_path(item['icon_path']))
                if not source.is_absolute():
                    local = app_directory() / source
                    source = local if local.is_file() else bundled_file(item['icon_path'])
                image = QPixmap(str(source))
                if image.isNull():
                    raise ValueError('Gambar ikon tidak dapat dibaca.')
                folder = app_directory() / 'icons'
                folder.mkdir(exist_ok=True)
                target = folder / (uuid.uuid4().hex + '.png')
                if image.width() > 256 or image.height() > 256:
                    image = image.scaled(256, 256, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                if not image.save(str(target)):
                    raise OSError('Ikon tidak dapat disimpan.')
                imported_icon = target
                item['icon_path'] = 'icons/' + target.name
            item['icon']=self.icon_policy
            items = [item if old is self.original else old for old in self.owner.items]
            if self.original is None:
                items.append(item)
            save_items(items)
            imported_icon = None
            self.owner.reload()
            self.owner.search.clear()
            self.owner.categories.setCurrentIndex(0)
            self.close()
        except (OSError, ValueError) as exc:
            if imported_icon is not None:
                try:
                    imported_icon.unlink()
                except OSError:
                    pass
            self.error.setText(str(exc))

    def delete(self):
        if QMessageBox.question(self, 'Hapus shortcut?', f'Hapus "{self.original["name"]}" dari launcher?',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
            return
        try:
            save_items([item for item in self.owner.items if item is not self.original])
            self.owner.reload()
            self.close()
        except OSError as exc:
            self.error.setText(str(exc))

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        elif event.key() == Qt.Key.Key_S and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.save()
        else:
            super().keyPressEvent(event)
