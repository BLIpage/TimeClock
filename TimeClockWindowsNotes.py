# -*- coding: utf-8 -*-
# 这是一个纯文字透明背景的数字桌面时钟应用程序。
# 它显示当前的日期和时间，并允许用户自定义时钟的字体大小、不透明度、颜色、
# 行间距以及时间偏移量。程序还支持窗口置顶，并提供系统托盘图标以便于管理。
# 时间同步功能通过 NTP（网络时间协议）实现，确保时间的准确性。

import sys  # 导入 sys 模块，用于访问系统相关的功能，如命令行参数和程序退出。
import json  # 导入 json 模块，用于处理 JSON 数据格式，以便保存和加载用户配置。
import time  # 导入 time 模块，用于时间相关的操作，如线程休眠。
import threading  # 导入 threading 模块，用于创建和管理多线程，实现后台 NTP 同步。
import datetime as dt  # 导入 datetime 模块，并重命名为 dt，用于处理日期和时间对象。
import email.utils  # 导入 email.utils 模块，用于解析 HTTP 响应头中的日期字符串。
import requests  # 导入 requests 模块，用于发送 HTTP 请求，以便从 NTP 服务器获取时间。
from pathlib import Path  # 导入 pathlib 模块的 Path 类，用于更方便地处理文件系统路径。
from platformdirs import user_config_dir  # 导入 platformdirs 模块的 user_config_dir 函数，用于获取跨平台的用户配置目录。
import logging  # 导入 logging 模块，用于实现应用程序的日志记录功能。
import os  # 导入 os 模块，虽然在此版本中直接用于文件操作的场景减少，但通常用于更低级别的操作系统交互，这里保留以备不时之需。

# PySide6 是 Qt for Python 的官方绑定库，用于创建图形用户界面。
# QtCore 模块包含核心的非 GUI 功能，如信号槽、定时器、线程等。
from PySide6.QtCore import Qt, QTimer, QPoint
# QtGui 模块包含图形相关的类，如字体、颜色、图标等。
from PySide6.QtGui import QFont, QColor, QFontMetrics, QIcon
# QtWidgets 模块包含各种 GUI 控件和布局管理器。
from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout,
    QMenu, QSlider, QDoubleSpinBox, QColorDialog, QSystemTrayIcon,
    QPushButton, QFormLayout, QStyle, QCheckBox,
    QDialog, QDialogButtonBox
)

# --- 路径设置 ---
# 定义应用程序的名称，这将作为配置和日志文件存放目录的一部分。
APP_NAME = "TimeClock"

# 获取用户配置目录的路径。
# user_config_dir(APP_NAME, "TimeClock") 会在不同操作系统上返回合适的配置路径，
# 例如在 Windows 上可能是 C:\Users\<用户名>\AppData\Roaming\TimeClock\TimeClock。
CONFIG_DIR = Path(user_config_dir(APP_NAME, "TimeClock"))
# 确保配置目录存在。如果目录不存在，就创建它，parents=True 确保父目录也会被创建，exist_ok=True 避免目录已存在时报错。
CONFIG_DIR.mkdir(parents=True, exist_ok=True)

# 构造配置文件的完整路径。
CONFIG_FILE = CONFIG_DIR / "config.json"

# 定义日志文件存放的子目录名称。
LOG_DIR = CONFIG_DIR / "Logs"
# 确保日志目录存在。
LOG_DIR.mkdir(parents=True, exist_ok=True)
# 构造当前日志文件的完整路径。文件名使用当前的日期和时间戳，确保每次程序启动都创建一个新的日志文件。
# dt.datetime.now().strftime('%Y%m%d_%H%M%S') 将当前时间格式化为“年月日_时分秒”的字符串。
LOG_FILE = LOG_DIR / f"{dt.datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

# 定义时钟图标文件的路径。Path(__file__).with_name("clock.ico") 表示与当前 Python 脚本在同一目录下的 "clock.ico" 文件。
ICON_PATH = Path(__file__).with_name("clock.ico")
# 定义用于 NTP 时间同步的 URL。这是一个提供当前准确时间的在线服务。
SYNC_URL = "https://time.is/just"

# --- 日志配置 ---
# 配置日志系统的基本设置。
logging.basicConfig(
    # 设置日志记录的最低级别。只有级别等于或高于此设置的消息才会被处理。
    # logging.INFO 表示会记录 INFO, WARNING, ERROR, CRITICAL 级别的消息。
    # 在开发调试阶段，可以将其改为 logging.DEBUG 以获取更详细的内部运行信息。
    level=logging.INFO,
    # 定义日志消息的输出格式。
    # %(asctime)s: 日志记录时间（例如：2023-10-27 10:30:00,123）。
    # %(levelname)s: 日志级别名称（例如：INFO, DEBUG, ERROR）。
    # %(filename)s:%(lineno)d: 记录日志的代码所在的文件名和行号，方便定位问题。
    # %(message)s: 日志的具体消息内容。
    format='%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
    # 定义日志消息将发送到哪里（处理器）。
    handlers=[
        # 文件处理器：将日志消息写入到指定的文件中。
        # LOG_FILE 是上面定义的日志文件路径。encoding='utf-8' 确保中文内容能正确写入和显示。
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        # 流处理器：将日志消息输出到标准输出流（通常是控制台）。
        # sys.stdout 表示输出到控制台，方便实时查看程序运行状态。
        logging.StreamHandler(sys.stdout)
    ]
)
# 获取一个日志记录器实例。建议使用 __name__ 作为记录器名称，这会根据模块名自动生成记录器层次结构。
# 所有通过这个 logger 实例发出的日志消息都会遵循上面basicConfig的配置。
logger = logging.getLogger(__name__)


