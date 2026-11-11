from __future__ import annotations
import sys
from pathlib import Path
from PySide6.QtCore import Qt, QTimer, QFileInfo, Signal, QSize
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap, QRegion, QPalette, QBitmap
from PySide6.QtWidgets import QWidget, QFrame, QLabel, QPushButton, QFileIconProvider, QHBoxLayout, QVBoxLayout, QSizePolicy
from storage import app_directory, bundled_file, expand_path, resolve_executable, resolve_local_path
from windows_effects import enable_windows_acrylic

STYLE = """
QWidget { color: #F4F4F3; font-family: 'Segoe UI'; font-size: 13px; font-weight: 400; }
QWidget#content, QWidget#gridHost, QScrollArea, QScrollArea > QWidget > QWidget {
    background: transparent; border: none; }
QLabel { background: transparent; border: none; }
QLabel#muted { color: #C4C7C8; font-size: 12px; }
QLabel#error { color: #FFB6B6; }
QLabel#dialogTitle { font-size: 20px; font-weight: 600; }
QLabel#cardName { font-size: 14px; font-weight: 600; }
QLineEdit#search { font-size: 15px; }
QComboBox#categoryFilter { font-size: 14px; }
QPushButton#toolbarButton, QPushButton#addShortcut { font-size: 14px; padding: 8px 12px; }
QPushButton#addShortcut { background: rgba(255,255,255,18); border-color: rgba(255,255,255,45); font-weight: 600; }
QWidget#pageHost, QWidget#appPage { background: transparent; border: none; }
QListWidget#appList { background: rgba(0,0,0,40); border: 1px solid rgba(255,255,255,24); border-radius: 10px; padding: 6px; outline: none; }
QListWidget#appList::item { padding: 6px 10px; border-radius: 6px; color: #F4F4F3; }
QListWidget#appList::item:selected { background: rgba(150,195,175,45); color: #F4F4F3; }
QListWidget#appList::item:hover { background: rgba(255,255,255,18); }
QPushButton#pageArrow { background: transparent; border: none; padding: 0; font-size: 20px; }
QPushButton#pageArrow:hover { background: rgba(255,255,255,24); }
QPushButton { background: rgba(255,255,255,10); border: 1px solid rgba(255,255,255,22);
    border-radius: 10px; padding: 9px 13px; }
QPushButton:hover { background: rgba(255,255,255,32); border-color: rgba(255,255,255,65); }
QPushButton:pressed { background: rgba(255,255,255,48); }
QPushButton#primary { background: rgba(255,255,255,18); color: #F2F5F3; font-weight: 600; border: 1px solid rgba(255,255,255,45); }
QPushButton#primary:hover { background: rgba(255,255,255,38); }
QPushButton#iconButton { padding: 5px; border: none; background: transparent; }
QPushButton#iconButton:hover { background: rgba(255,255,255,30); }
QPushButton#danger { color: #FFB6B6; }
QLineEdit, QComboBox, QPlainTextEdit { background: rgba(0,0,0,55);
    border: 1px solid rgba(255,255,255,28); border-radius: 9px; padding: 9px 11px;
    selection-background-color: #536F62; }
QLineEdit:focus, QPlainTextEdit:focus { border: 1px solid rgba(210,235,220,150); }
QComboBox::drop-down { border: none; width: 22px; }
QComboBox QAbstractItemView { background: #252A28; color: white; selection-background-color: #45584D; }
QFrame#card { background: rgba(9,12,13,52); border: 1px solid rgba(255,255,255,28); border-radius: 18px; }
QFrame#card:hover { background: rgba(25,30,29,88); border-color: rgba(230,245,233,96); }
QLabel#keycap { background: rgba(255,255,255,12); border: 1px solid rgba(255,255,255,30); border-radius: 6px; color: #D4E1D9; font-size: 11px; padding: 3px 6px; }
QMenu { background: #1C2821; color: #EDF4EF; border: 1px solid #455A4C; padding: 6px; }
QMenu::item { padding: 7px 22px; border-radius: 5px; }
QMenu::item:selected { background: #354B3E; }
QKeySequenceEdit { background: rgba(0,0,0,45); border: 1px solid rgba(255,255,255,28); border-radius: 8px; padding: 7px; }
QKeySequenceEdit QLineEdit { background: transparent; border: none; padding: 0; }
QCheckBox { background: transparent; spacing: 8px; }
QCheckBox::indicator { width: 16px; height: 16px; border: 1px solid #87968E; border-radius: 4px; background: rgba(0,0,0,55); }
QCheckBox::indicator:checked { background: #6E9B7D; border: 3px solid #E0ECE4; }
QScrollBar:vertical { background: transparent; width: 7px; }
QScrollBar::handle:vertical { background: rgba(255,255,255,55); border-radius: 3px; min-height: 28px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QToolTip { background: #202723; color: white; border: 1px solid #607068; padding: 5px; }
"""

