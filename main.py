"""Resident, single-instance launcher with customizable exact hotkeys."""
import argparse,os,subprocess,sys,json,hashlib
from pathlib import Path
from PySide6.QtCore import QLockFile,QDir,QTimer
from PySide6.QtNetwork import QLocalServer,QLocalSocket
from PySide6.QtWidgets import QApplication, QMessageBox, QFileDialog
from PySide6.QtGui import QDesktopServices
from launcher import Launcher
from editor import Editor
from widgets import STYLE, GlassWindow, Card, button, shortcut_icon,app_icon
from storage import save_items, load_shortcuts

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--background',action='store_true')
    parser.add_argument('--install',action='store_true')
    parser.add_argument('--install-dir')
    parser.add_argument('--quiet',action='store_true')
    args=parser.parse_args()
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName('AERI')
    app.setQuitOnLastWindowClosed(False)
    app.setWindowIcon(app_icon())
    app.setStyle('Fusion')
    app.setStyleSheet(STYLE)
    if args.install:
        from installer import install_application
        try:target,link=install_application(args.install_dir)
        except (OSError,ValueError) as exc:
            if not args.quiet:
                QMessageBox.warning(None,'AERI belum diperbarui',
                    'Pemasangan belum selesai. Jika AERI masih berjalan, pilih Keluar pada ikon tray lalu jalankan PASANG.cmd kembali.\n\n'+str(exc))
            return 1
        if not args.quiet:
            QMessageBox.information(None,'AERI terpasang','Shortcut desktop siap.\n\n'+str(link))
        return 0
    name='AERIKeys-'+hashlib.sha256(os.environ.get('USERNAME','user').encode()).hexdigest()[:12]
    lock=QLockFile(QDir.tempPath()+'/'+name+'.lock')
    if not lock.tryLock(0):
        client=QLocalSocket();client.connectToServer(name)
        if client.waitForConnected(800):
            client.write(b'show');client.flush();client.waitForBytesWritten(300)
        else:QMessageBox.information(None,'AERI','Launcher sudah berjalan. Gunakan ikon AERI di tray.')
        return
    server=QLocalServer(app)
    server.setSocketOptions(QLocalServer.SocketOption.UserAccessOption)
    QLocalServer.removeServer(name)
    if not server.listen(name):
        lock.unlock();raise OSError('Tidak dapat menyiapkan instance launcher.')
    window = Launcher()
    from runtime import RuntimeController
    controller=RuntimeController(app,window)
    app._controller,app._server,app._lock=controller,server,lock
    def show_existing():
        while server.hasPendingConnections():
            client=server.nextPendingConnection()
            client.disconnectFromServer();client.deleteLater()
        window.show_launcher()
    server.newConnection.connect(show_existing)
    app.aboutToQuit.connect(server.close)
    app.aboutToQuit.connect(lock.unlock)
    if not args.background:window.show_launcher()
    QTimer.singleShot(0,controller.start)
    app.exec()

if __name__ == '__main__':
    main()
