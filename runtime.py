from PySide6.QtCore import QObject
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QSystemTrayIcon,QMenu,QApplication,QMessageBox
from keybindings import GlobalHotkey
from storage import save_settings
from widgets import app_icon
from integration import set_autostart

class RuntimeController(QObject):
    def __init__(self,app,window):
        super().__init__(app)
        self.app,self.window=app,window
        window.controller=self
        self.hotkey=GlobalHotkey(app,int(window.winId()))
        self.hotkey.activated.connect(self.toggle)
        self.tray=QSystemTrayIcon(app_icon(),self)
        self.menu=QMenu()
        self.open_action=self.menu.addAction('Buka launcher',window.show_launcher)
        self.menu.addAction('Pengaturan shortcut',self.open_settings)
        self.menu.addAction('Muat ulang',window.reload)
        self.menu.addSeparator()
        self.menu.addAction('Keluar',self.quit)
        self.tray.setContextMenu(self.menu)
        self.tray.activated.connect(self._tray_click)
        app.aboutToQuit.connect(self.hotkey.close)
        self.tray.show()
    def start(self):
        try:self.hotkey.replace(self.window.preferences['global_hotkey'])
        except ValueError as exc:
            self.window.show_launcher()
            QMessageBox.warning(self.window,'Shortcut global belum aktif',str(exc))
        self.update_label()
    def update_label(self):
        key=self.hotkey.sequence or 'belum diatur'
        self.open_action.setText('Buka launcher  ·  '+key)
        self.tray.setToolTip('AERI · '+key)
    def toggle(self):
        modal=QApplication.activeModalWidget()
        if modal is not None:
            modal.raise_();modal.activateWindow();return
        if self.window.isVisible() and self.window.isActiveWindow():self.window.hide_launcher()
        else:self.window.show_launcher()
    def _tray_click(self,reason):
        if reason in (QSystemTrayIcon.ActivationReason.Trigger,QSystemTrayIcon.ActivationReason.DoubleClick):
            self.window.show_launcher()
    def open_settings(self):
        self.window.show_launcher();self.window.show_settings()
    def configure(self,values):
        for item in self.window.items:
            if item.get('hotkey')==values['global_hotkey']:
                raise ValueError('Tombol ini sudah dipakai oleh '+item['name']+'.')
        old=dict(self.window.preferences)
        changed=values['autostart']!=old.get('autostart',False)
        def persist():
            if changed:set_autostart(values['autostart'])
            try:save_settings(values)
            except Exception:
                if changed:set_autostart(old.get('autostart',False))
                raise
        self.hotkey.replace(values['global_hotkey'],persist)
        self.window.preferences=dict(values);self.update_label()
    def quit(self):
        self.hotkey.close();self.tray.hide()
        self.window._quitting=True;self.window.close();self.app.quit()