# --- 全局异常处理 ---
def handle_exception(exc_type, exc_value, exc_traceback):
    """
    这是一个全局异常处理函数，用于捕获任何未被程序内部 try-except 块处理的异常。
    当程序发生未预料的崩溃时，这个函数会被调用，确保错误信息被记录下来。
    """
    # 检查异常类型是否是 KeyboardInterrupt (通常是用户按下 Ctrl+C 导致的)。
    if issubclass(exc_type, KeyboardInterrupt):
        # 如果是 KeyboardInterrupt，调用 Python 默认的异常处理钩子，
        # 让程序正常退出，避免将其记录为错误。
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    # 对于所有其他未捕获的异常，以 CRITICAL 级别记录到日志中。
    # exc_info=(exc_type, exc_value, exc_traceback) 参数非常重要，它会包含完整的 Python 异常回溯信息，
    # 对于调试和定位问题至关重要。
    logger.critical("程序发生未捕获的异常！", exc_info=(exc_type, exc_value, exc_traceback))
    # 在记录完异常后，强制退出程序。这有助于防止程序在不确定的错误状态下继续运行。
    sys.exit(1)


# 将自定义的异常处理函数设置为 Python 的全局异常钩子。
# 这样，每当有未处理的异常发生时，Python 解释器就会调用 handle_exception 函数。
sys.excepthook = handle_exception


# --- 时间同步 ---
def fetch_ntp():
    """
    通过 HTTP 请求从预定义的 NTP 服务器 URL 获取当前的网络时间。
    它尝试解析 HTTP 响应头中的 'Date' 字段来获取时间。
    如果获取失败（例如超时、连接错误或响应头中没有日期），它将回退到使用本地系统的 UTC 时间。
    """
    logger.info("NTP 同步: 尝试从 NTP 服务器获取时间...")  # 记录开始获取 NTP 时间的操作。
    try:
        # 发送一个 HEAD 请求到 SYNC_URL。HEAD 请求只获取响应头，不下载整个页面内容，效率更高。
        # timeout=5 设置了请求的超时时间为 5 秒。
        r = requests.head(SYNC_URL, timeout=5)
        # 检查响应头中是否存在 'Date' 字段。HTTP 响应的 'Date' 字段通常包含服务器当前的 GMT/UTC 时间。
        if "Date" in r.headers:
            # 使用 email.utils.parsedate_to_datetime 解析 'Date' 字符串为 datetime 对象。
            ntp_time = email.utils.parsedate_to_datetime(r.headers["Date"])
            # 记录成功获取的 NTP 时间，使用 ISO 格式方便阅读和调试。
            logger.info(f"NTP 同步: 成功获取 NTP 时间: {ntp_time.isoformat()}")
            return ntp_time  # 返回解析到的 NTP 时间。
        else:
            # 如果响应头中没有 'Date' 字段，发出警告。
            logger.warning(f"NTP 同步: 从 {SYNC_URL} 接收到响应，但响应头中未找到 'Date' 字段。")
    except requests.exceptions.Timeout:
        # 捕获请求超时异常，记录错误信息并包含回溯。
        logger.error(f"NTP 同步: 从 {SYNC_URL} 获取 NTP 时间超时（5秒）。", exc_info=True)
    except requests.exceptions.ConnectionError as e:
        # 捕获连接错误异常（例如网络不通、服务器拒绝连接），记录错误信息并包含回溯。
        logger.error(f"NTP 同步: 连接到 {SYNC_URL} 失败: {e}", exc_info=True)
    except requests.exceptions.RequestException as e:
        # 捕获所有其他 requests 相关的通用异常，记录错误信息并包含回溯。
        logger.error(f"NTP 同步: HTTP 请求 {SYNC_URL} 失败: {e}", exc_info=True)
    except Exception as e:
        # 捕获解析时间过程中可能发生的任何其他未知异常，记录错误信息并包含回溯。
        logger.error(f"NTP 同步: 解析 NTP 时间时发生未知错误: {e}", exc_info=True)

    # 如果上述任何步骤失败，则回退到使用本地系统的 UTC 时间作为替代。
    local_utc_time = dt.datetime.now(dt.UTC)
    logger.info(f"NTP 同步: 回退到本地 UTC 时间: {local_utc_time.isoformat()}")  # 记录回退到本地时间的行为。
    return local_utc_time  # 返回本地 UTC 时间。


