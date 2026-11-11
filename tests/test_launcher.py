"""Functional checks in an isolated folder; never edits the user's configuration."""
import ctypes
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1]
TEMP = tempfile.TemporaryDirectory(prefix='aeri-test-')
ROOT = Path(TEMP.name)
for name in ('main.py', 'storage.py', 'widgets.py', 'editor.py', 'launcher.py', 'shortcuts.py', 'windows_effects.py', 'keybindings.py', 'settings_dialog.py', 'runtime.py', 'integration.py', 'installer.py','paging.py','order_dialog.py','app_picker.py','app_discovery.py'):
    shutil.copy2(SOURCE / name, ROOT / name)
for name in ('icons','assets'):
    shutil.copytree(SOURCE / name, ROOT / name)
sys.path.insert(0, str(ROOT))
import main
from PySide6.QtCore import Qt, QCoreApplication, QEvent
from PySide6.QtGui import QPixmap, QImage, QPainter, QShortcut, QKeyEvent, QKeySequence
from PySide6.QtWidgets import QApplication, QMessageBox, QPushButton, QLabel, QSlider
from PySide6.QtTest import QTest
import launcher as launcher_module
from keybindings import GlobalHotkey, normalize_key, native_combination
from types import SimpleNamespace


class LauncherTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setStyle('Fusion')
        cls.app.setStyleSheet(main.STYLE)
        cls.errors = []
        cls.old_hook = sys.excepthook
        sys.excepthook = lambda *info: cls.errors.append(info)

    def setUp(self):
        self.errors.clear()
        import shortcuts
        self.real_windows=shortcuts._windows
        self.real_capture=shortcuts._schedule_reuse_capture
        self.windows_patch=patch('shortcuts._windows',return_value=[])
        self.windows_mock=self.windows_patch.start();self.addCleanup(self.windows_patch.stop)
        capture_patch=patch('shortcuts._schedule_reuse_capture')
        capture_patch.start();self.addCleanup(capture_patch.stop)
        shortcuts._WINDOW_BINDINGS.clear();shortcuts._STARTING.clear();shortcuts._LINK_CACHE.clear()
        self.entries = [
            dict(name='Explorer', type='app', path='explorer.exe', category='Sistem', icon='auto', hotkey='E'),
            dict(name='Folder contoh', type='folder', path=str(ROOT), category='Pribadi', icon='auto', hotkey='F'),
            dict(name='Website contoh', type='website', path='https://example.org', category='Pribadi', icon='auto', hotkey='W')]
        (ROOT / 'apps.json').write_text(json.dumps(self.entries), encoding='utf-8')
        (ROOT / 'settings.json').write_text(json.dumps(dict(global_hotkey='Alt+Z',autostart=False)), encoding='utf-8')
        self.window = main.Launcher()
        self.window.show()
        self.app.processEvents()
        self.window.reload()

    def tearDown(self):
        for widget in list(self.app.topLevelWidgets()):
            try:
                widget.close()
                widget.deleteLater()
            except RuntimeError:
                pass
        self.app.processEvents()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        self.assertFalse(self.errors, self.errors)

    @classmethod
    def tearDownClass(cls):
        sys.excepthook = cls.old_hook
        TEMP.cleanup()

    def test_layout_icons_and_shortcuts(self):
        self.assertEqual(len(self.window.items), 3)
        self.assertTrue(self.window.loaded)
        self.assertEqual(self.window._columns, 4)
        self.window.resize(700,500)
        self.app.processEvents()
        self.assertEqual(self.window._columns, 4)
        self.assertFalse(any('Tes blur' in b.text() for b in self.window.findChildren(QPushButton)))
        keys = {s.key().toString() for s in self.window.findChildren(QShortcut)}
        self.assertTrue({'Ctrl+F','Ctrl+N','Ctrl+R'} <= keys)
        self.assertFalse(main.shortcut_icon(self.entries[0]).isNull())
        for name in ('whatsapp','google-drive','pinterest'):
            self.assertFalse(QPixmap(str(ROOT / 'icons' / (name+'.png'))).isNull())

    def test_native_alpha_surface(self):
        self.assertFalse(self.window.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground))
        self.assertTrue(self.window.windowFlags() & Qt.WindowType.FramelessWindowHint)
        self.assertEqual(self.window.windowOpacity(),1)
        self.assertTrue(self.window.glass_ok)
        surface=QImage(self.window.size(),QImage.Format.Format_ARGB32_Premultiplied)
        surface.fill(Qt.GlobalColor.transparent)
        for _ in range(30):
            painter=QPainter(surface)
            self.window.paint_glass(painter)
            painter.end()
            self.assertEqual(surface.pixelColor(500,400).alpha(),13)

    def test_fixed_glass_popups(self):
        self.window.edit(self.window.items[0])
        editor=self.window.editor
        self.assertEqual(editor.tint,5)
        self.assertFalse(editor.findChildren(QSlider))
        editor.close();self.app.processEvents()
        self.window.show_settings();dialog=self.window.settings_dialog
        self.assertEqual(dialog.tint,5)
        self.assertFalse(dialog.findChildren(QSlider))
        for panel in (self.window,dialog):
            surface=QImage(panel.size(),QImage.Format.Format_ARGB32_Premultiplied)
            surface.fill(Qt.GlobalColor.transparent)
            for _ in range(10):
                painter=QPainter(surface);panel.paint_glass(painter);painter.end()
            self.assertEqual(surface.pixelColor(panel.width()//2,panel.height()//2).alpha(),13)

    def test_uniform_icon_artwork_and_high_dpi(self):
        from widgets import normalized_icon
        from PySide6.QtGui import QIcon,QBitmap,QRegion,QColor
        for size,art in [(16,(2,2,12,12)),(256,(100,100,20,20)),(300,(0,120,300,60))]:
            source=QPixmap(size,size);source.fill(Qt.GlobalColor.transparent)
            painter=QPainter(source);painter.fillRect(*art,QColor('cyan'));painter.end()
            for dpr in (1,2):
                result=normalized_icon(QIcon(source),dpr=dpr)
                self.assertEqual(result.size().width(),48*dpr)
                self.assertEqual(result.devicePixelRatio(),dpr)
                mask=result.toImage().createAlphaMask(Qt.ImageConversionFlag.ThresholdAlphaDither)
                bounds=QRegion(QBitmap.fromImage(mask)).boundingRect()
                self.assertEqual(max(bounds.width(),bounds.height()),40*dpr)
                self.assertLessEqual(abs((bounds.left()+bounds.right()+1)/2-result.width()/2),1)
                self.assertLessEqual(abs((bounds.top()+bounds.bottom()+1)/2-result.height()/2),1)

    def test_card_alignment_branding_and_long_names(self):
        from widgets import Card,CardName
        self.assertEqual(self.window.windowTitle(),'AERI')
        self.window.show_launcher();self.app.processEvents()
        cards=[card for card in self.window.host.findChildren(Card) if card.isVisible()]
        heights={card.height() for card in cards}
        self.assertEqual(heights,{120})
        self.assertEqual({card.findChild(QLabel,'appLogo').width() for card in cards},{40})
        self.assertEqual({card.findChild(CardName).height() for card in cards},{22})
        self.assertEqual(len({card.findChild(CardName).pos().y() for card in cards}),1)
        self.window.items[0]['name']='Aplikasi dengan nama sangat panjang untuk menguji susunan yang rapi dan sejajar'
        self.window.render_cards();self.app.processEvents()
        title=next(card.findChild(CardName) for card in self.window.host.findChildren(Card) if card.isVisible())
        self.assertEqual(title.height(),22)
        self.assertTrue(title.toolTip())

    def test_search_categories_and_empty_state(self):
        self.window.search.setText('WEBSITE')
        self.assertEqual([i['name'] for i in self.window.visible],['Website contoh'])
        self.window.search.clear()
        self.window.categories.setCurrentText('Sistem')
        self.assertEqual(len(self.window.visible),1)
        self.window.search.setText('not-present')
        self.assertFalse(self.window.visible)
        self.window.reset_filters()
        self.assertEqual(len(self.window.visible),3)
        main.save_items([])
        self.window.reload()
        self.assertTrue(self.window.loaded)
        self.assertFalse(self.window.visible)
        self.window.edit()
        self.assertTrue(self.window.editor.isVisible())

    def test_add_edit_custom_icon_and_delete(self):
        self.window.edit()
        editor=self.window.editor
        editor.save()
        self.assertIn('wajib',editor.error.text())
        editor.name.setText('Shortcut uji')
        editor.kind.setCurrentIndex(editor.kind.findData('folder'))
        editor.path.setText(str(ROOT / 'does-not-exist'))
        editor.save()
        self.assertIn('Folder tidak ditemukan',editor.error.text())
        editor.path.setText(str(ROOT))
        editor.category.setText('Pengujian')
        image=QPixmap(50,50)
        image.fill(Qt.GlobalColor.green)
        image.save(str(ROOT/'source-icon.png'))
        editor.icon_path.setText(str(ROOT/'source-icon.png'))
        editor.save()
        self.app.processEvents()
        self.assertEqual(len(self.window.items),4)
        saved=self.window.items[-1]
        self.assertTrue((ROOT/saved['icon_path']).is_file())
        (ROOT/'source-icon.png').unlink()
        self.assertFalse(main.shortcut_icon(saved).isNull())
        self.assertEqual(len(json.loads((ROOT/'apps.json.bak').read_text())),3)
        before=set((ROOT/'icons').iterdir())
        self.window.edit(saved)
        editor=self.window.editor
        editor.name.setText('Nama diganti')
        editor.save()
        self.app.processEvents()
        self.assertEqual(self.window.items[-1]['name'],'Nama diganti')
        self.assertEqual(set((ROOT/'icons').iterdir()),before)
        self.window.edit(self.window.items[-1])
        with patch.object(main.QMessageBox,'question',return_value=QMessageBox.StandardButton.No):
            self.window.editor.delete()
        self.assertEqual(len(self.window.items),4)
        with patch.object(main.QMessageBox,'question',return_value=QMessageBox.StandardButton.Yes):
            self.window.editor.delete()
        self.assertEqual(len(main.load_shortcuts()),3)

    def test_web_validation_and_browse(self):
        self.window.edit()
        editor=self.window.editor
        editor.name.setText('Web baru')
        editor.kind.setCurrentIndex(editor.kind.findData('website'))
        self.assertFalse(editor.args.isEnabled())
        editor.path.setText('javascript:alert(1)')
        editor.save()
        self.assertIn('URL',editor.error.text())
        editor.path.setText('https://example.org/path')
        editor.save()
        self.app.processEvents()
        self.assertEqual(self.window.items[-1]['type'],'website')
        self.window.edit()
        editor=self.window.editor
        editor.kind.setCurrentIndex(editor.kind.findData('folder'))
        with patch.object(main.QFileDialog,'getExistingDirectory',return_value=str(ROOT)):
            editor.browse_target()
        self.assertEqual(editor.path.text(),str(ROOT))
        self.assertTrue(editor.name.text())

    def test_clean_layout_and_fixed_glass(self):
        self.window.show_launcher();self.app.processEvents()
        self.assertFalse(self.window.findChildren(QSlider))
        text=' '.join(label.text() for label in self.window.findChildren(QLabel))
        for forbidden in ('RUANG KERJA','Aplikasi Anda','Blur Windows','dari 3','Kepekatan'):
            self.assertNotIn(forbidden,text)
        self.assertEqual(self.window.tint,5)
        center=self.window.search.mapTo(self.window,self.window.search.rect().center()).x()
        self.assertLessEqual(abs(center-self.window.width()/2),3)
        self.assertFalse(self.window.search.hasFocus())

    def test_supplied_application_logo(self):
        from widgets import app_icon
        image=QImage(str(ROOT/'assets/app.png'))
        self.assertFalse(image.isNull())
        self.assertTrue(image.hasAlphaChannel())
        self.assertEqual(image.pixelColor(0,0).alpha(),0)
        for size in (16,32,48,256):
            pixmap=app_icon().pixmap(size,size)
            self.assertFalse(pixmap.isNull())
            self.assertAlmostEqual(pixmap.width()/pixmap.devicePixelRatio(),size,delta=1)
        self.assertFalse(app_icon('settings').isNull())

    def test_local_keys_search_and_escape(self):
        self.window.show_launcher();self.app.processEvents()
        with patch.object(launcher_module,'open_shortcut') as launch:
            QTest.keyClick(self.window,Qt.Key.Key_W)
            launch.assert_called_once()
            self.assertEqual(launch.call_args.args[0]['name'],'Website contoh')
        self.assertFalse(self.window.isVisible())
        self.window.show_launcher();self.window.focus_search();self.app.processEvents()
        with patch.object(launcher_module,'open_shortcut') as launch:
            QTest.keyClick(self.window.search,Qt.Key.Key_W)
            launch.assert_not_called()
        self.assertEqual(self.window.search.text().casefold(),'w')
        QTest.keyClick(self.window.search,Qt.Key.Key_Escape)
        self.assertEqual(self.window.search.text(),'')
        self.assertTrue(self.window.isVisible())
        QTest.keyClick(self.window,Qt.Key.Key_Escape)
        self.assertFalse(self.window.isVisible())

    def test_duplicate_and_reserved_local_keys(self):
        self.window.edit();editor=self.window.editor
        editor.name.setText('Shortcut baru');editor.path.setText('explorer.exe')
        editor.hotkey.setKeySequence(QKeySequence('W'));editor.save()
        self.assertIn('sudah dipakai',editor.error.text())
        editor.hotkey.setKeySequence(QKeySequence('Ctrl+F'));editor.save()
        self.assertIn('navigasi',editor.error.text())
        editor.hotkey.setKeySequence(QKeySequence('Alt+Z'));editor.save()
        self.assertIn('membuka launcher',editor.error.text())
        editor.hotkey.setKeySequence(QKeySequence('Q'));editor.save()
        self.assertEqual(self.window.items[-1]['hotkey'],'Q')
        with self.assertRaises(ValueError):normalize_key('Z',global_key=True)
        with self.assertRaises(ValueError):normalize_key('Ctrl+F12',global_key=True)
        self.assertEqual(normalize_key('w'),'W')
        self.assertEqual(native_combination('Alt+Z'),(0x4001,90))

    def test_global_registration_conflict_and_rollback(self):
        class FakeUser:
            def __init__(self):self.keys={};self.allow=True
            def RegisterHotKey(self,hwnd,id,mods,vk):
                if not self.allow:return False
                self.keys[id]=(mods,vk);return True
            def UnregisterHotKey(self,hwnd,id):self.keys.pop(id,None);return True
        user=FakeUser();manager=GlobalHotkey(self.app,int(self.window.winId()),user=user)
        try:
            manager.replace('Alt+Z');old=manager.active_id
            def failed():raise OSError('disk failure')
            with self.assertRaises(OSError):manager.replace('Alt+X',failed)
            self.assertEqual(manager.sequence,'Alt+Z');self.assertEqual(set(user.keys),{old})
            user.allow=False
            with self.assertRaises(ValueError):manager.replace('Alt+X')
            self.assertEqual(set(user.keys),{old})
            user.allow=True;manager.replace('Alt+X')
            self.assertEqual(manager.sequence,'Alt+X');self.assertEqual(len(user.keys),1)
        finally:manager.close()
        self.assertFalse(user.keys)

    def test_global_settings_dialog(self):
        from storage import save_settings,load_settings
        self.window.controller=SimpleNamespace(configure=lambda value:save_settings(value))
        self.window.show_settings();dialog=self.window.settings_dialog
        dialog.hotkey.setKeySequence(QKeySequence('Alt+X'));dialog.save()
        self.assertEqual(load_settings()['global_hotkey'],'Alt+X')
        self.assertEqual(self.window.preferences['global_hotkey'],'Alt+X')

    def test_global_settings_rejects_navigation_shortcuts(self):
        for key in ('Ctrl+F','Ctrl+N','Ctrl+R','Ctrl+,','Ctrl+Left','Ctrl+Right'):
            with self.subTest(key=key),self.assertRaisesRegex(ValueError,'navigasi'):
                normalize_key(key,global_key=True)
        self.assertEqual(normalize_key('Ctrl+Space',global_key=True),'Ctrl+Space')

    def test_settings_validation_error_clears_after_edit(self):
        self.window.controller=SimpleNamespace(configure=lambda value:None)
        self.window.show_settings();dialog=self.window.settings_dialog
        before=(ROOT/'settings.json').read_bytes()
        dialog.hotkey.setKeySequence(QKeySequence('Ctrl+F'));dialog.save()
        self.assertTrue(dialog.isVisible());self.assertTrue(dialog.error.isVisible())
        self.assertIn('navigasi',dialog.error.text())
        self.assertEqual((ROOT/'settings.json').read_bytes(),before)
        dialog.hotkey.setKeySequence(QKeySequence('Alt+X'))
        self.assertEqual(dialog.error.text(),'');self.assertFalse(dialog.error.isVisible())

    def test_settings_failed_apply_keeps_previous_preferences(self):
        def fail(values):raise OSError('Tidak dapat menyimpan pengaturan')
        self.window.controller=SimpleNamespace(configure=fail)
        before=dict(self.window.preferences);disk=(ROOT/'settings.json').read_bytes()
        self.window.show_settings();dialog=self.window.settings_dialog
        dialog.hotkey.setKeySequence(QKeySequence('Alt+X'));dialog.save()
        self.assertTrue(dialog.isVisible());self.assertIn('Tidak dapat menyimpan',dialog.error.text())
        self.assertEqual(self.window.preferences,before)
        self.assertEqual((ROOT/'settings.json').read_bytes(),disk)

    def test_settings_startup_availability_matches_execution_mode(self):
        for frozen in (False,True):
            with self.subTest(frozen=frozen),patch('settings_dialog.sys',SimpleNamespace(frozen=frozen)):
                self.window.show_settings();dialog=self.window.settings_dialog
                self.assertEqual(dialog.startup.isEnabled(),frozen)
                if not frozen:
                    self.assertIn('AERI.exe',dialog.startup.toolTip())
                    self.assertIn('khusus EXE',dialog.startup.text())
                dialog.close();self.app.processEvents()

    def test_source_settings_preserves_existing_startup_preference(self):
        from storage import save_settings
        self.window.preferences['autostart']=True
        self.window.controller=SimpleNamespace(configure=save_settings)
        with patch('settings_dialog.sys',SimpleNamespace(frozen=False)):
            self.window.show_settings();dialog=self.window.settings_dialog
            self.assertFalse(dialog.startup.isEnabled());self.assertTrue(dialog.startup.isChecked())
            dialog.hotkey.setKeySequence(QKeySequence('Alt+X'));dialog.save()
        self.assertTrue(self.window.preferences['autostart'])

    @unittest.skipUnless(sys.platform=='win32','Windows integration')
    def test_native_hotkey_and_message_filter(self):
        from ctypes import wintypes
        manager=GlobalHotkey(self.app,int(self.window.winId()))
        received=[];manager.activated.connect(lambda:received.append(True))
        try:
            try:manager.replace('Ctrl+Alt+Shift+F10')
            except ValueError:
                if ctypes.get_last_error()==5:self.skipTest('Sandbox denies RegisterHotKey (Windows error 5)')
                raise
            message=wintypes.MSG();message.message=0x0312;message.wParam=manager.active_id
            self.assertEqual(manager.filter.nativeEventFilter(b'windows_generic_MSG',ctypes.addressof(message)),(True,0))
            self.assertEqual(received,[True])
            message.wParam=1
            self.assertEqual(manager.filter.nativeEventFilter(b'windows_generic_MSG',ctypes.addressof(message)),(False,0))
        finally:manager.close()

    @unittest.skipUnless(sys.platform=='win32','Windows integration')
    def test_windows_shortcut_creation(self):
        from integration import _link
        link=ROOT/"contoh shortcut ' pribadi.lnk"
        _link(link,ROOT/'AERI.exe','--background')
        self.assertGreater(link.stat().st_size,0)
        _link(link,ROOT/'AERI.exe',remove=True)
        self.assertFalse(link.exists())

    def test_autostart_and_setting_rollback(self):
        from runtime import RuntimeController
        fake=SimpleNamespace(window=self.window,hotkey=SimpleNamespace(replace=lambda key,persist:persist()),update_label=lambda:None)
        with patch('runtime.set_autostart') as startup,patch('runtime.save_settings',side_effect=OSError('full')):
            with self.assertRaises(OSError):RuntimeController.configure(fake,{'global_hotkey':'Alt+X','autostart':True})
            self.assertEqual([c.args for c in startup.call_args_list],[(True,),(False,)])

    def test_install_copy_preserves_user_data(self):
        from installer import copy_install
        source=ROOT/'install-source';source.mkdir(exist_ok=True)
        (source/'program.exe').write_bytes(b'test executable fixture')
        (source/'apps.json').write_text('[]');(source/'settings.json').write_text('{}')
        (source/'icons').mkdir(exist_ok=True);(source/'icons/a.png').write_bytes(b'fixture')
        (source/'assets').mkdir(exist_ok=True)
        (source/'assets/app.ico').write_bytes((ROOT/'assets/app.ico').read_bytes())
        destination=ROOT/'installed'
        copy_install(source/'program.exe',source,destination)
        (destination/'apps.json').write_text('["keep"]')
        copy_install(source/'program.exe',source,destination)
        self.assertEqual((destination/'apps.json').read_text(),'["keep"]')
        self.assertTrue((destination/'icons/a.png').is_file())
        self.assertEqual((destination/'AERI.ico').read_bytes(),(ROOT/'assets/app.ico').read_bytes())

    def populate_many(self,count):
        self.window.items=[dict(name=f'App {i:02}',type='app',path='explorer.exe',icon='auto',category='Aplikasi',hotkey='',args=[str(i)]) for i in range(count)]
        self.window.render_cards();self.app.processEvents()

    def test_twelve_items_per_page_without_vertical_scroll(self):
        from widgets import Card
        from PySide6.QtWidgets import QScrollArea
        self.assertFalse(self.window.findChildren(QScrollArea))
        for count in (0,1,12,13,24,25):
            self.populate_many(count)
            self.assertEqual(len(self.window.pager.pages),max(1,(count+11)//12))
            for index,page in enumerate(self.window.pager.pages):
                self.window.pager.go(index,animate=False);self.app.processEvents()
                cards=page.findChildren(Card)
                self.assertEqual(len(cards),min(12,max(0,count-index*12)))
                for card in cards:self.assertTrue(page.rect().contains(card.geometry()),(count,card.geometry(),page.rect()))
                if len(cards)==12:
                    self.assertEqual(len({c.x() for c in cards}),4)
                    self.assertEqual(len({c.y() for c in cards}),3)
            if count>12:
                first=self.window.pager.pages[0].findChildren(Card)[0]
                last=self.window.pager.pages[-1].findChildren(Card)[0]
                self.assertEqual(first.width(),last.width())
        self.window.resize(800,600);self.app.processEvents()
        page=self.window.pager.pages[self.window.pager.current_index]
        for card in page.findChildren(Card):self.assertTrue(page.rect().contains(card.geometry()))

    def test_page_navigation_animation_and_search_reset(self):
        self.populate_many(25)
        self.assertFalse(self.window.previous.isEnabled());self.assertTrue(self.window.next.isEnabled())
        self.assertTrue(self.window.change_page(1));self.assertFalse(self.window.change_page(1))
        QTest.qWait(260);self.assertEqual(self.window.pager.current_index,1)
        self.assertTrue(self.window.change_page(1));QTest.qWait(260)
        self.assertEqual(self.window.page_label.text(),'3 / 3');self.assertFalse(self.window.next.isEnabled())
        self.window.search.setText('App 00');self.app.processEvents()
        self.assertEqual(self.window.pager.current_index,0);self.assertEqual(len(self.window.pager.pages),1)
        self.window.reset_filters();self.assertEqual(len(self.window.pager.pages),3)

    def test_one_wheel_gesture_moves_one_page(self):
        from PySide6.QtGui import QWheelEvent
        from PySide6.QtCore import QPoint,QPointF
        self.populate_many(36)
        def wheel():return QWheelEvent(QPointF(100,100),QPointF(100,100),QPoint(),QPoint(0,-120),Qt.MouseButton.NoButton,Qt.KeyboardModifier.NoModifier,Qt.ScrollPhase.NoScrollPhase,False)
        for _ in range(12):self.window.wheel_page(wheel())
        self.assertEqual(self.window.pager.current_index,1)
        self.window.pager.finish();self.window.reset_wheel();self.window.wheel_page(wheel())
        self.assertEqual(self.window.pager.current_index,2)

    def test_swipe_does_not_launch_and_edit_below_name(self):
        from PySide6.QtCore import QPoint
        from widgets import Card,CardName
        self.populate_many(13)
        card=self.window.pager.pages[0].findChildren(Card)[0]
        title=card.findChild(CardName)
        edit=next(b for b in card.findChildren(QPushButton) if b.toolTip()=='Edit shortcut')
        self.assertGreater(edit.mapTo(card,QPoint()).y(),title.y())
        keycap=card.findChild(QLabel,'keycap')
        with patch.object(launcher_module,'open_shortcut') as launch:
            QTest.mousePress(card,Qt.MouseButton.LeftButton,pos=QPoint(card.width()-15,30))
            QTest.mouseRelease(card,Qt.MouseButton.LeftButton,pos=QPoint(10,30))
            launch.assert_not_called()
        self.assertEqual(self.window.pager.current_index,1)

    def test_reorder_crosses_page_boundary_and_persists(self):
        self.populate_many(14);main.save_items(self.window.items)
        before=[dict(i) for i in self.window.items]
        self.window.show_order();dialog=self.window.order_dialog
        dialog.list.setCurrentRow(12);dialog.move_row(-1);dialog.save();self.app.processEvents()
        values=main.load_shortcuts()
        self.assertEqual(values[11],before[12]);self.assertEqual(values[12],before[11])
        self.window.reload();self.assertEqual(self.window.items[11]['args'],['12'])
        self.window.show_order();dialog=self.window.order_dialog;dialog.list.setCurrentRow(0);dialog.move_row(1)
        disk=(ROOT/'apps.json').read_bytes()
        with patch('order_dialog.save_items',side_effect=OSError('full')):dialog.save()
        self.assertTrue(dialog.isVisible());self.assertIn('full',dialog.error.text())
        self.assertEqual((ROOT/'apps.json').read_bytes(),disk)

    def test_chrome_shortcut_and_store_discovery(self):
        from app_discovery import discover_apps,store_entries
        folder=ROOT/'Chrome Apps';folder.mkdir(exist_ok=True)
        path=folder/'Google Drive.lnk';path.write_bytes(b'fixture')
        entries=discover_apps([folder],include_store=False)
        self.assertEqual(entries[0]['path'],str(path));self.assertEqual(entries[0]['category'],'Aplikasi web')
        self.window.edit();editor=self.window.editor;editor.use_installed(entries[0]);editor.save()
        selected=self.window.items[-1];self.assertEqual(selected['args'],[])
        with patch.object(main.os,'startfile') as start:
            from shortcuts import open_shortcut
            open_shortcut(selected);start.assert_called_once_with(str(path.resolve()))
        rows=store_entries([{'name':'ChatGPT','id':'Vendor.ChatGPT_abc!App','icon_path':''},{'name':'Bad','id':'bad shell argument'}])
        self.assertEqual(len(rows),1);self.assertEqual(rows[0]['args'],['shell:AppsFolder\\Vendor.ChatGPT_abc!App'])
        self.assertEqual(rows[0]['icon'],'initial')

    def test_installed_app_picker_selection(self):
        fixture=ROOT/'Visual Studio Code.lnk';fixture.write_bytes(b'test fixture')
        entries=[dict(name='Visual Studio Code',type='app',path=str(fixture),args=[],category='Aplikasi',icon='auto',source='Shortcut Windows')]
        self.window.edit();editor=self.window.editor
        with patch('app_discovery.discover_apps',return_value=entries):
            editor.pick_installed();QTest.qWait(100)
        picker=editor.picker;picker.search.setText('Code');self.assertEqual(picker.list.count(),1)
        picker.choose();self.app.processEvents()
        self.assertEqual(editor.name.text(),'Visual Studio Code');self.assertEqual(editor.path.text(),str(fixture))
        editor.save();self.assertEqual(self.window.items[-1]['name'],'Visual Studio Code')

    def test_busy_install_reports_failure(self):
        with patch.object(sys,'argv',['AERI.exe','--install']),patch('installer.install_application',side_effect=PermissionError('EXE masih dipakai')),patch.object(main.QMessageBox,'warning') as warning:
            self.assertEqual(main.main(),1)
            self.assertIn('Keluar',warning.call_args.args[2])

    def test_failed_saves_preserve_files_and_remove_import(self):
        before=(ROOT/'apps.json').read_bytes()
        self.window.edit()
        editor=self.window.editor
        editor.name.setText('Gagal simpan')
        editor.path.setText('explorer.exe')
        image=QPixmap(32,32)
        image.fill(Qt.GlobalColor.blue)
        image.save(str(ROOT/'fail-icon.png'))
        editor.icon_path.setText(str(ROOT/'fail-icon.png'))
        icons=set((ROOT/'icons').iterdir())
        with patch.object(main.os,'replace',side_effect=OSError('simulated save failure')):
            editor.save()
        self.assertIn('simulated',editor.error.text())
        self.assertEqual((ROOT/'apps.json').read_bytes(),before)
        self.assertEqual(set((ROOT/'icons').iterdir()),icons)
        self.assertFalse(list(ROOT.glob('*.tmp')))
        editor.close()
        from storage import save_settings
        before=(ROOT/'settings.json').read_bytes()
        with patch.object(main.os,'replace',side_effect=OSError('settings failure')):
            with self.assertRaises(OSError):save_settings({'global_hotkey':'Alt+X','autostart':False})
        self.assertEqual((ROOT/'settings.json').read_bytes(),before)

    def test_launch_dispatch_and_errors(self):
        with patch.object(main.subprocess,'Popen') as popen:
            item=dict(self.entries[0],args=['--profile-directory=Profile 1'])
            self.window.launch(item)
            self.assertEqual(popen.call_args.args[0][1:],['--profile-directory=Profile 1'])
            self.assertFalse(popen.call_args.kwargs['shell'])
        folder=ROOT/'local-data'
        folder.mkdir(exist_ok=True)
        shortcut=ROOT/'test.lnk'
        shortcut.touch()
        with patch.object(main.os,'startfile') as start:
            self.window.launch(dict(self.entries[1],path='local-data'))
            start.assert_called_with(str(folder))
            self.window.launch(dict(self.entries[0],path=str(shortcut)))
            start.assert_called_with(str(shortcut))
            self.window.launch(dict(self.entries[0],path='whatsapp:'))
            start.assert_called_with('whatsapp:')
        with patch.object(main.QDesktopServices,'openUrl',return_value=True) as browser:
            self.window.launch(self.entries[2])
            self.assertEqual(browser.call_args.args[0].toString(),'https://example.org')
        with patch.object(main.QMessageBox,'warning') as warning:
            self.window.launch(dict(self.entries[2],path='javascript:alert(1)'))
            warning.assert_called_once()
        with patch.object(main.QMessageBox,'warning') as warning:
            self.window.launch(dict(self.entries[0],path=str(ROOT/'missing.exe')))
            warning.assert_called_once()

    def app_window(self,hwnd,exe,aumid='',command='',title='Application'):
        return dict(hwnd=hwnd,pid=hwnd+100,exe=str(exe),aumid=aumid,command=command,title=title)

    def app_fixture(self,name='program.exe',args=None):
        target=ROOT/name;target.touch()
        return dict(name='Application',type='app',path=str(target),args=args or [],icon='auto',category='Aplikasi')

    def test_existing_executable_is_activated_without_spawning(self):
        from shortcuts import open_shortcut
        item=self.app_fixture();window=self.app_window(101,item['path'])
        self.windows_mock.return_value=[window]
        with patch('shortcuts._activate_window',return_value=True) as activate,patch.object(main.subprocess,'Popen') as spawn:
            open_shortcut(item);activate.assert_called_once_with(101);spawn.assert_not_called()

    def test_failed_focus_never_creates_duplicate_window(self):
        item=self.app_fixture();self.windows_mock.return_value=[self.app_window(101,item['path'])]
        with patch('shortcuts._activate_window',return_value=False),patch.object(main.subprocess,'Popen') as spawn,patch.object(main.QMessageBox,'warning') as warning:
            self.assertFalse(self.window.launch(item));spawn.assert_not_called()
            self.assertTrue(self.window.isVisible());self.assertIn('sudah terbuka',warning.call_args.args[2])

    def test_minimized_window_and_owned_popup_are_restored(self):
        from shortcuts import _activate_window
        from unittest.mock import Mock
        api=Mock();api.GetLastActivePopup.return_value=202;api.IsWindowVisible.return_value=True
        api.IsIconic.return_value=True;api.SetForegroundWindow.return_value=True
        with patch('shortcuts.ctypes.WinDLL',return_value=api):self.assertTrue(_activate_window(101))
        api.ShowWindowAsync.assert_called_once_with(202,9)
        api.SetForegroundWindow.assert_called_once_with(202)

    def test_chrome_profiles_do_not_focus_each_other(self):
        from shortcuts import open_shortcut
        item=self.app_fixture('chrome.exe',['--profile-directory=Profile 1'])
        self.windows_mock.return_value=[self.app_window(101,item['path'],'Chrome'),self.app_window(202,item['path'],'Chrome.UserData.Profile1')]
        with patch('shortcuts._activate_window',return_value=True) as activate,patch.object(main.subprocess,'Popen') as spawn:
            open_shortcut(item);activate.assert_called_once_with(202);spawn.assert_not_called()
        self.windows_mock.return_value=[self.app_window(101,item['path'],'Chrome')]
        with patch('shortcuts._activate_window') as activate,patch.object(main.subprocess,'Popen') as spawn:
            open_shortcut(item);activate.assert_not_called();spawn.assert_called_once()

    def test_generic_chrome_reuses_browser_but_not_web_app(self):
        from shortcuts import open_shortcut
        item=self.app_fixture('chrome.exe')
        self.windows_mock.return_value=[self.app_window(301,item['path'],'Chrome._crx_drive'),self.app_window(202,item['path'],'Chrome.UserData.Profile1')]
        with patch('shortcuts._activate_window',return_value=True) as activate,patch.object(main.subprocess,'Popen') as spawn:
            open_shortcut(item);activate.assert_called_once_with(202);spawn.assert_not_called()

    def test_chrome_web_app_identity_and_profile(self):
        from shortcuts import open_shortcut
        item=self.app_fixture('chrome.exe',['--profile-directory=Default','--app-id=drive123'])
        self.windows_mock.return_value=[self.app_window(101,item['path'],'Chrome'),
            self.app_window(202,item['path'],'Chrome._crx_drive123.UserData.Profile1'),
            self.app_window(303,item['path'],'Chrome._crx_drive123')]
        with patch('shortcuts._activate_window',return_value=True) as activate,patch.object(main.subprocess,'Popen') as spawn:
            open_shortcut(item);activate.assert_called_once_with(303);spawn.assert_not_called()

    def test_web_app_id_falls_back_to_native_identity(self):
        from shortcuts import _matches
        target=dict(kind='app',exe='C:/Apps/chrome.exe',args=['--profile-directory=Default','--app-id=drive123'],aumid='Chrome._crx_drive123')
        window=self.app_window(101,target['exe'],'Chrome._crx_drive123','C:/Apps/chrome.exe --profile-directory=Default --app=https://drive.google.com/')
        self.assertTrue(_matches(window,target))

    def test_chrome_account_url_uses_exact_relaunch_metadata(self):
        from shortcuts import open_shortcut
        item=self.app_fixture('chrome.exe',['--profile-directory=Default','--app=https://drive.google.com/drive/u/3/my-drive'])
        wrong='"'+item['path']+'" --profile-directory=Default --app=https://drive.google.com/drive/u/0/my-drive'
        exact='"'+item['path']+'" '+' '.join(item['args'])
        self.windows_mock.return_value=[self.app_window(101,item['path'],'Chrome.drive',wrong),self.app_window(202,item['path'],'Chrome.drive',exact)]
        with patch('shortcuts._activate_window',return_value=True) as activate,patch.object(main.subprocess,'Popen') as spawn:
            open_shortcut(item);activate.assert_called_once_with(202);spawn.assert_not_called()

    def test_windows_shortcut_resolves_target_and_app_identity(self):
        from shortcuts import open_shortcut
        chrome=self.app_fixture('chrome.exe')['path'];link=ROOT/'Drive installed.lnk';link.touch()
        item=dict(self.entries[0],path=str(link),args=[])
        details=dict(target=chrome,arguments='--profile-directory=Default --app-id=drive123',aumid='Chrome._crx_drive123')
        self.windows_mock.return_value=[self.app_window(101,chrome,'Chrome'),self.app_window(202,chrome,'Chrome._crx_drive123')]
        with patch('shortcuts._link_details',return_value=details),patch('shortcuts._activate_window',return_value=True) as activate,patch.object(main.os,'startfile') as start:
            open_shortcut(item);activate.assert_called_once_with(202);start.assert_not_called()

    def test_store_and_protocol_apps_reuse_correct_window(self):
        from shortcuts import open_shortcut
        item=dict(self.entries[0],args=['shell:AppsFolder\\Vendor.Chat!App'])
        self.windows_mock.return_value=[self.app_window(101,'C:/Windows/ApplicationFrameHost.exe','Vendor.Chat!App')]
        with patch('shortcuts._activate_window',return_value=True) as activate,patch.object(main.subprocess,'Popen') as spawn:
            open_shortcut(item);activate.assert_called_once_with(101);spawn.assert_not_called()
        item=dict(self.entries[0],path='whatsapp:')
        self.windows_mock.return_value=[self.app_window(202,'C:/Apps/WhatsApp.exe','Vendor.WhatsAppDesktop_abc!App')]
        with patch('shortcuts._associated_executable',return_value=''),patch('shortcuts._activate_window',return_value=True) as activate,patch.object(main.os,'startfile') as start:
            open_shortcut(item);activate.assert_called_once_with(202);start.assert_not_called()

    def test_folder_reuse_matches_exact_folder(self):
        from shortcuts import open_shortcut
        folder=ROOT/'reuse-folder';folder.mkdir(exist_ok=True)
        item=dict(self.entries[1],path=str(folder))
        self.windows_mock.return_value=[self.app_window(101,'C:/Windows/explorer.exe'),self.app_window(202,'C:/Windows/explorer.exe')]
        rows=[dict(hwnd=101,path=str(ROOT)),dict(hwnd=202,path=str(folder))]
        with patch('shortcuts._folder_windows',return_value=rows),patch('shortcuts._activate_window',return_value=True) as activate,patch.object(main.os,'startfile') as start:
            open_shortcut(item);activate.assert_called_once_with(202);start.assert_not_called()

    def test_website_reuses_matching_active_page_without_guessing_account(self):
        from shortcuts import open_shortcut
        item=dict(self.entries[2],name='Google Drive',path='https://drive.google.com/')
        self.windows_mock.return_value=[self.app_window(101,'C:/Apps/chrome.exe','Chrome',title='My Drive - Google Drive - Google Chrome')]
        with patch('shortcuts._associated_executable',return_value='C:/Apps/chrome.exe'),patch('shortcuts._activate_window',return_value=True) as activate,patch.object(main.QDesktopServices,'openUrl',return_value=True) as browser:
            open_shortcut(item);activate.assert_called_once_with(101);browser.assert_not_called()
            activate.reset_mock();item['path']='https://drive.google.com/drive/u/3/my-drive'
            open_shortcut(item);activate.assert_not_called();browser.assert_called_once()

    def test_repeated_clicks_while_starting_spawn_only_once(self):
        import shortcuts
        item=self.app_fixture();callbacks=[]
        with patch('shortcuts._schedule_reuse_capture',new=self.real_capture),patch('shortcuts.QTimer.singleShot',side_effect=lambda delay,callback:callbacks.append(callback)),patch.object(main.subprocess,'Popen') as spawn:
            shortcuts.open_shortcut(item);shortcuts.open_shortcut(item)
            self.assertEqual(spawn.call_count,1)
            window=self.app_window(101,item['path']);self.windows_mock.return_value=[window]
            callbacks[0]()
            self.assertIn(shortcuts._item_key(item),shortcuts._WINDOW_BINDINGS)
            with patch('shortcuts._activate_window',return_value=True):shortcuts.open_shortcut(item)
            self.assertEqual(spawn.call_count,1)

    def test_stale_cached_window_is_not_reused(self):
        import shortcuts
        item=self.app_fixture('chrome.exe',['--app=https://drive.google.com/drive/u/3/my-drive'])
        previous=self.app_window(101,item['path'],'Chrome._crx_drive')
        shortcuts._WINDOW_BINDINGS[shortcuts._item_key(item)]=previous
        self.windows_mock.return_value=[dict(previous,pid=999)]
        with patch('shortcuts._activate_window') as activate,patch.object(main.subprocess,'Popen') as spawn:
            shortcuts.open_shortcut(item);activate.assert_not_called();spawn.assert_called_once()

    def test_modified_link_does_not_reuse_old_target_binding(self):
        import shortcuts
        link=ROOT/'mutable.lnk';link.touch()
        item=dict(self.entries[0],path=str(link),args=[])
        key=shortcuts._item_key(item)
        previous=self.app_window(101,'C:/Apps/Old.exe')
        shortcuts._WINDOW_BINDINGS[key]=previous;self.windows_mock.return_value=[previous]
        stat=link.stat();os.utime(link,ns=(stat.st_atime_ns,stat.st_mtime_ns+10000000))
        self.assertNotEqual(shortcuts._item_key(item),key)
        with patch('shortcuts._link_details',return_value=dict(target='C:/Apps/New.exe',arguments='',aumid='')),patch('shortcuts._activate_window') as activate,patch.object(main.os,'startfile') as start:
            shortcuts.open_shortcut(item);activate.assert_not_called();start.assert_called_once_with(str(link))

    def test_web_app_capture_waits_for_stable_identity(self):
        import shortcuts
        item=self.app_fixture('chrome.exe',['--profile-directory=Default','--app=https://drive.google.com/drive/u/3/my-drive'])
        callbacks=[]
        with patch('shortcuts._schedule_reuse_capture',new=self.real_capture),patch('shortcuts.QTimer.singleShot',side_effect=lambda delay,callback:callbacks.append(callback)),patch.object(main.subprocess,'Popen') as spawn:
            shortcuts.open_shortcut(item)
            window=self.app_window(101,item['path']);self.windows_mock.return_value=[window]
            callbacks[0]();self.assertNotIn(shortcuts._item_key(item),shortcuts._WINDOW_BINDINGS)
            window['aumid']='Chrome._crx_drive';callbacks[1]()
            self.assertIn(shortcuts._item_key(item),shortcuts._WINDOW_BINDINGS)
            with patch('shortcuts._activate_window',return_value=True):shortcuts.open_shortcut(item)
            self.assertEqual(spawn.call_count,1)

    def test_custom_chrome_data_directory_needs_exact_metadata(self):
        from shortcuts import _matches
        target=dict(kind='app',exe='C:/Apps/chrome.exe',args=['--profile-directory=Default','--user-data-dir=C:/one/Custom'],aumid='')
        window=self.app_window(101,target['exe'],'Chrome.Custom.Default')
        self.assertFalse(_matches(window,target))

    def test_window_snapshot_reads_own_visible_window(self):
        windows=self.real_windows()
        own=next((w for w in windows if w['hwnd']==int(self.window.winId())),None)
        if own is None:self.skipTest('Desktop window enumeration unavailable in this sandbox')
        self.assertTrue(own['exe'].lower().endswith('python.exe'))

    def test_chrome_default_profile_case_and_private_window(self):
        from shortcuts import _matches
        target=dict(kind='app',exe='C:/Apps/chrome.exe',args=['--profile-directory=default'],aumid='')
        window=self.app_window(101,target['exe'],'Chrome')
        self.assertTrue(_matches(window,target))
        window['command']='C:/Apps/chrome.exe --profile-directory=Default --incognito'
        self.assertFalse(_matches(window,target))

    def test_native_window_identity_property_can_be_read(self):
        import shortcuts as launch
        from ctypes import wintypes
        shell=ctypes.WinDLL('shell32');ole=ctypes.WinDLL('ole32')
        ole.CoInitializeEx.argtypes=[ctypes.c_void_p,wintypes.DWORD];ole.CoInitializeEx.restype=ctypes.c_long
        initialized=ole.CoInitializeEx(None,2)>=0
        shell.SHGetPropertyStoreForWindow.argtypes=[wintypes.HWND,ctypes.POINTER(launch._GUID),ctypes.POINTER(ctypes.c_void_p)]
        shell.SHGetPropertyStoreForWindow.restype=ctypes.c_long
        store=ctypes.c_void_p();release=None;setter=None
        identity=launch._GUID.from_buffer_copy(launch.uuid.UUID('886d8eeb-8cf2-4446-8d02-cdba1dbdcf99').bytes_le)
        key=launch._PROPERTYKEY(launch._GUID.from_buffer_copy(launch.uuid.UUID('9f4c2855-9f79-4b39-a8d0-e1d42de1d5f3').bytes_le),5)
        hwnd=int(self.window.winId());previous=launch._window_properties(hwnd).get('aumid','')
        try:
            if shell.SHGetPropertyStoreForWindow(hwnd,ctypes.byref(identity),ctypes.byref(store))<0:
                self.skipTest('Window property store unavailable in this sandbox')
            table=ctypes.cast(store,ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
            release=ctypes.WINFUNCTYPE(wintypes.ULONG,ctypes.c_void_p)(table[2])
            setter=ctypes.WINFUNCTYPE(ctypes.c_long,ctypes.c_void_p,ctypes.POINTER(launch._PROPERTYKEY),ctypes.POINTER(launch._PROPVARIANT))(table[6])
            value=launch._PROPVARIANT();buffer=ctypes.create_unicode_buffer('AERI.TestWindow')
            value.vt=31;value.value.pointer=ctypes.cast(buffer,ctypes.c_void_p).value
            if setter(store,ctypes.byref(key),ctypes.byref(value))<0:
                self.skipTest('Setting identity on the test window is unavailable')
            self.assertEqual(launch._window_properties(hwnd).get('aumid'),'AERI.TestWindow')
        finally:
            if setter is not None:
                restore=launch._PROPVARIANT();buffer=ctypes.create_unicode_buffer(previous)
                if previous:restore.vt=31;restore.value.pointer=ctypes.cast(buffer,ctypes.c_void_p).value
                setter(store,ctypes.byref(key),ctypes.byref(restore))
            if release is not None:release(store)
            if initialized:ole.CoUninitialize()

    def test_invalid_config_blocks_edit_and_keeps_previous_cards(self):
        (ROOT/'apps.json').write_text('{ broken json',encoding='utf-8')
        with patch.object(main.QMessageBox,'warning') as warning:
            self.window.reload()
            self.assertFalse(self.window.loaded)
            self.window.edit()
            self.assertEqual(warning.call_count,2)
        self.assertEqual(len(self.window.items),3)
        self.assertEqual((ROOT/'apps.json').read_text(),'{ broken json')


if __name__=='__main__':
    unittest.main(verbosity=2)
