import sys
import os
import signal
import requests
from PyQt6.QtWidgets import QApplication, QMainWindow, QLabel, QWidget, QScrollArea, QFileDialog, QMenu, QMessageBox
from PyQt6.QtCore import Qt, QRect, QEvent, QPoint, pyqtSignal
from PyQt6.QtGui import QPainter, QPen, QBrush, QColor, QPixmap, QAction, QIcon
from PyQt6.QtWidgets import QSystemTrayIcon
from pynput import keyboard


# --- 资源路径辅助函数 ---
def resource_path(relative_path):
    """ 获取资源的绝对路径，无论是作为脚本运行还是在打包后运行 """
    try:
        # PyInstaller 创建一个临时文件夹，并将路径存储在 _MEIPASS 中
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


# --- QSS样式表 ---
SCROLL_BAR_STYLE = """
    QScrollBar:vertical, QScrollBar:horizontal { border: none; background: transparent; width: 8px; margin: 0px; }
    QScrollBar::handle:vertical, QScrollBar::handle:horizontal { background: #555; min-height: 20px; min-width: 20px; border-radius: 4px; }
    QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover { background: #777; }
    QScrollBar::add-line, QScrollBar::sub-line { height: 0px; width: 0px; }
    QScrollBar::add-page, QScrollBar::sub-page { background: none; }
"""


# --- 自定义的、支持拖拽和右键菜单的滚动区域 ---
class CustomScrollArea(QScrollArea):
    image_dropped = pyqtSignal(QPixmap)
    context_menu_requested = pyqtSignal(QPoint)

    def __init__(self, parent=None):
        super().__init__(parent);
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls() or event.mimeData().hasImage():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dropEvent(self, event):
        pixmap = None;
        mime_data = event.mimeData()
        if mime_data.hasUrls():
            url = mime_data.urls()[0]
            if url.isLocalFile():
                pixmap = QPixmap(url.toLocalFile())
            else:
                image_url = url.toString()
                print(f"正在从网络下载: {image_url}")
                try:
                    response = requests.get(image_url, timeout=10);
                    response.raise_for_status()
                    pixmap = QPixmap();
                    pixmap.loadFromData(response.content)
                except requests.exceptions.RequestException as e:
                    print(f"错误: 图片下载失败 - {e}")
        elif mime_data.hasImage():
            image_data = mime_data.imageData()
            if image_data: pixmap = QPixmap(); pixmap.loadFromData(image_data)
        if pixmap and not pixmap.isNull(): self.image_dropped.emit(pixmap)
        super().dropEvent(event)

    def contextMenuEvent(self, event):
        self.context_menu_requested.emit(event.globalPos())
        super().contextMenuEvent(event)