# --- DigitalClock 类 ---
class DigitalClock(QWidget):
    """
    DigitalClock 类继承自 PySide6.QtWidgets.QWidget，是桌面数字时钟的主窗口。
    它负责显示当前时间、处理用户交互（如拖动、设置）、加载/保存配置以及管理 NTP 同步。
    """

    def __init__(self):
        """
        初始化 DigitalClock 实例。
        这个构造函数会设置时钟的各种默认属性，创建并布局用户界面元素，
        加载保存的用户配置，并启动定时器和 NTP 同步的后台线程。
        """
        super().__init__()  # 调用父类 QWidget 的构造函数进行初始化。
        logger.info("程序启动: DigitalClock 应用程序初始化。")  # 记录应用程序启动的起始点。

        # --- 时钟属性的默认值设置 ---
        self.time_pt = 10.0  # 时钟文字的字体大小（磅值）。
        self.spacing = 2.0  # 日期和时间行之间的垂直间距（像素）。
        self.opacity = 90.0  # 窗口的不透明度，范围 0.0 到 100.0。
        self.topmost = True  # 布尔值，指示窗口是否始终保持在其他窗口之上。
        self.color = QColor("white")  # 时钟文字的颜色，默认为白色。
        self.offset = 0.0  # 由 NTP 同步计算出的时间偏移量（秒），用于校准本地时间。
        self.manual_offset = 0.0  # 用户在设置中手动输入的时间偏移量（秒）。
        self.drag_pos = None  # 用于记录鼠标按下时的全局位置，以实现窗口拖动功能。

        # --- 窗口属性设置 ---
        logger.debug("窗口配置: 设置 Qt 窗口标志和属性。")
        self.setWindowFlags(Qt.FramelessWindowHint)  # 设置窗口为无边框样式，意味着没有标题栏和标准边框。
        self.setAttribute(Qt.WA_TranslucentBackground)  # 设置窗口背景为透明，使得只有文字可见。

        # --- UI 元素创建 ---
        # 创建显示日期的 QLabel 控件。
        self.date_lbl = QLabel("--")
        # 创建显示时间的 QLabel 控件。
        self.time_lbl = QLabel("--")
        # 对两个标签进行通用设置。
        for lbl in (self.date_lbl, self.time_lbl):
            lbl.setAlignment(Qt.AlignRight)  # 设置文本右对齐。
            lbl.setAttribute(Qt.WA_TranslucentBackground)  # 确保标签自身的背景也是透明的。
        logger.debug("UI 组件: 日期和时间 QLabel 创建成功。")

        # --- 布局设置 ---
        # 创建一个垂直布局管理器，并将当前窗口设置为其父对象。
        self.vbox = QVBoxLayout(self)
        # 设置布局的内边距（左、上、右、下）。
        self.vbox.setContentsMargins(12, 8, 12, 8)
        # 将日期和时间标签添加到垂直布局中。
        self.vbox.addWidget(self.date_lbl)
        self.vbox.addWidget(self.time_lbl)
        logger.debug("UI 布局: QVBoxLayout 设置完成，标签已添加到布局中。")

        # --- 系统托盘图标设置 ---
        # 尝试加载自定义时钟图标。
        icon_path_str = str(ICON_PATH)
        if ICON_PATH.exists():  # 检查图标文件是否存在。
            icon = QIcon(icon_path_str)  # 如果存在，创建 QIcon 对象。
            logger.debug(f"资源加载: 成功加载托盘图标: {icon_path_str}")
        else:
            # 如果图标文件不存在，使用系统提供的默认电脑图标作为替代，并发出警告。
            icon = self.style().standardIcon(QStyle.SP_ComputerIcon)
            logger.warning(f"资源加载: 托盘图标文件 '{icon_path_str}' 不存在，使用系统默认图标。")

        # 创建系统托盘图标实例。
        self.tray = QSystemTrayIcon(icon, self)
        # 设置托盘图标的上下文菜单（右键菜单）。
        self.tray.setContextMenu(self._build_menu())
        # 连接托盘图标的 'activated' 信号到自定义的处理函数。
        # 当用户点击托盘图标时，会触发这个信号，reason 参数表示激活原因（如点击、双击、右键）。
        self.tray.activated.connect(self._handle_tray_activated)
        # 显示系统托盘图标。
        self.tray.show()
        logger.info("用户界面: 系统托盘图标创建并显示。")

        # --- 初始化与启动 ---
        self._load()  # 从配置文件加载之前保存的设置。
        self._apply_style()  # 根据当前设置应用字体、颜色、透明度等样式。

        # 创建一个 QTimer 定时器实例。
        self.timer = QTimer(self, timeout=self._tick)
        # 启动定时器，每 1000 毫秒（1秒）触发一次 _tick 方法来更新时间显示。
        self.timer.start(1000)
        logger.info("内部逻辑: 时间更新 QTimer 启动 (1000ms 间隔)。")

        # 启动一个后台线程来执行 NTP 时间同步。
        # daemon=True 将此线程设置为守护线程，意味着当主程序退出时，此线程也会自动终止。
        threading.Thread(target=self._ntp_loop, daemon=True).start()
        logger.info("内部逻辑: NTP 同步后台线程启动。")

    def _handle_tray_activated(self, reason):
        """
        处理系统托盘图标的激活事件（例如用户的点击或右键操作）。
        根据激活原因，执行相应的显示/隐藏窗口操作，并记录用户行为。
        """
        # QSystemTrayIcon.Trigger 表示用户通常的点击（如左键单击）。
        if reason == QSystemTrayIcon.Trigger:
            if self.isHidden():  # 如果窗口当前是隐藏状态。
                self.showNormal()  # 显示正常大小的窗口。
                logger.info("用户操作: 通过托盘点击显示主窗口。")
            else:  # 如果窗口当前是可见状态。
                self.hide()  # 隐藏窗口。
                logger.info("用户操作: 通过托盘点击隐藏主窗口。")
        # QSystemTrayIcon.Context 表示用户右键点击托盘图标。
        elif reason == QSystemTrayIcon.Context:
            logger.debug("用户操作: 右键点击托盘图标，上下文菜单显示。")
        else:
            # 记录其他不常见的托盘激活原因。
            logger.debug(f"用户操作: 托盘图标被激活，原因: {reason}。")

    def _now(self):
        """
        计算并返回当前准确的本地时间 (UTC+8)。
        这个时间是基于本地系统 UTC 时间，并加上 NTP 同步计算出的偏移量
        以及用户在设置中手动输入的偏移量。
        """
        current_utc = dt.datetime.now(dt.UTC)  # 获取当前精确的 UTC 时间。
        # 调整 UTC 时间：加上 NTP 偏移和用户手动偏移。
        adjusted_utc = current_utc + dt.timedelta(seconds=self.offset + self.manual_offset)
        # 将调整后的 UTC 时间转换为东八区（UTC+8）的本地时间。
        local_time = adjusted_utc.astimezone(dt.timezone(dt.timedelta(hours=8)))  # 假设目标时区是 UTC+8
        # 这行日志会每秒触发，如果开启 DEBUG 级别，会产生大量日志，通常在需要极端详细调试时才启用。
        # logger.debug(f"内部逻辑: _now() 计算结果 - 本地时间: {local_time.isoformat()} (UTC+8)")
        return local_time  # 返回计算出的本地时间。

    def _tick(self):
        """
        这是定时器每秒触发的回调函数。
        它负责更新日期和时间显示标签的文本，并根据文本内容动态调整窗口的大小，以确保显示完整且不裁剪。
        """
        now = self._now()  # 获取当前校准后的时间。
        # 格式化日期和时间字符串。
        date_text = f"{now.year}年{now.month}月{now.day}日"
        time_text = now.strftime("%H:%M:%S")

        self.date_lbl.setText(date_text)  # 更新日期标签的文本。
        self.time_lbl.setText(time_text)  # 更新时间标签的文本。
        # 这行日志会每秒触发，如果设置为 DEBUG，会产生大量日志，通常在需要极端详细调试时才启用。
        # logger.debug(f"UI 更新: 时间显示刷新 - 日期: '{date_text}', 时间: '{time_text}'")

        # 计算窗口需要的宽度：取日期和时间文本中较长者的像素宽度，并加上固定的左右边距。
        w = max(
            QFontMetrics(self.date_lbl.font()).horizontalAdvance(self.date_lbl.text()),
            QFontMetrics(self.time_lbl.font()).horizontalAdvance(self.time_lbl.text())
        ) + 24  # 24像素用于左右内边距 (12+12)。
        # 计算窗口需要的高度：日期文本高度 + 时间文本高度 + 行间距 + 上下边距。
        h = (
                self._font_h(self.time_pt - 1)  # 日期标签的字体高度 (通常比时间小1磅)。
                + self._font_h(self.time_pt)  # 时间标签的字体高度。
                + int(self.spacing)  # 日期和时间之间的行间距。
                + self.vbox.contentsMargins().top()  # 布局上边距。
                + self.vbox.contentsMargins().bottom()  # 布局下边距。
        )

        # 只有当计算出的宽度或高度与当前窗口的实际宽度或高度不同时，才重新设置窗口大小。
        # 这样做可以避免不必要的窗口重绘和日志记录，提高效率并减少日志噪音。
        if self.width() != w or self.height() != h:
            self.setFixedWidth(w)  # 设置窗口的固定宽度。
            self.setFixedHeight(h)  # 设置窗口的固定高度。
            logger.debug(f"UI 布局: 窗口大小已根据文本内容动态调整为: 宽度={w}, 高度={h}。")

    def _font_h(self, pt):
        """
        根据指定的磅值 (pt) 和预设字体 ("Noto Sans SC")，计算出该字体在像素上的实际高度。
        这有助于精确计算 UI 布局所需的高度。
        """
        f = QFont("Noto Sans SC")  # 创建一个 QFont 对象，指定字体家族为“思源黑体 SC”。
        f.setPointSizeF(pt)  # 设置字体大小为指定的磅值（可包含小数）。
        height = QFontMetrics(f).height() + 2  # 使用 QFontMetrics 获取字体在当前屏幕 DPI 下的像素高度，并额外增加 2 像素以防止文字底部被裁剪。
        logger.debug(f"字体计算: 磅值 {pt} 的 'Noto Sans SC' 字体高度为 {height} 像素。")
        return height  # 返回计算出的字体高度。

    def _apply_style(self):
        """
        根据 DigitalClock 实例当前的属性（字体大小、颜色、透明度、行间距、置顶状态），
        更新并应用到 UI 元素和窗口本身。
        """
        logger.info("UI 样式: 开始应用新的样式设置。")  # 记录开始应用样式操作。

        # 计算日期标签的字体大小：比时间标签小 1 磅，但最小不低于 1 磅。
        date_pt = max(self.time_pt - 1, 1)

        # 创建并设置日期标签的字体。
        f1 = QFont("Noto Sans SC")
        f1.setPointSizeF(date_pt)
        f1.setBold(True)  # 设置为粗体。
        self.date_lbl.setFont(f1)  # 应用字体到日期标签。

        # 创建并设置时间标签的字体。
        f2 = QFont("Noto Sans SC")
        f2.setPointSizeF(self.time_pt)
        f2.setBold(True)  # 设置为粗体。
        self.time_lbl.setFont(f2)  # 应用字体到时间标签。
        logger.debug(f"UI 样式: 字体已设置为 'Noto Sans SC'，日期字体大小: {date_pt}pt, 时间字体大小: {self.time_pt}pt。")

        # 生成 CSS 样式字符串，设置文字颜色和背景透明。
        css = f"color:{self.color.name()}; background: transparent;"
        self.date_lbl.setStyleSheet(css)  # 应用样式到日期标签。
        self.time_lbl.setStyleSheet(css)  # 应用样式到时间标签。
        logger.debug(f"UI 样式: 文字颜色设置为: {self.color.name()}。")

        self.vbox.setSpacing(int(self.spacing))  # 设置日期和时间标签之间的行间距。
        logger.debug(f"UI 样式: 行间距设置为: {int(self.spacing)} 像素。")

        self.setWindowOpacity(self.opacity / 100)  # 设置窗口的不透明度。Qt 的不透明度范围是 0.0（完全透明）到 1.0（完全不透明）。
        logger.debug(f"UI 样式: 窗口不透明度设置为: {self.opacity}%。")

        # --- 窗口置顶状态处理 ---
        # 获取当前窗口的标志。
        current_flags = self.windowFlags()
        # 根据 self.topmost 属性决定所需的窗口标志。
        # Qt.FramelessWindowHint 保持无边框。
        # Qt.WindowStaysOnTopHint 使窗口保持在最顶层，否则为 Qt.Widget (普通窗口)。
        desired_flags = Qt.FramelessWindowHint | (Qt.WindowStaysOnTopHint if self.topmost else Qt.Widget)

        # 只有当当前的窗口标志与期望的标志不同时，才重新设置。
        # 这样做可以避免不必要的窗口刷新和资源消耗，并减少日志噪音。
        if current_flags != desired_flags:
            self.setWindowFlags(desired_flags)  # 设置新的窗口标志。
            self.show()  # 调用 show() 来重新应用新的窗口标志。
            logger.info(f"UI 样式: 窗口置顶状态已更新为: {self.topmost}。")
        logger.info("UI 样式: 所有样式应用完成。")

    def _build_menu(self):
        """
        构建并返回系统托盘图标的右键上下文菜单。
        菜单包含“显示/隐藏时钟”、“设置”和“退出程序”选项。
        """
        logger.debug("用户界面: 正在构建系统托盘菜单。")
        m = QMenu()  # 创建一个空的 QMenu 实例。

        # 添加“显示/隐藏”动作。
        # lambda 函数根据窗口当前隐藏状态来调用 showNormal() 或 hide()。
        m.addAction("显示/隐藏", lambda: self.showNormal() if self.isHidden() else self.hide())
        # 添加“设置”动作，点击时调用 _open_settings 方法。
        m.addAction("设置", self._open_settings)
        m.addSeparator()  # 添加一个分隔线，用于视觉上的分组。
        # 添加“退出”动作，点击时调用 _exit 方法来关闭程序。
        m.addAction("退出", self._exit)
        logger.debug("用户界面: 系统托盘菜单构建完成。")
        return m  # 返回构建好的菜单。

    def _ntp_loop(self):
        """
        这是一个后台线程的主循环，用于定期执行 NTP 时间同步。
        它会每隔 10 分钟（600 秒）调用一次 fetch_ntp 函数来获取最新时间，并更新内部的时间偏移量。
        """
        logger.info("内部逻辑: NTP 同步循环线程启动。")  # 记录 NTP 循环线程的启动。
        while True:  # 无限循环，使线程持续运行。
            try:
                ntp_dt = fetch_ntp()  # 调用 fetch_ntp 函数获取 NTP 时间。
                current_utc = dt.datetime.now(dt.UTC)  # 获取当前本地系统的精确 UTC 时间。
                # 计算 NTP 时间与本地 UTC 时间之间的秒数差，作为时间校准的偏移量。
                self.offset = (ntp_dt - current_utc).total_seconds()
                # 记录更新后的 NTP 偏移量，精确到小数点后 6 位，方便精确调试。
                logger.info(f"内部逻辑: NTP 偏移量更新为: {self.offset:.6f} 秒。")
            except Exception as e:
                # 捕获 NTP 同步过程中可能发生的任何异常，并记录错误信息和回溯。
                logger.error(f"内部逻辑: NTP 同步循环中发生错误: {e}", exc_info=True)
            time.sleep(600)  # 线程休眠 600 秒（10 分钟），等待下一次同步。

    def _open_settings(self):
        """
        创建并显示设置对话框。
        当用户在设置对话框中点击“确定”并接受更改后，此方法会更新主时钟的属性，
        应用新样式，并保存到配置文件。它还会详细记录用户对设置的具体更改。
        """
        logger.info("用户操作: 点击 '设置'，打开设置对话框。")  # 记录用户打开设置对话框的行为。
        # 存储当前的所有设置值，以便稍后与用户更改后的新值进行比较。
        old_settings = {
            "font": self.time_pt,
            "opacity": self.opacity,
            "spacing": self.spacing,
            "color": self.color.name(),  # 将 QColor 转换为颜色名称字符串。
            "top": self.topmost,
            "offset": self.manual_offset
        }
        logger.debug(f"用户操作: 设置对话框打开前，当前设置为: {old_settings}")

        dlg = SettingsDialog(self)  # 创建 SettingsDialog 实例，并将当前 DigitalClock 实例作为其父窗口。
        # 显示对话框并进入事件循环。exec() 方法会阻塞，直到对话框被关闭。
        # 如果用户点击了“确定”，exec() 返回 QDialog.Accepted (非零值)。
        # 如果用户点击了“取消”或关闭对话框，exec() 返回 QDialog.Rejected (零)。
        if dlg.exec():
            logger.info("用户操作: 设置对话框已接受更改。")  # 记录用户接受更改。
            # --- 更新 DigitalClock 实例的属性为对话框中设置的新值 ---
            self.time_pt = dlg.font_size
            self.opacity = dlg.opacity
            self.spacing = dlg.spacing
            self.color = dlg.color
            self.manual_offset = dlg.manual_offset
            self.topmost = dlg.chk_top.isChecked()  # 获取“窗口置顶”复选框的最终状态。

            # --- 详细记录用户更改了哪些设置 ---
            new_settings = {
                "font": self.time_pt,
                "opacity": self.opacity,
                "spacing": self.spacing,
                "color": self.color.name(),
                "top": self.topmost,
                "offset": self.manual_offset
            }
            changed_items = []  # 用于存储所有发生更改的设置项描述。
            for key, new_val in new_settings.items():
                old_val = old_settings[key]
                # 比较旧值和新值。对于浮点数，直接比较可能存在精度问题，但在这里对于显示用途通常足够。
                if old_val != new_val:
                    changed_items.append(f"'{key}': '{old_val}' -> '{new_val}'")

            if changed_items:
                # 如果有任何设置被更改，则记录详细的更改内容。
                logger.info(f"用户操作: 检测到设置更改: {'; '.join(changed_items)}")
            else:
                # 如果用户点击了确定但实际上没有改变任何设置。
                logger.info("用户操作: 设置对话框被接受，但未检测到任何设置更改。")

            self._apply_style()  # 立即应用这些新的样式设置到时钟显示。
            self._save()  # 将当前所有的设置（包括更改后的）保存到配置文件中。
        else:
            logger.info("用户操作: 设置对话框已取消更改。")  # 记录用户取消更改。

    def _save(self):
        """
        将当前 DigitalClock 实例的所有关键设置（包括字体、透明度、颜色、位置等）
        序列化为 JSON 格式，并保存到配置文件中。
        """
        logger.info("配置管理: 尝试保存当前配置到文件。")  # 记录开始保存配置。
        try:
            # 构建一个字典，包含所有要保存的设置项。
            data = dict(
                font=self.time_pt,
                opacity=self.opacity,
                spacing=self.spacing,
                color=self.color.name(),  # 将 QColor 对象转换为其颜色名称字符串（如 "#FFFFFF"）。
                top=self.topmost,
                offset=self.manual_offset,
                pos=[self.x(), self.y()]  # 保存窗口当前的 X 和 Y 坐标，以便下次启动时恢复位置。
            )
            # 将字典转换为 JSON 格式的字符串，并写入文件。
            # indent=2 使 JSON 格式化，方便阅读。
            # ensure_ascii=False 确保非 ASCII 字符（如中文）能直接写入，而不是转义编码。
            # encoding='utf-8' 指定文件编码。
            CONFIG_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')
            logger.info(f"配置管理: 配置已成功保存到 '{CONFIG_FILE}'。")  # 记录保存成功。
            logger.debug(f"配置管理: 保存的配置数据:\n{json.dumps(data, indent=2, ensure_ascii=False)}")  # 详细记录保存的数据内容。
        except Exception as e:
            # 捕获保存过程中可能发生的任何异常，记录错误信息和回溯。
            logger.error(f"配置管理: 保存配置失败: {e}", exc_info=True)

    def _load(self):
        """
        从 JSON 配置文件中加载应用程序的设置。
        如果配置文件不存在、内容无效或加载失败，则使用默认的程序设置，并记录相应的警告或错误。
        """
        logger.info("配置管理: 尝试从文件加载配置。")  # 记录开始加载配置。
        if CONFIG_FILE.exists():  # 检查配置文件是否存在。
            try:
                raw_data = CONFIG_FILE.read_text(encoding='utf-8')  # 读取文件内容。
                d = json.loads(raw_data)  # 解析 JSON 字符串为 Python 字典。

                logger.debug(f"配置管理: 原始配置数据:\n{raw_data}")  # 记录原始配置文件内容，方便调试。

                # 从加载的字典中获取各项设置。使用 .get() 方法，如果键不存在，则返回默认值（self.属性当前值）。
                self.time_pt = d.get("font", self.time_pt)
                self.opacity = d.get("opacity", self.opacity)
                self.spacing = d.get("spacing", self.spacing)
                self.color = QColor(d.get("color", self.color.name()))  # 从颜色名称字符串创建 QColor 对象。
                self.topmost = d.get("top", self.topmost)
                self.manual_offset = d.get("offset", 0.0)

                # 处理窗口位置的加载。
                if pos_list := d.get("pos"):  # 使用海象运算符 := (Python 3.8+) 赋值并检查值。
                    # 验证 pos_list 是否是一个包含两个数值的列表。
                    if isinstance(pos_list, list) and len(pos_list) == 2:
                        try:
                            # 移动窗口到保存的位置。QPoint 需要整数坐标。
                            self.move(QPoint(int(pos_list[0]), int(pos_list[1])))
                            logger.info(f"配置管理: 成功加载窗口位置: x={pos_list[0]}, y={pos_list[1]}。")
                        except ValueError:
                            # 如果列表中的值无法转换为整数，记录错误。
                            logger.error(f"配置管理: 配置文件中位置数据无效（非整数）: {pos_list}，将使用默认位置。",
                                         exc_info=True)
                    else:
                        # 如果 'pos' 键存在但格式不正确，记录警告。
                        logger.warning(
                            f"配置管理: 配置文件中 'pos' 格式不正确: {pos_list}，应为 [x, y] 列表，将使用默认位置。")
                else:
                    # 如果配置文件中没有 'pos' 键，也记录一下，表示将使用默认位置（或系统决定的位置）。
                    logger.debug("配置管理: 配置文件中未找到 'pos' 键，将使用默认位置。")

                logger.info(f"配置管理: 配置已成功从 '{CONFIG_FILE}' 加载。")  # 记录加载成功。
                logger.debug(
                    f"配置管理: 加载后的配置属性: font={self.time_pt}, opacity={self.opacity}, spacing={self.spacing}, "
                    f"color={self.color.name()}, top={self.topmost}, offset={self.manual_offset}")
            except json.JSONDecodeError as e:
                # 捕获 JSON 解析错误，记录详细错误信息和回溯。
                logger.error(f"配置管理: 加载配置失败，JSON 解析错误: {e}", exc_info=True)
                logger.warning("配置管理: 无法解析配置文件，将使用默认配置。")  # 警告用户将使用默认配置。
            except Exception as e:
                # 捕获加载过程中可能发生的其他所有未知异常，记录错误信息和回溯。
                logger.error(f"配置管理: 加载配置时发生未知错误: {e}", exc_info=True)
                logger.warning("配置管理: 加载配置文件失败，将使用默认配置。")  # 警告用户将使用默认配置。
        else:
            # 如果配置文件本身就不存在，记录警告。
            logger.warning(f"配置管理: 配置文件 '{CONFIG_FILE}' 不存在，将使用默认配置。")

    def _exit(self):
        """
        保存当前应用程序的所有设置，然后优雅地退出应用程序。
        这是通过托盘菜单“退出”选项触发的程序结束流程。
        """
        logger.info("用户操作: 用户选择退出应用程序。")  # 记录用户主动退出操作。
        self._save()  # 调用 _save 方法保存当前所有设置。
        QApplication.quit()  # 发送退出信号给 QApplication，开始关闭应用程序。
        logger.info("程序生命周期: 应用程序已正常退出。")  # 记录应用程序的最终退出。

    def paintEvent(self, e):
        """
        重写 Qt 窗口的 paintEvent 方法。
        由于时钟窗口被设置为透明背景（Qt.WA_TranslucentBackground），
        Qt 会负责处理背景透明，我们不需要在这里进行任何自定义的绘制操作。
        因此，此方法为空。
        """
        # 这行日志会非常频繁地触发，如果设置为 DEBUG 会产生海量日志，通常在极端需要调试渲染问题时才启用。
        # logger.debug("UI 绘制: paintEvent 被调用，跳过绘制（透明背景）。")
        pass

    def mousePressEvent(self, e):
        """
        处理鼠标按下事件。
        如果用户按下鼠标左键，此方法会记录鼠标的当前全局位置，
        这是窗口拖动操作的起始点。
        """
        if e.button() == Qt.LeftButton:  # 检查是否是鼠标左键按下。
            # 获取鼠标事件发生时，鼠标指针的全局坐标，并转换为 QPoint 对象。
            self.drag_pos = e.globalPosition().toPoint()
            logger.debug(f"用户操作: 鼠标左键按下，开始窗口拖动。起始位置: ({self.drag_pos.x()}, {self.drag_pos.y()})。")
        else:
            self.drag_pos = None  # 如果不是左键按下，则不进行拖动，将 drag_pos 重置为 None。
            logger.debug("用户操作: 鼠标非左键按下，不进行拖动。")

    def mouseMoveEvent(self, e):
        """
        处理鼠标移动事件。
        如果用户正在拖动窗口（即 self.drag_pos 不为 None），此方法会根据鼠标的移动距离，
        实时更新窗口在屏幕上的位置，实现平滑的拖动效果。
        """
        if self.drag_pos:  # 检查是否处于拖动模式。
            # 计算新的窗口位置：当前窗口位置 + (当前鼠标全局位置 - 鼠标按下时的全局位置)。
            new_pos = self.pos() + e.globalPosition().toPoint() - self.drag_pos
            self.move(new_pos)  # 移动窗口到新的位置。
            self.drag_pos = e.globalPosition().toPoint()  # 更新 drag_pos 为当前的鼠标全局位置，以便下一次移动的计算。
            # 这行日志会非常频繁地触发，如果设置为 DEBUG 会产生海量日志，通常不建议在正常运行时开启。
            # logger.debug(f"用户操作: 窗口拖动中，当前位置: ({new_pos.x()}, {new_pos.y()})")
        pass  # 如果不处于拖动模式，不执行任何操作。

    def mouseReleaseEvent(self, _):
        """
        处理鼠标释放事件。
        当用户释放鼠标按键时，此方法会结束窗口拖动操作，并记录窗口最终停留的位置。
        """
        if self.drag_pos:  # 检查是否之前处于拖动模式。
            # 记录窗口拖动结束时的最终位置。
            logger.info(f"用户操作: 鼠标释放，窗口拖动结束。最终位置: ({self.x()}, {self.y()})。")
        self.drag_pos = None  # 将 drag_pos 重置为 None，表示拖动操作已结束。

    def closeEvent(self, e):
        """
        重写 Qt 窗口的 closeEvent 方法。
        当用户点击窗口的关闭按钮时，此方法会被调用。
        我们选择拦截这个关闭事件，不真正关闭窗口，而是将其隐藏并最小化到系统托盘，
        提供一个更友好的用户体验。
        """
        logger.info("用户操作: 用户点击窗口关闭按钮，窗口将隐藏到系统托盘。")  # 记录用户尝试关闭窗口的行为。
        e.ignore()  # 忽略默认的关闭事件处理，阻止窗口被真正关闭。
        self.hide()  # 隐藏窗口，使其从屏幕上消失。


