# 桌面时间 (TimeClock)

一个基于 PySide6 实现的桌面透明数字时钟应用，支持自定义样式、NTP 时间同步和系统托盘管理。

### ✨ 功能特性

* **纯文字透明显示：** 时钟内容以纯文字形式显示，背景完全透明，不遮挡桌面内容。
* **自由拖动：** 支持鼠标拖动，可将时钟随意放置在桌面任意位置。
* **样式高度自定义：**
    * 调整字体大小。
    * 自定义文字颜色。
    * 设置窗口不透明度。
    * 调整日期和时间行之间的间距。
* **精准时间同步：** 通过 NTP（网络时间协议）自动校准时间，确保时间显示准确。
* **手动时间偏移：** 允许用户手动设置时间偏移量，以应对特定需求。
* **窗口置顶：** 可选将时钟窗口保持在所有其他窗口之上。
* **系统托盘集成：** 最小化到系统托盘，不占用任务栏空间，提供便捷的右键菜单操作（显示/隐藏、设置、退出）。
* **自动保存配置：** 用户的所有设置更改会自动保存，下次启动时自动加载。
* **详细日志记录：** 提供详细的运行日志，方便问题排查和调试。

### 🚀 如何安装和运行

1.  **克隆仓库：**
    ```bash
    git clone https://github.com/BLIpage/TimeClock.git
    cd TimeClock
    ```
2.  **安装依赖：**
    ```bash
    pip install PySide6 requests platformdirs
    ```
3.  **运行程序：**
    ```bash
    python TimeClockWindows.py 
    ```

**注意：** 程序启动后会最小化到系统托盘。如果看不到窗口，请检查桌面右下角的托盘图标。


### 📦 依赖

* **PySide6:** 用于构建图形用户界面。
* **requests:** 用于 NTP 时间同步的网络请求。
* **platformdirs:** 用于获取跨平台的配置目录路径。

### 📦 打包为独立可执行文件 (使用 PyInstaller)

* 为了让其他用户无需安装 Python 环境也能运行您的应用，您可以将其打包成一个独立的跨平台可执行文件（例如 Windows 上的 .exe）。我们推荐使用 PyInstaller 工具。

1.  **安装 PyInstaller**
     * 如果您尚未安装 PyInstaller，请运行以下命令：
    ```bash
    pip install pyinstaller
    ```
2.  **安装 PyInstaller**
     * 在命令行中，切换到您的项目根目录，然后运行以下 PyInstaller 命令：
    ```bash
    pyinstaller --name "TimeClock" --onefile --windowed --icon "clock.ico" "TimeClockWindows.py"
    ```


#### 命令解释：

* **--name "TimeClock" : ** 设置生成的可执行文件的名称。
* **--onefile:** 将所有组件（包括 Python 解释器和所有依赖）打包成一个独立的执行文件。
* **--windowed (或 --noconsole):** 生成一个没有控制台窗口的 GUI 应用程序，双击即可运行，不会弹出命令行窗口。
* **--icon "clock.ico": ** 指定应用程序的图标文件。

3.  **获取可执行文件**
打包过程可能需要几分钟。完成后，您会在项目根目录下看到一个名为 dist 的新文件夹。最终生成的可执行文件就在这个 dist 文件夹内（例如在 Windows 上是 dist/TransparentClock.exe）。

注意事项：

文件大小： 由于 PyInstaller 会将 Python 解释器和所有依赖（尤其是 PySide6 库）打包进去，生成的可执行文件会相对较大，这是正常现象。

跨平台兼容性： PyInstaller 是跨平台的，但它只能在当前操作系统上打包出该操作系统对应的可执行文件。例如，在 Windows 上打包会生成 .exe，在 macOS 上会生成 .app，在 Linux 上则生成二进制可执行文件。

字体： 本应用使用了 "Noto Sans SC" (思源黑体 SC) 字体。如果目标系统没有安装该字体，可能会回退到系统默认的中文字体进行显示。

### 💡 未来展望

* [ ] 增加更多字体选择。
* [ ] 支持自定义日期格式。
* [ ] 优化 CPU/内存占用。
* [ ] 增加多语言支持。

### 📄 许可证

本项目采用 MIT 许可证。详见 [LICENSE](LICENSE) 文件。
