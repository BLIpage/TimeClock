# -*- coding: utf-8 -*-
# 完整：纯文字透明背景数字桌面时钟

import sys, json, time, threading, datetime as dt, email.utils, requests
from pathlib import Path
from platformdirs import user_config_dir
import logging  # 导入日志模块
import os  # 导入 os 模块用于路径操作

from PySide6.QtCore import Qt, QTimer, QPoint
from PySide6.QtGui import QFont, QColor, QFontMetrics, QIcon
from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout,
    QMenu, QSlider, QDoubleSpinBox, QColorDialog, QSystemTrayIcon,
    QPushButton, QFormLayout, QStyle, QCheckBox,
    QDialog, QDialogButtonBox
)

# --- 路径设置 ---
# 应用程序名称，用于生成配置文件的路径
APP_NAME = "TimeClock"
# 获取用户配置目录的路径，并以应用程序名称作为子目录
CONFIG_DIR = Path(user_config_dir(APP_NAME, "TimeClock"))
# 如果配置目录不存在，则创建它
CONFIG_DIR.mkdir(parents=True, exist_ok=True)
# 配置文件路径
CONFIG_FILE = CONFIG_DIR / "config.json"

# 日志文件目录
LOG_DIR = CONFIG_DIR / "Logs"
# 如果日志目录不存在，则创建它
LOG_DIR.mkdir(parents=True, exist_ok=True)
# 日志文件路径，以当前时间命名
LOG_FILE = LOG_DIR / f"{dt.datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

ICON_PATH = Path(__file__).with_name("clock.ico")
SYNC_URL = "https://time.is/just"

# --- 日志配置 ---
logging.basicConfig(
    level=logging.INFO,  # 默认日志级别为 INFO，可以在开发时改为 DEBUG
    format='%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),  # 将日志写入文件
        logging.StreamHandler(sys.stdout)  # 同时将日志输出到控制台
    ]
)
logger = logging.getLogger(__name__)  # 获取日志记录器实例


# --- 全局异常处理 ---
def handle_exception(exc_type, exc_value, exc_traceback):
    """捕获所有未处理的异常并记录到日志中。"""
    if issubclass(exc_type, KeyboardInterrupt):
        # 允许 Ctrl+C 正常退出，不记录为错误
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logger.critical("程序发生未捕获的异常！", exc_info=(exc_type, exc_value, exc_traceback))
    # 可以选择在此处重新调用默认的异常处理以显示错误窗口等
    sys.exit(1)  # 强制退出程序以防止不确定状态


sys.excepthook = handle_exception  # 将自定义的异常处理函数设置为全局钩子


# --- 时间同步 ---
def fetch_ntp():
    """
    通过 HTTP 请求获取 NTP 时间。
    尝试从响应头中的 'Date' 字段解析时间。
    如果失败，则返回本地 UTC 时间。
    """
    logger.info("NTP 同步: 尝试从 NTP 服务器获取时间...")
    try:
        r = requests.head(SYNC_URL, timeout=5)
        if "Date" in r.headers:
            ntp_time = email.utils.parsedate_to_datetime(r.headers["Date"])
            logger.info(f"NTP 同步: 成功获取 NTP 时间: {ntp_time.isoformat()}")
            return ntp_time
        else:
            logger.warning(f"NTP 同步: 从 {SYNC_URL} 接收到响应，但响应头中未找到 'Date' 字段。")
    except requests.exceptions.Timeout:
        logger.error(f"NTP 同步: 从 {SYNC_URL} 获取 NTP 时间超时（5秒）。", exc_info=True)
    except requests.exceptions.ConnectionError as e:
        logger.error(f"NTP 同步: 连接到 {SYNC_URL} 失败: {e}", exc_info=True)
    except requests.exceptions.RequestException as e:
        logger.error(f"NTP 同步: HTTP 请求 {SYNC_URL} 失败: {e}", exc_info=True)
    except Exception as e:
        logger.error(f"NTP 同步: 解析 NTP 时间时发生未知错误: {e}", exc_info=True)

    local_utc_time = dt.datetime.now(dt.UTC)
    logger.info(f"NTP 同步: 回退到本地 UTC 时间: {local_utc_time.isoformat()}")
    return local_utc_time