STYLE += """
QMessageBox { background: #18211C; }
QMessageBox QLabel { color: #F0F4F1; }
QMessageBox QPushButton { background: #2C3931; color: #F0F4F1; min-width: 64px; }
"""

def app_icon(name='app'):
    return QIcon(str(bundled_file('assets/app.png' if name=='app' else 'assets/ui/'+name+'.svg')))

def button(text, callback, name=None):
    result = QPushButton(text)
    if name:
        result.setObjectName(name)
    result.clicked.connect(callback)
    result.setCursor(Qt.CursorShape.PointingHandCursor)
    icon={'⚙':'settings','×':'close','✎':'edit'}.get(text)
    if icon:
        result.setText('')
        result.setIcon(app_icon(icon))
        result.setIconSize(QSize(18,18))
        result.setAccessibleName({'settings':'Pengaturan shortcut','close':'Sembunyikan / tutup','edit':'Edit shortcut'}[icon])
    return result

def shortcut_icon(item):
    try:
        return read_shortcut_icon(item)
    except (OSError, ValueError):
        return QIcon()

def normalized_icon(image, extent=40, canvas=48, dpr=1.0):
    """Trim transparent padding; fit artwork without distorting its proportions."""
    dpr=max(1.0,float(dpr))
    result=QPixmap(round(canvas*dpr),round(canvas*dpr))
    result.fill(Qt.GlobalColor.transparent)
    if image.isNull():
        result.setDevicePixelRatio(dpr)
        return result
    source=image.pixmap(256,256)
    if source.isNull():
        result.setDevicePixelRatio(dpr)
        return result
    source.setDevicePixelRatio(1)
    if source.hasAlphaChannel():
        mask=source.toImage().createAlphaMask(Qt.ImageConversionFlag.ThresholdAlphaDither)
        bounds=QRegion(QBitmap.fromImage(mask)).boundingRect()
        if bounds.isEmpty():
            result.setDevicePixelRatio(dpr)
            return result
        source=source.copy(bounds)
    artwork=source.scaled(round(extent*dpr),round(extent*dpr),
        Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation)
    painter=QPainter(result)
    painter.drawPixmap((result.width()-artwork.width())//2,(result.height()-artwork.height())//2,artwork)
    painter.end();result.setDevicePixelRatio(dpr)
    return result

class CardName(QLabel):
    def __init__(self,text):
        super().__init__()
        self.full_text=text
        self.setObjectName('cardName')
        self.setFixedHeight(22)
        self.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Fixed)
        self.setAlignment(Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignVCenter)
        self.setToolTip(text)
    def resizeEvent(self,event):
        super().resizeEvent(event)
        self.setText(self.fontMetrics().elidedText(self.full_text,Qt.TextElideMode.ElideRight,self.contentsRect().width()))

def read_shortcut_icon(item):
    custom = item.get('icon_path', '')
    if custom:
        path = Path(expand_path(custom))
        if not path.is_absolute():
            local = app_directory() / path
            path = local if local.is_file() else bundled_file(custom)
        image = QPixmap(str(path))
        if not image.isNull():
            return QIcon(image)
    if item.get('type') == 'website':
        return QIcon()
    if item.get('icon')=='initial':return QIcon()
    if item.get('args') and str(item['args'][0]).startswith('shell:AppsFolder\\'):return QIcon()
    target = str(resolve_local_path(item.get('path', ''))) if item.get('type') == 'folder' else (resolve_executable(item.get('path', '')) or expand_path(item.get('path', '')))
    if not Path(target).exists():
        return QIcon()
    return QFileIconProvider().icon(QFileInfo(target))

