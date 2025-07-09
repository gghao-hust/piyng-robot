import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QPushButton, QLabel, QTextEdit, QTabWidget, QFileDialog, QVBoxLayout, QWidget, QStackedWidget, QHBoxLayout, QMessageBox
)
import threading
import body  # 导入body.py
import json
import time
import serial_usb
import shutil
import uuid
import os

from PyQt5.QtCore import pyqtSignal, QObject, Qt
from PyQt5.QtGui import QFont, QIcon, QColor, QPalette, QLinearGradient, QBrush, QPixmap, QTransform
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl
from PyQt5.QtSvg import QSvgWidget
from PyQt5.QtSvg import QSvgRenderer
from PyQt5.QtGui import QPainter

class StartPage(QWidget):
    def __init__(self, switch_callback):
        super().__init__()
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)
        self.label = QLabel("欢迎使用皮影机器人上位机！")
        self.label.setFont(QFont("微软雅黑", 28, QFont.Bold))
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet("color: #90CAF9; text-shadow: 1px 1px 2px #0D47A1;")
        self.start_btn = QPushButton("进入主界面")
        self.start_btn.setFixedWidth(220)
        self.start_btn.setFont(QFont("微软雅黑", 16, QFont.Bold))
        self.start_btn.setStyleSheet("QPushButton {background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1976D2, stop:1 #90CAF9); color: white; border-radius: 12px; border: 2px solid #90CAF9; padding: 12px;} QPushButton:hover {background-color: #90CAF9; color: #0D47A1;}")
        self.start_btn.clicked.connect(switch_callback)
        layout.addSpacing(100)
        layout.addWidget(self.label)
        layout.addSpacing(40)
        layout.addWidget(self.start_btn, alignment=Qt.AlignCenter)
        layout.addSpacing(100)
        self.setLayout(layout)

class DetectWorker(QObject):
    data_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._stop_flag = False

    def start_detect(self):
        def callback(data):
            self.data_signal.emit(data)
        body.main(data_callback=callback, stop_flag_func=lambda: self._stop_flag)

    def stop(self):
        self._stop_flag = True