# --- PinnedWindow 类 ---
class PinnedWindow(QMainWindow):
    def __init__(self, pixmap: QPixmap, geometry: QRect):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint);
        self.setGeometry(geometry)
        self.setMouseTracking(True);
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        self.original_pixmap = pixmap;
        self.scale_factor = 1.0
        self.image_label = QLabel();
        self.image_label.setPixmap(self.original_pixmap);
        self.image_label.setMouseTracking(True)
        self.scroll_area = CustomScrollArea();
        self.scroll_area.setWidget(self.image_label);
        self.scroll_area.setStyleSheet(SCROLL_BAR_STYLE)
        self.scroll_area.setMouseTracking(True);
        self.scroll_area.setWidgetResizable(True);
        self.scroll_area.viewport().installEventFilter(self)
        self.scroll_area.image_dropped.connect(self.load_new_pixmap);
        self.scroll_area.context_menu_requested.connect(self.show_context_menu)
        self.setCentralWidget(self.scroll_area)
        self.drag_position, self.is_resizing, self.resize_handle = None, False, None
        self.resize_margin = 8;
        self.is_panning = False;
        self.pan_start_pos = QPoint()

    def eventFilter(self, source, event):
        if source != self.scroll_area.viewport(): return super().eventFilter(source, event)
        if event.type() == QEvent.Type.Wheel:
            if event.angleDelta().y() > 0:
                self.scale_factor *= 1.15
            else:
                self.scale_factor *= 0.85
            self.scale_factor = max(0.1, self.scale_factor);
            self.update_image_zoom();
            return True
        if event.type() == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.MiddleButton:
            self.is_panning = True;
            self.pan_start_pos = event.pos();
            self.setCursor(Qt.CursorShape.ClosedHandCursor);
            return True
        if event.type() == QEvent.Type.MouseMove and self.is_panning:
            delta = event.pos() - self.pan_start_pos
            h_bar = self.scroll_area.horizontalScrollBar();
            v_bar = self.scroll_area.verticalScrollBar()
            h_bar.setValue(h_bar.value() - delta.x());
            v_bar.setValue(v_bar.value() - delta.y())
            self.pan_start_pos = event.pos();
            return True
        if event.type() == QEvent.Type.MouseButtonRelease and event.button() == Qt.MouseButton.MiddleButton:
            self.is_panning = False;
            self.setCursor(Qt.CursorShape.ArrowCursor);
            return True
        return super().eventFilter(source, event)

    def update_image_zoom(self):
        scaled_pixmap = self.original_pixmap.scaled(
            int(self.original_pixmap.width() * self.scale_factor),
            int(self.original_pixmap.height() * self.scale_factor),
            Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self.image_label.setPixmap(scaled_pixmap)

    def show_context_menu(self, global_pos):
        context_menu = QMenu(self);
        open_action = QAction("打开本地图片...", self);
        open_action.triggered.connect(self.open_local_image)
        context_menu.addAction(open_action);
        context_menu.addSeparator();
        close_action = QAction("关闭", self)
        close_action.triggered.connect(self.close);
        context_menu.addAction(close_action);
        context_menu.exec(global_pos)

    def open_local_image(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "选择一张图片", "",
                                                   "图片文件 (*.png *.jpg *.jpeg *.bmp *.gif)")
        if file_path: self.load_new_pixmap(QPixmap(file_path))

    def load_new_pixmap(self, pixmap):
        if pixmap.isNull(): return
        self.original_pixmap = pixmap;
        self.scale_factor = 1.0
        self.image_label.setPixmap(self.original_pixmap);
        self.update_image_zoom()

    def _update_resize_cursor(self, pos: QPoint):
        x, y, w, h = pos.x(), pos.y(), self.width(), self.height()
        if not self.is_resizing and not self.is_panning:
            self.resize_handle = None
            if x < self.resize_margin and y < self.resize_margin:
                self.resize_handle = "top-left"; self.setCursor(Qt.CursorShape.SizeFDiagCursor)
            elif x > w - self.resize_margin and y < self.resize_margin:
                self.resize_handle = "top-right"; self.setCursor(Qt.CursorShape.SizeBDiagCursor)
            elif x < self.resize_margin and y > h - self.resize_margin:
                self.resize_handle = "bottom-left"; self.setCursor(Qt.CursorShape.SizeBDiagCursor)
            elif x > w - self.resize_margin and y > h - self.resize_margin:
                self.resize_handle = "bottom-right"; self.setCursor(Qt.CursorShape.SizeFDiagCursor)
            elif x < self.resize_margin:
                self.resize_handle = "left"; self.setCursor(Qt.CursorShape.SizeHorCursor)
            elif x > w - self.resize_margin:
                self.resize_handle = "right"; self.setCursor(Qt.CursorShape.SizeHorCursor)
            elif y < self.resize_margin:
                self.resize_handle = "top"; self.setCursor(Qt.CursorShape.SizeVerCursor)
            elif y > h - self.resize_margin:
                self.resize_handle = "bottom"; self.setCursor(Qt.CursorShape.SizeVerCursor)
            else:
                self.setCursor(Qt.CursorShape.ArrowCursor)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.resize_handle:
                self.is_resizing = True; self.drag_position = event.globalPosition().toPoint()
            else:
                self.is_resizing = False; self.drag_position = event.globalPosition().toPoint() - self.geometry().topLeft()
        event.accept()

    def mouseMoveEvent(self, event):
        self._update_resize_cursor(event.pos())
        if event.buttons() == Qt.MouseButton.LeftButton:
            if self.is_resizing:
                new_pos, delta = event.globalPosition().toPoint(), event.globalPosition().toPoint() - self.drag_position
                self.drag_position = new_pos;
                geom = self.geometry()
                if "top" in self.resize_handle: geom.setTop(geom.top() + delta.y())
                if "bottom" in self.resize_handle: geom.setBottom(geom.bottom() + delta.y())
                if "left" in self.resize_handle: geom.setLeft(geom.left() + delta.x())
                if "right" in self.resize_handle: geom.setRight(geom.right() + delta.x())
                if geom.width() < 100: geom.setWidth(100)
                if geom.height() < 100: geom.setHeight(100)
                self.setGeometry(geom)
            else:
                self.move(event.globalPosition().toPoint() - self.drag_position)
        event.accept()

    def mouseReleaseEvent(self, event):
        self.is_resizing = False;
        self.drag_position = None;
        event.accept()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape: self.close()


class ScreenshotOverlay(QWidget):
    screenshot_taken = pyqtSignal(QPixmap, QRect)

    def __init__(self, screen_pixmap):
        super().__init__();
        self.full_screen_pixmap = screen_pixmap;
        self.begin, self.end = None, None
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint);
        self.setGeometry(QApplication.primaryScreen().geometry())
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground);
        self.setCursor(Qt.CursorShape.CrossCursor)

    def paintEvent(self, event):
        painter = QPainter(self);
        painter.fillRect(self.rect(), QBrush(QColor(0, 0, 0, 128)))
        if self.begin and self.end:
            selection_rect = QRect(self.begin, self.end).normalized()
            painter.drawPixmap(selection_rect, self.full_screen_pixmap, selection_rect);
            painter.setPen(QPen(QColor(0, 128, 255), 2));
            painter.drawRect(selection_rect)

    def mousePressEvent(self, event):
        self.begin, self.end = event.pos(), event.pos(); self.repaint()

    def mouseMoveEvent(self, event):
        self.end = event.pos(); self.repaint()

    def mouseReleaseEvent(self, event):
        self.hide();
        selection_rect = QRect(self.begin, self.end).normalized()
        if selection_rect.width() > 0 and selection_rect.height() > 0:
            cropped_pixmap = self.full_screen_pixmap.copy(selection_rect);
            self.screenshot_taken.emit(cropped_pixmap, selection_rect)
        self.close()


