from PySide6.QtCore import Qt,QSize
from PySide6.QtGui import QShortcut,QKeySequence,QIcon
from PySide6.QtWidgets import (QVBoxLayout,QHBoxLayout,QLabel,QListWidget,QListWidgetItem,QAbstractItemView)
from widgets import GlassWindow,button,shortcut_icon,normalized_icon
from storage import save_items

class OrderDialog(GlassWindow):
    def __init__(self,owner):
        super().__init__(owner,dialog=True);self.owner=owner;self.original=list(owner.items)
        self.setWindowTitle('Atur posisi — AERI');self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.resize(540,560)
        layout=QVBoxLayout(self);layout.setContentsMargins(28,24,28,24);layout.setSpacing(12)
        header=QHBoxLayout();title=QLabel('Atur posisi');title.setObjectName('dialogTitle')
        header.addWidget(title);header.addStretch();header.addWidget(button('×',self.close,'iconButton'));layout.addLayout(header)
        note=QLabel('Seret untuk mengurutkan. Setiap 12 aplikasi mengisi satu halaman.')
        note.setObjectName('muted');note.setWordWrap(True);layout.addWidget(note)
        self.list=QListWidget();self.list.setObjectName('appList');self.list.setIconSize(QSize(32,32))
        self.list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.list.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.list.setDragDropOverwriteMode(False)
        for index,item in enumerate(self.original):
            icon=QIcon(normalized_icon(shortcut_icon(item),extent=28,canvas=32,dpr=self.devicePixelRatioF()))
            row=QListWidgetItem(icon,item['name']);row.setData(Qt.ItemDataRole.UserRole,index)
            row.setSizeHint(QSize(200,48));self.list.addItem(row)
        self.list.setCurrentRow(0);layout.addWidget(self.list,1)
        self.position=QLabel();self.position.setObjectName('muted');layout.addWidget(self.position)
        self.list.currentRowChanged.connect(self.update_position)
        self.list.model().rowsMoved.connect(self.update_position);self.update_position()
        self.error=QLabel();self.error.setObjectName('error');self.error.setWordWrap(True);layout.addWidget(self.error)
        footer=QHBoxLayout();footer.addWidget(button('Naik',lambda:self.move_row(-1)))
        footer.addWidget(button('Turun',lambda:self.move_row(1)));footer.addStretch()
        footer.addWidget(button('Batal',self.close));footer.addWidget(button('Simpan',self.save,'primary'));layout.addLayout(footer)
        QShortcut(QKeySequence('Escape'),self,activated=self.close)
        QShortcut(QKeySequence('Ctrl+S'),self,activated=self.save)
    def update_position(self,*args):
        row=self.list.currentRow()
        self.position.setText(f'Halaman {row//12+1} · Posisi {row%12+1}' if row>=0 else '')
    def move_row(self,direction):
        source=self.list.currentRow();target=source+direction
        if source<0 or not 0<=target<self.list.count():return
        item=self.list.takeItem(source);self.list.insertItem(target,item);self.list.setCurrentRow(target)
    def save(self):
        indices=[self.list.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.list.count())]
        if len(indices)!=len(self.original) or set(indices)!=set(range(len(self.original))):
            self.error.setText('Urutan tidak valid. Tutup dan buka kembali pengaturan posisi.');return
        values=[self.original[index] for index in indices]
        try:save_items(values)
        except (OSError,ValueError) as exc:self.error.setText(str(exc));return
        self.owner.reload();self.close()
