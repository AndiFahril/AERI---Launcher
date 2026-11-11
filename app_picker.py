from PySide6.QtCore import Qt,QSize,Signal
from PySide6.QtGui import QKeySequence,QShortcut,QIcon
from PySide6.QtWidgets import QApplication,QVBoxLayout,QHBoxLayout,QLabel,QLineEdit,QListWidget,QListWidgetItem
from widgets import GlassWindow,button,shortcut_icon,normalized_icon
from app_discovery import DiscoveryWorker

class AppPicker(GlassWindow):
    picked=Signal(dict)
    def __init__(self,owner):
        super().__init__(owner,dialog=True);self.entries=[]
        self.setWindowTitle('Aplikasi terpasang — AERI');self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose);self.resize(560,530)
        layout=QVBoxLayout(self);layout.setContentsMargins(28,24,28,24);layout.setSpacing(12)
        header=QHBoxLayout();title=QLabel('Aplikasi terpasang');title.setObjectName('dialogTitle')
        header.addWidget(title);header.addStretch();header.addWidget(button('×',self.close,'iconButton'));layout.addLayout(header)
        self.search=QLineEdit();self.search.setPlaceholderText('Cari ChatGPT, Visual Studio Code, Drive…')
        self.search.setFixedHeight(42);self.search.textChanged.connect(self.filter);layout.addWidget(self.search)
        self.list=QListWidget();self.list.setObjectName('appList');self.list.setIconSize(QSize(28,28))
        self.list.itemDoubleClicked.connect(self.choose);layout.addWidget(self.list,1)
        self.status=QLabel('Membaca aplikasi dan shortcut Windows…');self.status.setObjectName('muted')
        self.status.setWordWrap(True);layout.addWidget(self.status)
        row=QHBoxLayout();row.addStretch();row.addWidget(button('Batal',self.close))
        row.addWidget(button('Gunakan',self.choose,'primary'));layout.addLayout(row)
        QShortcut(QKeySequence('Escape'),self,activated=self.close)
        QShortcut(QKeySequence('Return'),self,activated=self.choose)
        app=QApplication.instance();worker=DiscoveryWorker(app)
        worker.found.connect(self.populate);worker.finished.connect(worker.deleteLater)
        app.aboutToQuit.connect(worker.shutdown);worker.start()
        self.worker=worker
    def populate(self,entries):self.entries=entries;self.filter()
    def filter(self):
        query=self.search.text().strip().casefold();self.list.clear()
        for index,entry in enumerate(self.entries):
            if query not in (entry['name']+' '+entry.get('source','')).casefold():continue
            icon=QIcon(normalized_icon(shortcut_icon(entry),extent=24,canvas=28,dpr=self.devicePixelRatioF()))
            row=QListWidgetItem(icon,entry['name']+'  ·  '+entry.get('source',''))
            row.setData(Qt.ItemDataRole.UserRole,index);row.setToolTip(entry['path']);row.setSizeHint(QSize(200,44))
            self.list.addItem(row)
        if self.list.count():self.list.setCurrentRow(0)
        self.status.setText('Pilih aplikasi, lalu Gunakan. Shortcut Chrome mempertahankan mode aplikasi dan profilnya.'
            if self.list.count() else 'Tidak ditemukan. Anda tetap dapat memilih file .exe atau shortcut .lnk melalui Pilih….')
    def choose(self,*args):
        row=self.list.currentItem()
        if row is None:return
        self.picked.emit(dict(self.entries[row.data(Qt.ItemDataRole.UserRole)]));self.close()