class AppController(QWidget):
    trigger_screenshot_signal = pyqtSignal()

    def __init__(self, app):
        super().__init__();
        self.app = app;
        self.pinned_windows = [];
        self.overlay = None
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon(resource_path("icon.png")))  # <-- 已修改
        self.tray_icon.setToolTip("PinClip - 截图贴图工具\n快捷键: Ctrl+Alt+P")
        tray_menu = QMenu();
        screenshot_action = QAction("截图 (Ctrl+Alt+P)", self);
        screenshot_action.triggered.connect(self.execute_screenshot)
        about_action = QAction("关于", self);
        about_action.triggered.connect(self.show_about_dialog)
        quit_action = QAction("退出", self);
        quit_action.triggered.connect(self.app.quit)
        tray_menu.addAction(screenshot_action);
        tray_menu.addSeparator();
        tray_menu.addAction(about_action);
        tray_menu.addAction(quit_action)
        self.tray_icon.setContextMenu(tray_menu);
        self.tray_icon.show()
        self.trigger_screenshot_signal.connect(self.execute_screenshot)
        self.hotkey = keyboard.HotKey(keyboard.HotKey.parse('<ctrl>+<alt>+p'), self.on_hotkey_pressed)
        self.listener = keyboard.Listener(on_press=self.hotkey.press, on_release=self.hotkey.release)

    def on_hotkey_pressed(self):
        self.trigger_screenshot_signal.emit()

    def execute_screenshot(self):
        screen = self.app.primaryScreen();
        if not screen: return
        full_screen_pixmap = screen.grabWindow(0);
        self.overlay = ScreenshotOverlay(full_screen_pixmap)
        self.overlay.screenshot_taken.connect(self.on_screenshot_taken);
        self.overlay.show()

    def on_screenshot_taken(self, pixmap, geometry):
        if not pixmap.isNull():
            new_window = PinnedWindow(pixmap, geometry);
            self.pinned_windows.append(new_window);
            new_window.show()

    def show_about_dialog(self):
        QMessageBox.about(self, "关于 PinClip",
                          "<h3>PinClip v1.0</h3><p>一款由您构思和设计的截图、贴图与看图工具。</p><p>主要功能:</p><ul><li><b>截图贴图:</b> 使用 Ctrl+Alt+P 快速截图并置顶。</li><li><b>图片查看:</b> 缩放、拖动、调整大小。</li><li><b>万能输入:</b> 支持拖拽网络/本地图片，右键打开文件。</li></ul><p>感谢您的使用！</p>")

    def start(self):
        print("PinClip 后台服务已启动。请通过系统托盘图标进行交互。");
        self.listener.start()

    def stop(self):
        self.tray_icon.hide();
        self.listener.stop();
        print("PinClip 后台服务已退出。")


if __name__ == '__main__':
    signal.signal(signal.SIGINT, signal.SIG_DFL);
    app = QApplication(sys.argv)
    QApplication.setQuitOnLastWindowClosed(False)
    controller = AppController(app)
    app.aboutToQuit.connect(controller.stop)
    controller.start()
    sys.exit(app.exec())