class DigitalClock(QWidget):
    """
    数字时钟主窗口类。
    显示日期和时间，支持自定义字体大小、透明度、颜色、时间偏移和窗口置顶。
    具有托盘图标菜单，用于设置和退出。
    """

    def __init__(self):
        """
        初始化 DigitalClock 实例。
        设置默认属性，创建 UI 元素，加载配置，并启动定时器和 NTP 同步线程。
        """
        super().__init__()
        logger.info("程序启动: DigitalClock 应用程序初始化。")

        # 默认属性设置
        self.time_pt = 10.0
        self.spacing = 2.0
        self.opacity = 90.0
        self.topmost = True
        self.color = QColor("white")
        self.offset = 0.0  # NTP 同步获取的偏移
        self.manual_offset = 0.0  # 用户手动设置的偏移
        self.drag_pos = None  # 用于窗口拖动

        logger.debug("窗口配置: 设置 Qt 窗口标志和属性。")
        self.setWindowFlags(Qt.FramelessWindowHint)  # 无边框
        self.setAttribute(Qt.WA_TranslucentBackground)  # 背景透明

        # 创建日期和时间显示标签
        self.date_lbl = QLabel("--")
        self.time_lbl = QLabel("--")
        for lbl in (self.date_lbl, self.time_lbl):
            lbl.setAlignment(Qt.AlignRight)
            lbl.setAttribute(Qt.WA_TranslucentBackground)
        logger.debug("UI 组件: 日期和时间 QLabel 创建成功。")

        # 设置垂直布局
        self.vbox = QVBoxLayout(self)
        self.vbox.setContentsMargins(12, 8, 12, 8)  # 设置内边距
        self.vbox.addWidget(self.date_lbl)
        self.vbox.addWidget(self.time_lbl)
        logger.debug("UI 布局: QVBoxLayout 设置完成，标签已添加。")

        # 加载托盘图标
        icon_path_str = str(ICON_PATH)
        if ICON_PATH.exists():
            icon = QIcon(icon_path_str)
            logger.debug(f"资源加载: 成功加载托盘图标: {icon_path_str}")
        else:
            icon = self.style().standardIcon(QStyle.SP_ComputerIcon)
            logger.warning(f"资源加载: 托盘图标文件 '{icon_path_str}' 不存在，使用系统默认图标。")

        # 创建系统托盘图标并设置菜单
        self.tray = QSystemTrayIcon(icon, self)
        self.tray.setContextMenu(self._build_menu())
        self.tray.activated.connect(self._handle_tray_activated)  # 连接激活信号
        self.tray.show()
        logger.info("用户界面: 系统托盘图标创建并显示。")

        self._load()  # 加载用户配置
        self._apply_style()  # 应用样式

        # 启动定时器更新时间
        self.timer = QTimer(self, timeout=self._tick)
        self.timer.start(1000)  # 每秒触发
        logger.info("内部逻辑: 时间更新 QTimer 启动 (1000ms 间隔)。")

        # 启动 NTP 同步线程
        threading.Thread(target=self._ntp_loop, daemon=True).start()
        logger.info("内部逻辑: NTP 同步后台线程启动。")

    def _handle_tray_activated(self, reason):
        """处理托盘图标激活事件，记录用户操作。"""
        if reason == QSystemTrayIcon.Trigger:
            if self.isHidden():
                self.showNormal()
                logger.info("用户操作: 通过托盘点击显示主窗口。")
            else:
                self.hide()
                logger.info("用户操作: 通过托盘点击隐藏主窗口。")
        elif reason == QSystemTrayIcon.Context:
            logger.debug("用户操作: 右键点击托盘图标，上下文菜单显示。")
        else:
            logger.debug(f"用户操作: 托盘图标被激活，原因: {reason}。")

    def _now(self):
        """
        计算并返回当前准确时间。
        包含 NTP 偏移和用户手动偏移，并转换为东八区时间。
        """
        current_utc = dt.datetime.now(dt.UTC)
        adjusted_utc = current_utc + dt.timedelta(seconds=self.offset + self.manual_offset)
        local_time = adjusted_utc.astimezone(dt.timezone(dt.timedelta(hours=8)))  # 假设目标时区是 UTC+8
        # logger.debug(f"内部逻辑: _now() 计算结果 - 本地时间: {local_time.isoformat()} (UTC+8)") # 过于频繁，改为 debug
        return local_time

    def _tick(self):
        """
        定时器触发函数，每秒更新日期和时间显示，并调整窗口大小。
        """
        now = self._now()
        date_text = f"{now.year}年{now.month}月{now.day}日"
        time_text = now.strftime("%H:%M:%S")

        self.date_lbl.setText(date_text)
        self.time_lbl.setText(time_text)
        # logger.debug(f"UI 更新: 时间显示刷新 - 日期: '{date_text}', 时间: '{time_text}'")

        # 计算并设置窗口大小
        w = max(
            QFontMetrics(self.date_lbl.font()).horizontalAdvance(self.date_lbl.text()),
            QFontMetrics(self.time_lbl.font()).horizontalAdvance(self.time_lbl.text())
        ) + 24  # 额外留出一些边距
        h = (
                self._font_h(self.time_pt - 1)  # 日期字体高度
                + self._font_h(self.time_pt)  # 时间字体高度
                + int(self.spacing)  # 行间距
                + self.vbox.contentsMargins().top()  # 上边距
                + self.vbox.contentsMargins().bottom()  # 下边距
        )
        # 仅当窗口大小实际改变时才记录，避免重复日志
        if self.width() != w or self.height() != h:
            self.setFixedWidth(w)
            self.setFixedHeight(h)
            logger.debug(f"UI 布局: 窗口大小已根据文本内容调整为: 宽度={w}, 高度={h}。")

    def _font_h(self, pt):
        """
        计算指定磅值字体的像素高度。
        """
        f = QFont("Noto Sans SC")  # 假设使用思源黑体 SC 字体
        f.setPointSizeF(pt)
        height = QFontMetrics(f).height() + 2  # 额外增加2像素以确保不裁剪
        logger.debug(f"字体计算: 磅值 {pt} 的 'Noto Sans SC' 字体高度为 {height} 像素。")
        return height

    def _apply_style(self):
        """
        根据当前设置应用字体、颜色、透明度、行间距和窗口置顶状态。
        """
        logger.info("UI 样式: 开始应用新的样式设置。")
        date_pt = max(self.time_pt - 1, 1)  # 日期字体比时间字体小1磅，最小为1

        f1 = QFont("Noto Sans SC");
        f1.setPointSizeF(date_pt);
        f1.setBold(True)
        f2 = QFont("Noto Sans SC");
        f2.setPointSizeF(self.time_pt);
        f2.setBold(True)
        self.date_lbl.setFont(f1)
        self.time_lbl.setFont(f2)
        logger.debug(f"UI 样式: 字体已设置为 'Noto Sans SC'，日期字体大小: {date_pt}pt, 时间字体大小: {self.time_pt}pt。")

        css = f"color:{self.color.name()}; background: transparent;"
        self.date_lbl.setStyleSheet(css)
        self.time_lbl.setStyleSheet(css)
        logger.debug(f"UI 样式: 文字颜色设置为: {self.color.name()}。")

        self.vbox.setSpacing(int(self.spacing))
        logger.debug(f"UI 样式: 行间距设置为: {int(self.spacing)} 像素。")

        self.setWindowOpacity(self.opacity / 100)
        logger.debug(f"UI 样式: 窗口不透明度设置为: {self.opacity}%。")

        # 检查窗口置顶状态是否改变，如果改变则重新设置并记录
        current_flags = self.windowFlags()
        desired_flags = Qt.FramelessWindowHint | (Qt.WindowStaysOnTopHint if self.topmost else Qt.Widget)
        if current_flags != desired_flags:
            self.setWindowFlags(desired_flags)
            self.show()  # 重新显示窗口以应用新的窗口标志
            logger.info(f"UI 样式: 窗口置顶状态已更新为: {self.topmost}。")
        logger.info("UI 样式: 样式应用完成。")

    def _build_menu(self):
        """
        构建并返回系统托盘图标的上下文菜单。
        包含显示/隐藏、设置和退出选项。
        """
        logger.debug("用户界面: 正在构建系统托盘菜单。")
        m = QMenu()
        m.addAction("显示/隐藏", lambda: self.showNormal() if self.isHidden() else self.hide())
        m.addAction("设置", self._open_settings)
        m.addSeparator()
        m.addAction("退出", self._exit)
        logger.debug("用户界面: 系统托盘菜单构建完成。")
        return m

    def _ntp_loop(self):
        """
        后台线程循环，每 10 分钟执行一次 NTP 时间同步，并更新时间偏移量。
        """
        logger.info("内部逻辑: NTP 同步循环线程启动。")
        while True:
            try:
                ntp_dt = fetch_ntp()
                current_utc = dt.datetime.now(dt.UTC)
                self.offset = (ntp_dt - current_utc).total_seconds()
                logger.info(f"内部逻辑: NTP 偏移量更新为: {self.offset:.6f} 秒。")
            except Exception as e:
                logger.error(f"内部逻辑: NTP 同步循环中发生错误: {e}", exc_info=True)
            time.sleep(600)  # 暂停 10 分钟 (600 秒)

    def _open_settings(self):
        """
        打开设置对话框，并根据用户在对话框中的选择更新时钟设置。
        """
        logger.info("用户操作: 点击 '设置'，打开设置对话框。")
        # 记录旧的设置值，以便在接受后比较哪些参数被更改
        old_settings = {
            "font": self.time_pt,
            "opacity": self.opacity,
            "spacing": self.spacing,
            "color": self.color.name(),
            "top": self.topmost,
            "offset": self.manual_offset
        }

        dlg = SettingsDialog(self)
        if dlg.exec():  # 如果用户点击了“确定”按钮 (QDialog.Accepted)
            logger.info("用户操作: 设置对话框已接受更改。")
            # 更新时钟属性为对话框中设置的值
            self.time_pt = dlg.font_size
            self.opacity = dlg.opacity
            self.spacing = dlg.spacing
            self.color = dlg.color
            self.manual_offset = dlg.manual_offset
            self.topmost = dlg.chk_top.isChecked()

            # 记录具体的更改
            new_settings = {
                "font": self.time_pt,
                "opacity": self.opacity,
                "spacing": self.spacing,
                "color": self.color.name(),
                "top": self.topmost,
                "offset": self.manual_offset
            }
            changed_items = []
            for key, new_val in new_settings.items():
                old_val = old_settings[key]
                if old_val != new_val:
                    changed_items.append(f"'{key}': '{old_val}' -> '{new_val}'")
            if changed_items:
                logger.info(f"用户操作: 检测到设置更改: {'; '.join(changed_items)}")
            else:
                logger.info("用户操作: 设置对话框被接受，但未检测到任何设置更改。")

            self._apply_style()  # 应用新的样式设置
            self._save()  # 保存当前配置
        else:  # 如果用户点击了“取消”按钮 (QDialog.Rejected)
            logger.info("用户操作: 设置对话框已取消更改。")

    def _save(self):
        """
        将当前时钟的各项设置保存到 JSON 配置文件中。
        """
        logger.info("配置管理: 尝试保存当前配置到文件。")
        try:
            data = dict(
                font=self.time_pt,
                opacity=self.opacity,
                spacing=self.spacing,
                color=self.color.name(),
                top=self.topmost,
                offset=self.manual_offset,
                pos=[self.x(), self.y()]  # 保存窗口当前位置
            )
            CONFIG_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')
            logger.info(f"配置管理: 配置已成功保存到 '{CONFIG_FILE}'。")
            logger.debug(f"配置管理: 保存的配置数据: {json.dumps(data, indent=2, ensure_ascii=False)}")
        except Exception as e:
            logger.error(f"配置管理: 保存配置失败: {e}", exc_info=True)

    def _load(self):
        """
        从 JSON 配置文件中加载保存的设置。
        如果配置文件不存在或加载失败，则使用默认值。
        """
        logger.info("配置管理: 尝试从文件加载配置。")
        if CONFIG_FILE.exists():
            try:
                raw_data = CONFIG_FILE.read_text(encoding='utf-8')
                d = json.loads(raw_data)

                # 记录加载前后的值，以便调试
                logger.debug(f"配置管理: 原始配置数据:\n{raw_data}")

                self.time_pt = d.get("font", self.time_pt)
                self.opacity = d.get("opacity", self.opacity)
                self.spacing = d.get("spacing", self.spacing)
                self.color = QColor(d.get("color", self.color.name()))
                self.topmost = d.get("top", self.topmost)
                self.manual_offset = d.get("offset", 0.0)

                if pos_list := d.get("pos"):
                    if isinstance(pos_list, list) and len(pos_list) == 2:
                        # 确保 pos_list 是有效的 [x, y] 格式
                        try:
                            self.move(QPoint(int(pos_list[0]), int(pos_list[1])))
                            logger.info(f"配置管理: 成功加载窗口位置: x={pos_list[0]}, y={pos_list[1]}。")
                        except ValueError:
                            logger.error(f"配置管理: 配置文件中位置数据无效: {pos_list}，将使用默认位置。", exc_info=True)
                    else:
                        logger.warning(f"配置管理: 配置文件中 'pos' 格式不正确: {pos_list}，将使用默认位置。")
                else:
                    logger.debug("配置管理: 配置文件中未找到 'pos' 键，将使用默认位置。")

                logger.info(f"配置管理: 配置已成功从 '{CONFIG_FILE}' 加载。")
                logger.debug(
                    f"配置管理: 加载后的配置属性: font={self.time_pt}, opacity={self.opacity}, spacing={self.spacing}, "
                    f"color={self.color.name()}, top={self.topmost}, offset={self.manual_offset}")
            except json.JSONDecodeError as e:
                logger.error(f"配置管理: 加载配置失败，JSON 解析错误: {e}", exc_info=True)
                logger.warning("配置管理: 无法解析配置文件，将使用默认配置。")
            except Exception as e:  # 捕获其他所有可能的异常
                logger.error(f"配置管理: 加载配置时发生未知错误: {e}", exc_info=True)
                logger.warning("配置管理: 加载配置文件失败，将使用默认配置。")
        else:
            logger.warning(f"配置管理: 配置文件 '{CONFIG_FILE}' 不存在，将使用默认配置。")

    def _exit(self):
        """
        保存当前设置并退出应用程序。
        """
        logger.info("用户操作: 用户选择退出应用程序。")
        self._save()
        QApplication.quit()
        logger.info("程序生命周期: 应用程序已正常退出。")

    def paintEvent(self, e):
        """
        重写 paintEvent 方法，因为窗口背景是透明的，不需要进行任何绘制。
        """
        # logger.debug("UI 绘制: paintEvent 被调用，跳过绘制（透明背景）。") # 如果设置为DEBUG会非常频繁
        pass

    def mousePressEvent(self, e):
        """
        鼠标按下事件处理函数。
        如果鼠标左键按下，则记录当前全局位置，用于拖动窗口。
        """
        if e.button() == Qt.LeftButton:
            self.drag_pos = e.globalPosition().toPoint()
            logger.debug(f"用户操作: 鼠标左键按下，开始窗口拖动。起始位置: ({self.drag_pos.x()}, {self.drag_pos.y()})。")
        else:
            self.drag_pos = None
            logger.debug("用户操作: 鼠标非左键按下，不进行拖动。")

    def mouseMoveEvent(self, e):
        """
        鼠标移动事件处理函数。
        如果正在拖动窗口（drag_pos 不为 None），则根据鼠标移动距离更新窗口位置。
        """
        if self.drag_pos:
            new_pos = self.pos() + e.globalPosition().toPoint() - self.drag_pos
            self.move(new_pos)
            self.drag_pos = e.globalPosition().toPoint()
            # logger.debug(f"用户操作: 窗口拖动中，当前位置: ({new_pos.x()}, {new_pos.y()})") # 过于频繁，改为 debug
        pass

    def mouseReleaseEvent(self, _):
        """
        鼠标释放事件处理函数。
        重置拖动位置为 None，停止拖动，并记录最终位置。
        """
        if self.drag_pos:
            logger.info(f"用户操作: 鼠标释放，窗口拖动结束。最终位置: ({self.x()}, {self.y()})。")
        self.drag_pos = None

    def closeEvent(self, e):
        """
        窗口关闭事件处理函数。
        拦截关闭事件，不真正关闭窗口，而是隐藏窗口并将其最小化到托盘。
        """
        logger.info("用户操作: 用户点击窗口关闭按钮，窗口将隐藏到系统托盘。")
        e.ignore()  # 忽略关闭事件
        self.hide()  # 隐藏窗口