class MainTabs(QTabWidget):
    video_script_generated = pyqtSignal(str)  # 新增信号，参数为剧本路径
    def __init__(self):
        super().__init__()
        self.setFont(QFont("微软雅黑", 13, QFont.Bold))
        self.setStyleSheet("""
            QTabWidget::pane { border: 3px solid #90CAF9; border-radius: 12px; background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #e3f2fd, stop:1 #bbdefb); }
            QTabBar::tab { background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1976D2, stop:1 #90CAF9); border: 2px solid #90CAF9; border-radius: 8px; min-width: 120px; min-height: 36px; margin: 6px; font-weight: bold; color: white; }
            QTabBar::tab:selected { background: #90CAF9; color: #0D47A1; }
        """)
        self.recording_thread = None  # 新增
        self.recording_file = None    # 新增
        self.is_recording = False     # 新增
        self._stop_record_flag = False # 新增
        # 只保留一组tab添加
        self.addTab(self.create_import_tab(), QIcon(), "导入剧本")
        self.addTab(self.create_generate_tab(), QIcon(), "生成剧本")
        self.addTab(self.create_detect_tab(), QIcon(), "实时检测")
        # 连接信号
        self.video_script_generated.connect(self.on_video_script_generated)
        self.recording_thread = None  # 新增
        self.recording_file = None    # 新增
        self.is_recording = False     # 新增
        self._stop_record_flag = False # 新增

    def create_import_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(16)
        self.import_btn = QPushButton("选择剧本文件")
        self.import_btn.setFont(QFont("微软雅黑", 12))
        self.import_btn.setStyleSheet("QPushButton {background-color: #2196F3; color: white; border-radius: 8px; padding: 8px;} QPushButton:hover {background-color: #1976D2;}")
        self.import_btn.clicked.connect(self.import_script)
        self.script_content = QTextEdit()
        self.script_content.setFont(QFont("Consolas", 11))
        self.script_content.setStyleSheet("QTextEdit {background: #f5f5f5; border: 1px solid #bdbdbd; border-radius: 6px;}")
        self.run_btn = QPushButton("运行剧本")
        self.run_btn.setFont(QFont("微软雅黑", 12))
        self.run_btn.setStyleSheet("QPushButton {background-color: #FF9800; color: white; border-radius: 8px; padding: 8px;} QPushButton:hover {background-color: #F57C00;}")
        self.run_btn.clicked.connect(self.run_script_thread)
        layout.addWidget(self.import_btn)
        layout.addWidget(self.script_content)
        layout.addWidget(self.run_btn, alignment=Qt.AlignRight)
        widget.setLayout(layout)
        return widget

    def import_script(self):
        file, _ = QFileDialog.getOpenFileName(self, "选择剧本文件", "", "JSON Files (*.json)")
        if file:
            with open(file, 'r', encoding='utf-8') as f:
                self.script_content.setText(f.read())

    def create_generate_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(16)
        # 新增两种生成方式按钮
        self.realtime_record_btn = QPushButton("实时录制生成剧本")
        self.realtime_record_btn.setFont(QFont("微软雅黑", 13, QFont.Bold))
        self.realtime_record_btn.setStyleSheet("QPushButton {background-color: #1976D2; color: white; border-radius: 10px; padding: 10px;} QPushButton:hover {background-color: #90CAF9; color: #0D47A1;}")
        self.realtime_record_btn.clicked.connect(self.show_realtime_record_area)
        self.video_detect_btn = QPushButton("视频检测生成剧本")
        self.video_detect_btn.setFont(QFont("微软雅黑", 13, QFont.Bold))
        self.video_detect_btn.setStyleSheet("QPushButton {background-color: #1976D2; color: white; border-radius: 10px; padding: 10px;} QPushButton:hover {background-color: #90CAF9; color: #0D47A1;}")
        self.video_detect_btn.clicked.connect(self.show_video_detect_tip)
        layout.addWidget(self.realtime_record_btn)
        layout.addWidget(self.video_detect_btn)
        # 下面保留原有录制相关控件
        self.record_btn = QPushButton("开始录制")
        self.record_btn.setFont(QFont("微软雅黑", 12))
        self.record_btn.setStyleSheet("QPushButton {background-color: #8BC34A; color: white; border-radius: 8px; padding: 8px;} QPushButton:hover {background-color: #689F38;}")
        self.stop_record_btn = QPushButton("结束录制")
        self.stop_record_btn.setFont(QFont("微软雅黑", 12))
        self.stop_record_btn.setStyleSheet("QPushButton {background-color: #FF9800; color: white; border-radius: 8px; padding: 8px;} QPushButton:hover {background-color: #F57C00;}")
        self.save_btn = QPushButton("保存剧本")
        self.save_btn.setFont(QFont("微软雅黑", 12))
        self.save_btn.setStyleSheet("QPushButton {background-color: #607D8B; color: white; border-radius: 8px; padding: 8px;} QPushButton:hover {background-color: #455A64;}")
        self.save_btn.setVisible(False)  # 隐藏保存按钮
        self.record_status = QLabel("")  # 新增
        self.record_status.setFont(QFont("微软雅黑", 11))
        # 新增返回按钮
        self.back_btn = QPushButton("返回")
        self.back_btn.setFont(QFont("微软雅黑", 12))
        self.back_btn.setStyleSheet("QPushButton {background-color: #B0BEC5; color: #263238; border-radius: 8px; padding: 8px;} QPushButton:hover {background-color: #90A4AE; color: #263238;}")
        self.back_btn.clicked.connect(self.hide_realtime_record_area)
        # 默认隐藏录制相关控件
        self.record_btn.setVisible(False)
        self.stop_record_btn.setVisible(False)
        self.record_status.setVisible(False)
        self.back_btn.setVisible(False)
        # 添加到布局
        layout.addWidget(self.record_btn)
        layout.addWidget(self.stop_record_btn, alignment=Qt.AlignRight)
        layout.addWidget(self.save_btn, alignment=Qt.AlignRight)
        layout.addWidget(self.record_status)
        layout.addWidget(self.back_btn, alignment=Qt.AlignLeft)
        widget.setLayout(layout)
        self.record_btn.clicked.connect(self.start_record_script)
        self.stop_record_btn.clicked.connect(self.stop_record_script)
        self.save_btn.clicked.connect(self.save_recorded_script)
        self.stop_record_btn.setEnabled(False)
        return widget

    def show_realtime_record_area(self):
        self.record_btn.setVisible(True)
        self.stop_record_btn.setVisible(True)
        self.record_status.setVisible(True)
        self.back_btn.setVisible(True)
        self.realtime_record_btn.setVisible(False)
        self.video_detect_btn.setVisible(False)
        self.record_status.setText("请点击下方按钮进行实时录制操作。")

    def hide_realtime_record_area(self):
        self.record_btn.setVisible(False)
        self.stop_record_btn.setVisible(False)
        self.record_status.setVisible(False)
        self.back_btn.setVisible(False)
        self.realtime_record_btn.setVisible(True)
        self.video_detect_btn.setVisible(True)
        self.record_status.setText("")

    def show_realtime_record_tip(self):
        self.record_status.setText("实时录制生成剧本功能，后续实现！")

    def show_video_detect_tip(self):
        file, _ = QFileDialog.getOpenFileName(self, "选择视频文件", "", "Video Files (*.mp4 *.avi *.mov *.mkv)")
        if file:
            self.record_status.setText("正在生成剧本，请稍候...")
            self.record_status.setVisible(True)
            def generate_script():
                import time, json, os
                time.sleep(5)  # 模拟处理
                base, ext = os.path.splitext(file)
                script_path = base + "_script.json"
                with open(script_path, 'w', encoding='utf-8') as f:
                    json.dump([{"func": "set_angle_24", "args": [0, 90], "interval": 0.5}], f, ensure_ascii=False, indent=2)
                # 处理完后发射信号
                self.video_script_generated.emit(script_path)
            import threading
            t = threading.Thread(target=generate_script, daemon=True)
            t.start()

    def on_video_script_generated(self, script_path):
        self.record_status.setText("")
        QMessageBox.information(self, "生成完成", f"已生成剧本，并保存在同级目录下：\n{script_path}")

    def create_detect_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(16)
        self.start_detect_btn = QPushButton("开始检测")
        self.start_detect_btn.setFont(QFont("微软雅黑", 12))
        self.start_detect_btn.setStyleSheet("QPushButton {background-color: #00BCD4; color: white; border-radius: 8px; padding: 8px;} QPushButton:hover {background-color: #00838F;}")
        self.stop_detect_btn = QPushButton("停止检测")
        self.stop_detect_btn.setFont(QFont("微软雅黑", 12))
        self.stop_detect_btn.setStyleSheet("QPushButton {background-color: #F44336; color: white; border-radius: 8px; padding: 8px;} QPushButton:hover {background-color: #B71C1C;}")
        self.detect_display = QTextEdit()
        self.detect_display.setFont(QFont("Consolas", 11))
        self.detect_display.setStyleSheet("QTextEdit {background: #f5f5f5; border: 1px solid #bdbdbd; border-radius: 6px;}")
        layout.addWidget(self.start_detect_btn)
        layout.addWidget(self.stop_detect_btn)
        layout.addWidget(self.detect_display)
        widget.setLayout(layout)
        # 检测线程相关
        self.detect_worker = DetectWorker()
        self.detect_worker.data_signal.connect(self.update_detect_display)
        self.detect_thread = None
        self.start_detect_btn.clicked.connect(self.start_detect_thread)
        self.stop_detect_btn.clicked.connect(self.stop_detect_thread)
        return widget

    def start_detect_thread(self):
        if self.detect_thread is None or not self.detect_thread.is_alive():
            self.detect_display.append("检测已启动...")
            self.detect_worker._stop_flag = False  # 重置停止标志
            self.detect_thread = threading.Thread(target=self.detect_worker.start_detect, daemon=True)
            self.detect_thread.start()
        else:
            self.detect_display.append("检测线程已在运行！")

    def stop_detect_thread(self):
        if self.detect_thread and self.detect_thread.is_alive():
            self.detect_worker.stop()
            self.detect_display.append("检测已停止。")
        else:
            self.detect_display.append("检测线程未在运行！")

    def update_detect_display(self, data):
        self.detect_display.clear()
        self.detect_display.append(data)

    def run_script_thread(self):
        import threading
        t = threading.Thread(target=self.run_script, daemon=True)
        t.start()

    def run_script(self):
        script_text = self.script_content.toPlainText()
        try:
            actions = json.loads(script_text)
            for action in actions:
                func = action.get("func")
                args = action.get("args", [])
                interval = action.get("interval", 0.5)
                if func == "set_angle_24":
                    serial_usb.set_angle_24(*args)
                elif func == "set_angle_13":
                    serial_usb.set_angle_13(*args)
                elif func == "zdt_position_control":
                    import serial_zdt
                    serial_zdt.position_control(serial_zdt.ser_zdt, *args)
                # 可扩展更多动作类型
                self.script_content.append(f"已执行: {func} {args}")
                time.sleep(interval)
            self.script_content.append("\n剧本执行完毕！")
        except Exception as e:
            self.script_content.append(f"\n运行剧本出错: {e}")

    def start_record_script(self):
        if self.is_recording:
            self.record_status.setText("正在录制中，请勿重复点击！")
            return
        file_path, _ = QFileDialog.getSaveFileName(self, "选择剧本保存路径", "", "JSON Files (*.json)")
        if not file_path:
            self.record_status.setText("未选择保存路径，取消录制。")
            return
        import threading
        self.recording_file = file_path
        self.is_recording = True
        self._stop_record_flag = False
        self.record_status.setText(f"录制中，文件: {self.recording_file}")
        self.record_btn.setEnabled(False)
        self.save_btn.setEnabled(False)
        self.stop_record_btn.setEnabled(True)
        def record_thread():
            import body
            try:
                body.main(args=["--mode", "realtime", "--serial_file", self.recording_file], stop_flag_func=lambda: self._stop_record_flag)
            except Exception as e:
                self.record_status.setText(f"录制出错: {e}")
            finally:
                self.is_recording = False
                self.record_btn.setEnabled(True)
                self.save_btn.setEnabled(False)
                self.stop_record_btn.setEnabled(False)
                self.record_status.setText(f"录制已结束，文件: {self.recording_file}")
        self.recording_thread = threading.Thread(target=record_thread, daemon=True)
        self.recording_thread.start()

    def stop_record_script(self):
        if not self.is_recording:
            self.record_status.setText("未在录制中！")
            return
        self._stop_record_flag = True
        self.record_status.setText("正在结束录制，请稍候...")
        if self.recording_thread is not None:
            self.recording_thread.join(timeout=5)
        self.is_recording = False
        self.record_btn.setEnabled(True)
        self.save_btn.setEnabled(False)
        self.stop_record_btn.setEnabled(False)
        self.record_status.setText(f"录制已结束，文件: {self.recording_file}")

    def save_recorded_script(self):
        # 该功能已隐藏，无需实现
        pass

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("皮影机器人上位机")
        self.setGeometry(100, 100, 1600, 900)
        # 主界面整体布局
        main_widget = QWidget()
        main_layout = QVBoxLayout()
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        # 顶部横条
        self.top_bar = QWidget()
        self.top_bar.setFixedHeight(54)
        self.top_bar.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1976D2, stop:1 #90CAF9);
            border-bottom: 2px solid #C9B037;
            border-top-left-radius: 18px;
            border-top-right-radius: 18px;
            box-shadow: 0 2px 12px #1976D2;
        """)
        main_layout.addWidget(self.top_bar)
        # 平台名称及两侧祥云花纹
        title_row = QHBoxLayout()
        self.left_flower = QSvgWidget("古风祥云云朵46.svg")
        self.left_flower.setFixedHeight(60)
        self.left_flower.setFixedWidth(200)
        self.left_flower.setStyleSheet("background: transparent; margin-left: 18px;")
        title_row.addWidget(self.left_flower, alignment=Qt.AlignVCenter)
        self.platform_title = QLabel("皮影机器人控制平台")
        self.platform_title.setFont(QFont("微软雅黑", 44, QFont.Bold))
        self.platform_title.setAlignment(Qt.AlignCenter)
        self.platform_title.setStyleSheet("""
            color: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1976D2, stop:1 #90CAF9);
            letter-spacing: 12px;
            text-shadow: 2px 2px 8px #90CAF9;
            margin-top: 18px;
            margin-bottom: 12px;
        """)
        title_row.addWidget(self.platform_title, stretch=1, alignment=Qt.AlignVCenter)
        self.right_flower = QLabel()
        # 用QSvgRenderer渲染SVG到QPixmap
        renderer = QSvgRenderer("古风祥云云朵46.svg")
        pixmap = QPixmap(200, 60)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()
        # 水平翻转
        flipped_pixmap = pixmap.transformed(QTransform().scale(-1, 1))
        self.right_flower.setPixmap(flipped_pixmap)
        self.right_flower.setFixedSize(200, 60)
        self.right_flower.setStyleSheet("background: transparent; margin-right: 18px;")
        title_row.addWidget(self.right_flower, alignment=Qt.AlignVCenter)
        main_layout.addLayout(title_row)
        # 分割线
        self.divider = QWidget()
        self.divider.setFixedHeight(4)
        self.divider.setStyleSheet("background: #C9B037; border-radius: 2px; margin-left: 80px; margin-right: 80px;")
        main_layout.addWidget(self.divider)
        # 主体内容左右分栏
        content_layout = QHBoxLayout()
        content_layout.setSpacing(32)
        content_layout.setContentsMargins(32, 16, 32, 16)
        # 左侧Tab卡片
        self.left_card = QWidget()
        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(32, 32, 32, 32)
        self.stack = QStackedWidget()
        left_layout.addWidget(self.stack)
        self.start_page = StartPage(self.show_main_tabs)
        self.main_tabs = MainTabs()
        self.stack.addWidget(self.start_page)
        self.stack.addWidget(self.main_tabs)
        self.left_card.setLayout(left_layout)
        self.left_card.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #fff, stop:1 #e3f2fd);
            border-radius: 32px;
            box-shadow: 0 8px 32px #90CAF9;
            margin: 18px;
        """)
        content_layout.addWidget(self.left_card, 2)
        # 右侧网页卡片
        self.web_view = QWebEngineView()
        self.web_view.setMinimumWidth(900)
        self.web_view.setVisible(False)  # 初始隐藏
        self.web_frame = QWidget()
        web_layout = QVBoxLayout()
        web_layout.setContentsMargins(18, 18, 18, 18)
        # 网页卡片顶部渐变条
        web_card_top_bar = QWidget()
        web_card_top_bar.setFixedHeight(10)
        web_card_top_bar.setStyleSheet("background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1976D2, stop:1 #90CAF9); border-top-left-radius: 20px; border-top-right-radius: 20px;")
        web_layout.addWidget(web_card_top_bar)
        # 网页卡片顶部标题和刷新
        web_card_top = QHBoxLayout()
        web_title = QLabel("检测图像")
        web_title.setFont(QFont("微软雅黑", 20, QFont.Bold))
        web_title.setStyleSheet("color: #1976D2; margin-left: 8px;")
        refresh_btn = QPushButton("⟳")
        refresh_btn.setFixedSize(36, 36)
        refresh_btn.setStyleSheet("background: #90CAF9; border-radius: 18px; color: #fff; font-size: 20px; border: none;")
        refresh_btn.clicked.connect(lambda: self.web_view.reload())
        web_card_top.addWidget(web_title)
        web_card_top.addStretch()
        web_card_top.addWidget(refresh_btn)
        web_layout.addLayout(web_card_top)
        web_layout.addWidget(self.web_view)
        self.web_frame.setLayout(web_layout)
        self.web_frame.setStyleSheet('''
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #e3f2fd, stop:1 #bbdefb);
            border: 3px solid #1976D2;
            border-radius: 32px;
            box-shadow: 0px 0px 32px #1976D2;
        ''')
        self.web_frame.setMinimumWidth(960)
        self.web_frame.setMaximumWidth(1200)
        self.web_frame.setSizePolicy(self.web_view.sizePolicy())
        self.web_frame.setVisible(False)  # 初始隐藏
        content_layout.addWidget(self.web_frame, 3)
        main_layout.addLayout(content_layout)
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)
        # 设置主窗口蓝色渐变背景
        palette = QPalette()
        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0, QColor("#0D47A1"))  # 深蓝
        gradient.setColorAt(1, QColor("#90CAF9"))  # 浅蓝
        palette.setBrush(QPalette.Window, QBrush(gradient))
        self.setPalette(palette)
        # 设置窗口圆角
        self.setStyleSheet("QMainWindow { border-radius: 18px; }")

    def show_main_tabs(self):
        self.stack.setCurrentWidget(self.main_tabs)
        # 进入主界面时再显示网页并加载
        if not self.web_view.isVisible():
            self.web_view.setVisible(True)
            self.web_view.setUrl(QUrl("http://192.168.137.11:8000/"))
        self.web_frame.setVisible(True)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_()) 