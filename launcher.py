from __future__ import annotations
from PySide6.QtCore import Qt,QTimer,QEvent
from PySide6.QtGui import QShortcut,QKeySequence,QCursor
from PySide6.QtWidgets import (QApplication,QWidget,QLabel,QVBoxLayout,QHBoxLayout,
    QGridLayout,QLineEdit,QComboBox,QMessageBox,QPlainTextEdit,QTextEdit,QKeySequenceEdit)
from storage import load_shortcuts,load_settings,ConfigError
from widgets import GlassWindow,Card,button
from editor import Editor
from settings_dialog import SettingsDialog
from shortcuts import open_shortcut
from keybindings import event_key
from paging import SlidePages,AppPage
from order_dialog import OrderDialog

class Launcher(GlassWindow):
    PAGE_SIZE=12
    # One shared layout scale makes the launcher visually balanced at every size.
    OUTER_MARGIN=32
    HEADER_SIDE=88
    TOOLBAR_HEIGHT=42
    def __init__(self):
        super().__init__()
        self.items=[];self.visible=[];self.editor=None;self.settings_dialog=None;self.order_dialog=None
        self.controller=None;self.loaded=False;self._columns=4;self._quitting=False
        self._wheel_amount=0;self._wheel_switched=False
        self.wheel_timer=QTimer(self);self.wheel_timer.setSingleShot(True)
        self.wheel_timer.timeout.connect(self.reset_wheel)
        try:self.preferences=load_settings()
        except ConfigError:self.preferences={'global_hotkey':'Alt+Z','autostart':False}
        self.setWindowTitle('AERI');self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMinimumSize(800,600)
        area=QApplication.primaryScreen().availableGeometry()
        self.resize(min(1000,area.width()-48),min(640,area.height()-48))
        self.move(area.center()-self.rect().center())
        root=QVBoxLayout(self);root.setContentsMargins(self.OUTER_MARGIN,24,self.OUTER_MARGIN,24);root.setSpacing(16)
        header=QGridLayout();header.setContentsMargins(0,0,0,0)
        # Equal side columns keep the search field centred around the window.
        header.setColumnMinimumWidth(0,self.HEADER_SIDE);header.setColumnMinimumWidth(2,self.HEADER_SIDE);header.setColumnStretch(1,1)
        spacer=QWidget();spacer.setFixedWidth(self.HEADER_SIDE);header.addWidget(spacer,0,0)
        self.search=QLineEdit();self.search.setObjectName('search')
        self.search.setPlaceholderText('Cari aplikasi…  Ctrl+F');self.search.setAccessibleName('Cari aplikasi')
        self.search.setClearButtonEnabled(True);self.search.setFixedHeight(44)
        self.search.textChanged.connect(self.render_cards)
        self.search.returnPressed.connect(lambda:self.launch(self.visible[0]) if self.visible else None)
        header.addWidget(self.search,0,1,Qt.AlignmentFlag.AlignCenter)
        actions=QHBoxLayout();actions.setSpacing(8);actions.setContentsMargins(0,0,0,0)
        settings=button('⚙',self.show_settings,'iconButton');settings.setFixedSize(34,34)
        settings.setToolTip('Shortcut launcher · Ctrl+,')
        close=button('×',self.hide_launcher,'iconButton');close.setFixedSize(34,34);close.setToolTip('Sembunyikan · Esc')
        actions.addWidget(settings);actions.addWidget(close)
        action_host=QWidget();action_host.setFixedWidth(self.HEADER_SIDE);action_host.setLayout(actions)
        header.addWidget(action_host,0,2);root.addLayout(header)
        toolbar=QHBoxLayout();toolbar.setContentsMargins(0,0,0,0);toolbar.setSpacing(12)
        self.categories=QComboBox();self.categories.setObjectName('categoryFilter');self.categories.addItem('Semua kategori')
        self.categories.setFixedSize(200,self.TOOLBAR_HEIGHT);self.categories.setAccessibleName('Filter kategori')
        self.categories.currentTextChanged.connect(self.render_cards)
        toolbar.addWidget(self.categories);toolbar.addStretch()
        order=button('Atur posisi',self.show_order,'toolbarButton');order.setFixedSize(132,self.TOOLBAR_HEIGHT);toolbar.addWidget(order)
        add=button('+  Tambah shortcut',lambda:self.edit(),'addShortcut');add.setFixedSize(184,self.TOOLBAR_HEIGHT)
        add.setToolTip('Tambah shortcut · Ctrl+N');toolbar.addWidget(add);root.addLayout(toolbar)
        self.pager=SlidePages();self.host=self.pager
        self.pager.changed.connect(self.update_navigation);self.pager.swipe.connect(self.change_page)
        root.addWidget(self.pager,1)
        footer=QWidget();footer.setFixedHeight(32)
        foot=QHBoxLayout(footer);foot.setContentsMargins(0,0,0,0);foot.addStretch()
        self.page_nav=QWidget();nav=QHBoxLayout(self.page_nav);nav.setContentsMargins(0,0,0,0);nav.setSpacing(12)
        self.previous=button('‹',lambda:self.change_page(-1),'pageArrow');self.previous.setFixedSize(32,32)
        self.previous.setAccessibleName('Halaman sebelumnya');self.previous.setToolTip('Halaman sebelumnya · Ctrl+←')
        self.page_label=QLabel();self.page_label.setObjectName('muted');self.page_label.setFixedWidth(56)
        self.page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.next=button('›',lambda:self.change_page(1),'pageArrow');self.next.setFixedSize(32,32)
        self.next.setAccessibleName('Halaman berikutnya');self.next.setToolTip('Halaman berikutnya · Ctrl+→')
        nav.addWidget(self.previous);nav.addWidget(self.page_label);nav.addWidget(self.next)
        foot.addWidget(self.page_nav);foot.addStretch();root.addWidget(footer)
        self.update_navigation()
        for keys,action in [('Ctrl+F',self.focus_search),('Ctrl+N',lambda:self.edit()),('Ctrl+R',self.reload),('Ctrl+,',self.show_settings)]:
            QShortcut(QKeySequence(keys),self,activated=action)
        QApplication.instance().installEventFilter(self)
        self._size_search();QTimer.singleShot(0,self.reload)

    def _size_search(self):
        if hasattr(self,'search'):self.search.setFixedWidth(max(260,min(520,self.width()-250)))
    def resizeEvent(self,event):
        super().resizeEvent(event);self._size_search()
    def focus_search(self):self.search.setFocus();self.search.selectAll()
    def show_launcher(self):
        self.reset_filters()
        screen=QApplication.screenAt(QCursor.pos()) or QApplication.primaryScreen()
        self.move(screen.availableGeometry().center()-self.rect().center())
        self.showNormal();self.raise_();self.activateWindow();self.setFocus(Qt.FocusReason.OtherFocusReason)
    def hide_launcher(self):self.hide()
    def closeEvent(self,event):
        if self.controller is not None and not self._quitting:event.ignore();self.hide_launcher()
        else:super().closeEvent(event)
    def reset_filters(self):
        self.search.clear();self.categories.setCurrentIndex(0)
        self.pager.finish();self.pager.go(0,animate=False);self.reset_wheel()
    def reload(self):
        try:items=load_shortcuts()
        except (ConfigError,OSError) as exc:
            self.loaded=False;QMessageBox.warning(self,'Konfigurasi bermasalah',str(exc));return
        self.items=items;self.loaded=True;selected=self.categories.currentText()
        self.categories.blockSignals(True);self.categories.clear()
        self.categories.addItems(['Semua kategori']+sorted({i['category'] for i in items},key=str.casefold))
        self.categories.setCurrentIndex(max(0,self.categories.findText(selected)))
        self.categories.blockSignals(False);self.render_cards()
    def render_cards(self):
        if not hasattr(self,'pager'):return
        query=self.search.text().strip().casefold();category=self.categories.currentText()
        self.visible=[i for i in self.items if (self.categories.currentIndex()==0 or i['category']==category)
            and query in ' '.join([i['name'],i['path'],i['category'],i.get('hotkey','')]).casefold()]
        pages=[]
        for start in range(0,max(1,len(self.visible)),self.PAGE_SIZE):
            page=AppPage();grid=page.grid
            for index,item in enumerate(self.visible[start:start+self.PAGE_SIZE]):
                card=Card(item);card.launch.connect(lambda item=item:self.launch(item))
                card.edit.connect(lambda item=item:self.edit(item));card.swipe.connect(self.change_page)
                grid.addWidget(card,index//4,index%4)
            if not self.visible:
                label=QLabel('Tidak ditemukan' if query else 'Belum ada shortcut');label.setObjectName('muted')
                label.setAlignment(Qt.AlignmentFlag.AlignCenter);grid.addWidget(label,0,0,3,4)
            pages.append(page)
        self.pager.replace(pages);self.reset_wheel()
    def update_navigation(self,*args):
        if not hasattr(self,'page_nav'):return
        total=len(self.pager.pages);index=self.pager.current_index
        self.page_nav.setVisible(total>1);self.page_label.setText(f'{index+1} / {total}')
        self.previous.setEnabled(index>0);self.next.setEnabled(index<total-1)
    def change_page(self,direction):
        return self.pager.go(self.pager.current_index+direction)
    def reset_wheel(self):
        self.wheel_timer.stop();self._wheel_amount=0;self._wheel_switched=False
    def wheel_page(self,event):
        phase=event.phase()
        if phase==Qt.ScrollPhase.ScrollBegin:self.reset_wheel()
        delta=event.pixelDelta();threshold=60
        if delta.isNull():delta=event.angleDelta();threshold=100
        amount=delta.x() if abs(delta.x())>=abs(delta.y()) else delta.y()
        if not self._wheel_switched:
            self._wheel_amount+=amount
            if abs(self._wheel_amount)>=threshold:
                self.change_page(1 if self._wheel_amount<0 else -1);self._wheel_switched=True
        if phase==Qt.ScrollPhase.ScrollEnd:
            self.wheel_timer.start(200)
        elif phase==Qt.ScrollPhase.NoScrollPhase:self.wheel_timer.start(350)
        event.accept()
    def show_order(self):
        if not self.loaded:return
        if self.order_dialog is not None:
            try:
                if self.order_dialog.isVisible():self.order_dialog.raise_();return
            except RuntimeError:pass
        self.order_dialog=OrderDialog(self);self._show_popup(self.order_dialog)

    def _show_popup(self,popup):
        popup.show();popup.move(self.frameGeometry().center()-popup.rect().center())

    def edit(self,item=None):
        if not self.loaded:
            QMessageBox.warning(self,'Konfigurasi belum siap','Muat ulang apps.json yang valid terlebih dahulu.');return
        if self.editor is not None:
            try:
                if self.editor.isVisible():self.editor.raise_();self.editor.activateWindow();return
            except RuntimeError:pass
        self.editor=Editor(self,item);self._show_popup(self.editor);self.editor.name.setFocus()

    def show_settings(self):
        if self.settings_dialog is not None:
            try:
                if self.settings_dialog.isVisible():self.settings_dialog.raise_();return
            except RuntimeError:pass
        self.settings_dialog=SettingsDialog(self);self._show_popup(self.settings_dialog)

    def launch(self,item):
        try:open_shortcut(item)
        except (OSError,ValueError) as exc:
            QMessageBox.warning(self,'Shortcut tidak dapat dibuka',f'{item["name"]}\n\n{exc}');return False
        self.hide_launcher();return True

    def dispatch_key(self,event,focus=None):
        if event.isAutoRepeat():return False
        if event.key()==Qt.Key.Key_Escape:
            if focus is self.search:self.search.clear();self.setFocus();return True
            self.hide_launcher();return True
        if isinstance(focus,(QLineEdit,QPlainTextEdit,QTextEdit,QKeySequenceEdit,QComboBox)):return False
        if event.key()==Qt.Key.Key_Slash and not event.modifiers():self.focus_search();return True
        key=event_key(event)
        if key in ('PgDown','Ctrl+Right'):self.change_page(1);return True
        if key in ('PgUp','Ctrl+Left'):self.change_page(-1);return True
        for item in self.items:
            if item.get('hotkey') and item['hotkey']==key:self.launch(item);return True
        return False

    def eventFilter(self,obj,event):
        if event.type()==QEvent.Type.Wheel and self.isVisible() and self.isActiveWindow():
            if isinstance(obj,QWidget) and obj.window() is self and not isinstance(obj,(QLineEdit,QComboBox)):
                self.wheel_page(event);return True
        if event.type()==QEvent.Type.KeyPress and self.isVisible() and self.isActiveWindow():
            if isinstance(obj,QWidget) and obj.window() is self:
                if self.dispatch_key(event,QApplication.focusWidget()):return True
        return super().eventFilter(obj,event)

    def keyPressEvent(self,event):
        if self.dispatch_key(event,QApplication.focusWidget()):event.accept()
        else:super().keyPressEvent(event)