class SettingsDialog(QDialog):
    """
    设置对话框类。
    允许用户调整字体大小、透明度、行间距、时间偏移和窗口置顶状态。
    """

    def __init__(self, parent):
        """
        初始化 SettingsDialog 实例。
        根据父窗口的当前设置初始化控件值，并布局对话框。
        """
        super().__init__(parent)
        logger.info("用户界面: 设置对话框初始化。")
        self.setWindowTitle("设置")

        # 从父窗口获取当前设置值并记录
        self.font_size = parent.time_pt
        self.opacity = parent.opacity
        self.spacing = parent.spacing
        self.color = QColor(parent.color)
        self.manual_offset = parent.manual_offset
        logger.debug(f"设置对话框初始化值: 字体={self.font_size}, 透明度={self.opacity}, 行间距={self.spacing}, "
                     f"颜色={self.color.name()}, 手动偏移={self.manual_offset}")

        # 创建“窗口置顶”复选框
        self.chk_top = QCheckBox("窗口置顶")
        self.chk_top.setChecked(parent.topmost)
        self.chk_top.stateChanged.connect(
            lambda state: logger.debug(f"用户操作: '窗口置顶' 复选框状态改变为: {bool(state)}。"))
        logger.debug(f"用户界面: '窗口置顶' 复选框初始状态: {parent.topmost}。")

        # 创建滑块和微调框组合控件
        self.s_font, self.e_font = self._slider_spin(1.0, 64.0, self.font_size, "字号")
        self.s_opac, self.e_opac = self._slider_spin(30.0, 100.0, self.opacity, "透明度")
        self.s_space, self.e_space = self._slider_spin(0.0, 20.0, self.spacing, "行间距")
        self.s_off, self.e_off = self._slider_spin(-200.0, 200.0, self.manual_offset, "时间偏移")

        # 创建“选择颜色”按钮
        self.btn_col = QPushButton("选择颜色")
        self.btn_col.clicked.connect(self._choose_color)
        logger.debug("用户界面: '选择颜色' 按钮创建。")

        # 创建表单布局
        form = QFormLayout(self)
        form.addRow("字号：", self._wrap(self.s_font, self.e_font))
        form.addRow("透明度：", self._wrap(self.s_opac, self.e_opac))
        form.addRow("行间距：", self._wrap(self.s_space, self.e_space))
        form.addRow("时间偏移(秒)：", self._wrap(self.s_off, self.e_off))
        form.addRow(self.chk_top)
        form.addRow(self.btn_col)

        # 创建标准对话框按钮（确定和取消）
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        form.addRow(btns)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        logger.info("用户界面: 设置对话框 UI 布局完成。")

    def _slider_spin(self, mn, mx, val, name):
        """
        创建并返回一个滑块 (QSlider) 和一个浮点微调框 (QDoubleSpinBox) 的组合。
        滑块的值与微调框同步，并进行 10 倍缩放以支持浮点数。
        增加日志记录每次值变化。
        """
        s = QSlider(Qt.Horizontal)
        s.setRange(int(mn * 10), int(mx * 10))
        s.setValue(int(val * 10))
        s.setFixedWidth(160)
        # 连接滑块值改变信号到微调框，并记录
        s.valueChanged.connect(lambda v: (self.e_font.setValue(v / 10) if name == "字号" else None,
                                          self.e_opac.setValue(v / 10) if name == "透明度" else None,
                                          self.e_space.setValue(v / 10) if name == "行间距" else None,
                                          self.e_off.setValue(v / 10) if name == "时间偏移" else None,
                                          logger.debug(f"用户操作: 设置对话框 - 滑块 '{name}' 值改变为: {v / 10}"))[-1])

        e = QDoubleSpinBox()
        e.setDecimals(1)
        e.setRange(mn, mx)
        e.setValue(val)
        e.setFixedWidth(60)
        # 连接微调框值改变信号到滑块，并记录
        e.valueChanged.connect(lambda v: (s.setValue(int(v * 10)),
                                          logger.debug(f"用户操作: 设置对话框 - 微调框 '{name}' 值改变为: {v}"))[-1])
        logger.debug(f"用户界面: 创建滑块和微调框组合: '{name}', 范围[{mn}, {mx}], 初始值={val}。")
        return s, e

    def _wrap(self, s, e):
        """
        将滑块和微调框包装在一个水平布局的 QWidget 中，用于表单布局。
        """
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(0, 0, 0, 0)
        h.addWidget(s)
        h.addWidget(e)
        return w

    def _choose_color(self):
        """
        打开颜色选择对话框，让用户选择颜色。
        如果用户选择了有效颜色，则更新 self.color。
        """
        logger.info("用户操作: 点击 '选择颜色' 按钮，打开颜色选择对话框。")
        c = QColorDialog.getColor(self.color, self)  # 打开颜色对话框，初始颜色为当前颜色
        if c.isValid():
            self.color = c
            logger.info(f"用户操作: 颜色选择对话框 - 用户选择了新颜色: {self.color.name()}。")
        else:
            logger.info("用户操作: 颜色选择对话框已取消。")

    def accept(self):
        """
        当用户点击“确定”按钮时调用。
        从对话框控件中获取最终值，并更新对话框的属性。
        """
        # 实际值的获取在 _open_settings 中进行并记录，这里仅记录接受动作
        logger.debug("用户界面: 设置对话框 '确定' 按钮被点击。")
        super().accept()


# --- 主程序入口 ---
if __name__ == "__main__":
    # QApplication 实例必须在所有 Qt 对象之前创建
    app = QApplication(sys.argv)
    logger.info("程序启动: QApplication 实例创建成功。")

    # 创建 DigitalClock 主窗口实例
    win = DigitalClock()
    win.show()  # 显示主窗口
    logger.info("程序启动: 主窗口已显示。")

    # 启动应用程序事件循环，阻塞直到应用程序退出
    exit_code = app.exec()
    logger.info(f"程序生命周期: 应用程序事件循环结束，退出码: {exit_code}。")
    sys.exit(exit_code)