# --- SettingsDialog 类 ---
class SettingsDialog(QDialog):
    """
    SettingsDialog 类继承自 PySide6.QtWidgets.QDialog，是用于配置时钟设置的对话框。
    它允许用户调整字体大小、不透明度、行间距、时间偏移和窗口置顶等参数，
    并通过滑块、微调框和颜色选择器提供直观的交互。
    """

    def __init__(self, parent):
        """
        初始化 SettingsDialog 实例。
        这个构造函数会根据父窗口（DigitalClock 实例）的当前设置来初始化对话框中的控件值，
        并构建整个设置界面的布局。
        """
        super().__init__(parent)  # 调用父类 QDialog 的构造函数，并设置父窗口。
        logger.info("用户界面: 设置对话框初始化。")  # 记录设置对话框的初始化。
        self.setWindowTitle("设置")  # 设置对话框的标题栏文本。

        # --- 从父窗口获取并记录当前设置值，作为对话框控件的初始值 ---
        self.font_size = parent.time_pt
        self.opacity = parent.opacity
        self.spacing = parent.spacing
        self.color = QColor(parent.color)  # 复制 QColor 对象，避免直接修改父窗口的颜色。
        self.manual_offset = parent.manual_offset
        logger.debug(f"设置对话框初始化值: 字体={self.font_size}, 透明度={self.opacity}, 行间距={self.spacing}, "
                     f"颜色={self.color.name()}, 手动偏移={self.manual_offset}。")

        # --- 创建“窗口置顶”复选框 ---
        self.chk_top = QCheckBox("窗口置顶")
        self.chk_top.setChecked(parent.topmost)  # 根据父窗口的当前置顶状态设置复选框的初始选中状态。
        # 连接复选框的 stateChanged 信号，当用户改变复选框状态时，记录 DEBUG 级别的日志。
        self.chk_top.stateChanged.connect(
            lambda state: logger.debug(f"用户操作: '窗口置顶' 复选框状态改变为: {bool(state)}。"))
        logger.debug(f"用户界面: '窗口置顶' 复选框创建，初始状态: {parent.topmost}。")

        # --- 创建各种设置项的滑块和微调框组合控件 ---
        # _slider_spin 方法会创建一对滑块和微调框，并设置它们的范围、初始值和名称。
        self.s_font, self.e_font = self._slider_spin(1.0, 64.0, self.font_size, "字号")
        self.s_opac, self.e_opac = self._slider_spin(30.0, 100.0, self.opacity, "透明度")
        self.s_space, self.e_space = self._slider_spin(0.0, 20.0, self.spacing, "行间距")
        self.s_off, self.e_off = self._slider_spin(-200.0, 200.0, self.manual_offset, "时间偏移")

        # --- 创建“选择颜色”按钮 ---
        self.btn_col = QPushButton("选择颜色")
        # 连接按钮的 clicked 信号到 _choose_color 方法，点击时会打开颜色选择对话框。
        self.btn_col.clicked.connect(self._choose_color)
        logger.debug("用户界面: '选择颜色' 按钮创建。")

        # --- 构建表单布局 ---
        form = QFormLayout(self)  # 创建一个 QFormLayout，用于以“标签-控件”对的形式排列设置项。
        # 添加各项设置到表单布局中。_wrap 方法将滑块和微调框包装在一个水平布局中。
        form.addRow("字号：", self._wrap(self.s_font, self.e_font))
        form.addRow("透明度：", self._wrap(self.s_opac, self.e_opac))
        form.addRow("行间距：", self._wrap(self.s_space, self.e_space))
        form.addRow("时间偏移(秒)：", self._wrap(self.s_off, self.e_off))
        form.addRow(self.chk_top)  # 添加“窗口置顶”复选框。
        form.addRow(self.btn_col)  # 添加“选择颜色”按钮。

        # --- 添加标准对话框按钮（确定/取消） ---
        # QDialogButtonBox 提供了一组标准的按钮，这里是“确定”和“取消”按钮。
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        form.addRow(btns)  # 将按钮添加到表单布局的底部。
        # 连接按钮的 accepted 信号到对话框的 accept() 槽，点击“确定”时关闭对话框并返回 Accepted。
        btns.accepted.connect(self.accept)
        # 连接按钮的 rejected 信号到对话框的 reject() 槽，点击“取消”时关闭对话框并返回 Rejected。
        btns.rejected.connect(self.reject)
        logger.info("用户界面: 设置对话框 UI 布局完成。")

    def _slider_spin(self, mn, mx, val, name):
        """
        创建一个滑块 (QSlider) 和一个浮点微调框 (QDoubleSpinBox) 的组合控件。
        这两个控件的值会相互同步。滑块的值会乘以 10 以支持浮点数的调节（因为 QSlider 只能处理整数）。
        同时，此方法会记录用户每次通过滑块或微调框调整数值的 DEBUG 级别日志。
        """
        s = QSlider(Qt.Horizontal)  # 创建一个水平方向的滑块。
        s.setRange(int(mn * 10), int(mx * 10))  # 设置滑块的范围，将浮点范围乘以 10 转换为整数范围。
        s.setValue(int(val * 10))  # 设置滑块的初始值，同样乘以 10。
        s.setFixedWidth(160)  # 设置滑块的固定宽度。
        # 连接滑块的 valueChanged 信号。当滑块的值改变时，lambda 函数会被调用。
        # 这个 lambda 函数会更新对应的 QDoubleSpinBox 的值（除以 10 还原浮点数），
        # 并记录 DEBUG 级别的日志，显示滑块的新值。
        s.valueChanged.connect(lambda v: (
            self.e_font.setValue(v / 10) if name == "字号" else None,
            self.e_opac.setValue(v / 10) if name == "透明度" else None,
            self.e_space.setValue(v / 10) if name == "行间距" else None,
            self.e_off.setValue(v / 10) if name == "时间偏移" else None,
            logger.debug(f"用户操作: 设置对话框 - 滑块 '{name}' 值改变为: {v / 10}"))[
            -1])  # [-1] 是为了让 lambda 表达式能返回一个值（PySide6 signal slot 要求）。

        e = QDoubleSpinBox()  # 创建一个浮点微调框。
        e.setDecimals(1)  # 设置微调框显示一位小数。
        e.setRange(mn, mx)  # 设置微调框的浮点数值范围。
        e.setValue(val)  # 设置微调框的初始浮点数值。
        e.setFixedWidth(60)  # 设置微调框的固定宽度。
        # 连接微调框的 valueChanged 信号。当微调框的值改变时，lambda 函数会被调用。
        # 这个 lambda 函数会更新对应的 QSlider 的值（乘以 10 转换为整数），
        # 并记录 DEBUG 级别的日志，显示微调框的新值。
        e.valueChanged.connect(lambda v: (
            s.setValue(int(v * 10)),
            logger.debug(f"用户操作: 设置对话框 - 微调框 '{name}' 值改变为: {v}"))[-1])

        logger.debug(f"用户界面: 创建滑块和微调框组合: '{name}', 范围[{mn}, {mx}], 初始值={val}。")
        return s, e  # 返回创建的滑块和微调框。

    def _wrap(self, s, e):
        """
        将一个滑块 (s) 和一个微调框 (e) 包装在一个新的 QWidget 中，并使用 QHBoxLayout 进行水平布局。
        这有助于将滑块和微调框作为一个整体添加到 QFormLayout 的一行中。
        """
        w = QWidget()  # 创建一个通用的 QWidget 作为容器。
        h = QHBoxLayout(w)  # 为容器创建一个水平布局。
        h.setContentsMargins(0, 0, 0, 0)  # 设置布局的内边距为 0，确保控件紧密排列。
        h.addWidget(s)  # 将滑块添加到布局中。
        h.addWidget(e)  # 将微调框添加到布局中。
        return w  # 返回包含滑块和微调框的容器 Widget。

    def _choose_color(self):
        """
        打开一个颜色选择对话框，允许用户从调色板中选择一个新颜色。
        如果用户选择了有效的颜色，则更新对话框内部的颜色属性。
        """
        logger.info("用户操作: 点击 '选择颜色' 按钮，打开颜色选择对话框。")  # 记录用户打开颜色选择器的操作。
        # 调用 QColorDialog.getColor() 静态方法显示颜色选择对话框。
        # self.color 作为初始选中的颜色，self 作为父窗口。
        c = QColorDialog.getColor(self.color, self)
        if c.isValid():  # 检查用户是否选择了有效的颜色（而不是点击取消）。
            self.color = c  # 更新对话框的颜色属性为用户选择的新颜色。
            logger.info(f"用户操作: 颜色选择对话框 - 用户选择了新颜色: {self.color.name()}。")  # 记录用户选择的新颜色。
        else:
            logger.info("用户操作: 颜色选择对话框已取消。")  # 记录用户取消颜色选择。

    def accept(self):
        """
        当用户点击设置对话框中的“确定”按钮时，此方法会被调用。
        它负责将对话框中控件的当前值赋给对话框的相应属性。
        实际的属性更新和保存逻辑在父窗口的 _open_settings 方法中处理。
        """
        # 从微调框中获取最终的浮点数值，更新对话框实例的属性。
        self.font_size = self.e_font.value()
        self.opacity = self.e_opac.value()
        self.spacing = self.e_space.value()
        self.manual_offset = self.e_off.value()
        logger.debug("用户界面: 设置对话框 '确定' 按钮被点击，内部属性已更新。")
        super().accept()  # 调用父类 QDialog 的 accept() 方法，关闭对话框并返回 QDialog.Accepted。


# --- 主程序入口 ---
# 检查当前脚本是否作为主程序运行（而不是被其他模块导入）。
if __name__ == "__main__":
    # 必须在创建任何 Qt 窗口或控件之前，先创建 QApplication 实例。
    # QApplication 管理应用程序的事件循环和大部分 GUI 相关的初始化。
    app = QApplication(sys.argv)
    logger.info("程序启动: QApplication 实例创建成功。")  # 记录 QApplication 的成功创建。

    # 创建 DigitalClock 主窗口的实例。
    win = DigitalClock()
    win.show()  # 显示主窗口。此时窗口会出现在屏幕上。
    logger.info("程序启动: 主窗口已显示。")  # 记录主窗口的显示。

    # 启动 QApplication 的事件循环。
    # app.exec() 方法会阻塞程序执行，直到应用程序退出（例如，所有窗口都被关闭或 QApplication.quit() 被调用）。
    # 它返回应用程序的退出代码。
    exit_code = app.exec()
    logger.info(f"程序生命周期: 应用程序事件循环结束，退出码: {exit_code}。")  # 记录应用程序事件循环的结束和退出码。
    sys.exit(exit_code)  # 使用 sys.exit() 退出 Python 解释器，并将应用程序的退出码传递给操作系统。