class GlassWindow(QWidget):
    def __init__(self, parent=None, dialog=False):
        super().__init__(parent, Qt.WindowType.Dialog if dialog else Qt.WindowType.Window)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.FramelessWindowHint)
        # Windows acrylic needs a DWM-composed HWND, not Qt's layered window.
        # WA_TranslucentBackground creates WS_EX_LAYERED on Windows and conflicts
        # with that native backdrop, despite producing correct offscreen alpha.
        if sys.platform == 'win32':
            self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
            palette = self.palette()
            palette.setColor(QPalette.ColorRole.Window, QColor(0, 0, 0, 0))
            self.setPalette(palette)
        else:
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAutoFillBackground(False)
        self.setWindowTitle('AERI')
        self.tint = 5
        self.glass_ok = False
        self._drag = None

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(0, self.apply_glass)

    def apply_glass(self):
        # No global window opacity or color-key holes: controls keep full opacity.
        self.glass_ok = enable_windows_acrylic(int(self.winId()), (20, 23, 23), 20)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        self.paint_glass(painter)

    def paint_glass(self, painter):
        # Replace the old alpha each frame instead of accumulating dark layers.
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 0))
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        # Real alpha composition reveals the desktop even without the blur API.
        alpha = round(self.tint * 2.55)
        painter.setBrush(QColor(17, 21, 21, alpha))
        painter.setPen(QPen(QColor(255, 255, 255, 45), 1))
        painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 24, 24)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and event.position().y() < 110:
            if self.windowHandle() and self.windowHandle().startSystemMove():
                return
            self._drag = event.globalPosition().toPoint() - self.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag)

    def mouseReleaseEvent(self, event):
        self._drag = None

    def resizeEvent(self, event):
        super().resizeEvent(event)
        outline = QPainterPath()
        outline.addRoundedRect(self.rect(), 24, 24)
        self.setMask(QRegion(outline.toFillPolygon().toPolygon()))

class Card(QFrame):
    launch = Signal()
    edit = Signal()
    swipe = Signal(int)

    def __init__(self, item):
        super().__init__()
        self.setObjectName('card')
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(120)
        self.origin=None
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setToolTip(item['name']+'\n'+item['path'])
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16,12,16,10);layout.setSpacing(0)
        top = QHBoxLayout()
        top.setContentsMargins(0,0,0,0);top.setSpacing(8)
        icon = QLabel()
        icon.setObjectName('appLogo');icon.setFixedSize(40,40)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        image = shortcut_icon(item)
        if image.isNull():
            icon.setText(item['name'][:1].upper())
            icon.setStyleSheet('font-size: 25px; font-weight: 600;')
        else:
            icon.setPixmap(normalized_icon(image,extent=36,canvas=40,dpr=self.devicePixelRatioF()))
        top.addWidget(icon)
        top.addStretch()
        if item.get('hotkey'):
            cap=QLabel(item['hotkey'])
            cap.setObjectName('keycap')
            cap.setMaximumWidth(90)
            cap.setFixedHeight(24)
            cap.setToolTip(item['hotkey'])
            cap.setText(cap.fontMetrics().elidedText(item['hotkey'],Qt.TextElideMode.ElideMiddle,76))
            cap.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            top.addWidget(cap,alignment=Qt.AlignmentFlag.AlignTop)
        layout.addLayout(top)
        layout.addSpacing(6)
        name = CardName(item['name'])
        layout.addWidget(name)
        bottom=QHBoxLayout();bottom.setContentsMargins(0,0,0,0);bottom.addStretch()
        edit=button('✎',self.edit.emit,'iconButton');edit.setFixedSize(24,24)
        edit.setIconSize(QSize(15,15));edit.setToolTip('Edit shortcut')
        bottom.addWidget(edit);layout.addLayout(bottom)
        for label in (icon, name):
            label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

    def mousePressEvent(self,event):
        if event.button()==Qt.MouseButton.LeftButton:self.origin=event.position().toPoint()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button()==Qt.MouseButton.LeftButton and self.origin is not None:
            delta=event.position().toPoint()-self.origin;self.origin=None
            if abs(delta.x())>=60 and abs(delta.x())>abs(delta.y()):
                self.swipe.emit(1 if delta.x()<0 else -1);return
            if delta.manhattanLength()>10:return
        if event.button() == Qt.MouseButton.RightButton:
            self.edit.emit()
        elif event.button() == Qt.MouseButton.LeftButton and self.rect().contains(event.position().toPoint()):
            self.launch.emit()

    def keyPressEvent(self,event):
        if event.key() in (Qt.Key.Key_Return,Qt.Key.Key_Enter,Qt.Key.Key_Space):
            self.launch.emit()
        else:
            super().keyPressEvent(event)
