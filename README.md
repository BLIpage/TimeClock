# 🕒 桌面时间 (TimeClock)

一个基于 PySide6 实现的桌面透明数字时钟应用，支持自定义样式、NTP 时间同步和系统托盘管理。

---

## ✨ 功能特性

- **纯文字透明显示：**  
  时钟内容以纯文字形式显示，背景完全透明，不遮挡桌面内容。

- **自由拖动：**  
  支持鼠标拖动，可将时钟随意放置在桌面任意位置。

- **样式高度自定义：**  
  - 调整字体大小  
  - 自定义文字颜色  
  - 设置窗口不透明度  
  - 调整日期和时间行之间的间距  

- **精准时间同步：**  
  通过 NTP（网络时间协议）自动校准时间，确保时间显示准确。

- **手动时间偏移：**  
  允许用户手动设置时间偏移量，以应对特定需求。

- **窗口置顶：**  
  可选将时钟窗口保持在所有其他窗口之上。

- **系统托盘集成：**  
  最小化到系统托盘，不占用任务栏空间，提供便捷的右键菜单操作（显示/隐藏、设置、退出）。

- **自动保存配置：**  
  用户的所有设置更改会自动保存，下次启动时自动加载。

- **详细日志记录：**  
  提供详细的运行日志，方便问题排查和调试。

---

## 🚀 如何安装和运行

1. **克隆仓库：**

    ```bash
    git clone https://github.com/BLIpage/TimeClock.git
    cd TimeClock
    ```

2. **安装依赖：**

    ```bash
    pip install PySide6 requests platformdirs
    ```

3. **运行程序：**

    ```bash
    python TimeClockWindows.py
    ```

> ⚠️ 程序启动后会最小化到系统托盘。如果看不到窗口，请检查桌面右下角的托盘图标。


---

## 📦 依赖

- `PySide6`：用于构建图形用户界面  
- `requests`：用于 NTP 时间同步  
- `platformdirs`：用于获取跨平台配置目录路径
- ⚠️ `PySide6` 需要 `Python 3.8 `及更高版本。

---

## 🛠️ 打包为独立可执行文件（使用 PyInstaller）

为了让其他用户无需安装 Python 环境也能运行应用，可以将其打包为一个独立的可执行文件（如 Windows 上的 `.exe`）。

### 1. 安装 PyInstaller

```bash
pip install pyinstaller
```

### 2. 打包命令（推荐）

```bash
pyinstaller TimeClockWindows.py --name "TimeClock" --onefile --windowed --icon "clock.ico"
```

#### 参数说明：

- `--name "TimeClock"`：设置可执行文件名称  
- `--onefile`：将程序打包为一个单独的 `.exe` 文件  
- `--windowed` 或 `--noconsole`：打包为 GUI 应用，运行时不显示控制台窗口  
- `--icon "clock.ico"`：设置图标文件（可选）  

### 3. 获取可执行文件

打包完成后，可执行文件会生成在 `dist/` 文件夹内，例如：

```
dist/TimeClock.exe
```

> ⚠️ 注意事项：
>
> - **文件较大**：由于包含 Python 解释器和所有依赖，打包后的文件体积较大是正常现象  
> - **平台限制**：只能在对应平台上打包，例如 Windows 上生成 `.exe`，macOS 上生成 `.app`  
> - **字体依赖**：程序使用了 `Noto Sans SC`（思源黑体 SC），若系统未安装，将回退到默认字体  

---

**📄 配置文件：**  
  配置文件默认保存在：

  ```
  C:\Users\<用户名>\AppData\Local\TimeClock\TimeClock\config.json
  ```
  ```
  %localappdata%\TimeClock\TimeClock\config.json
  ```

**📝日志目录：**  
  日志文件默认保存在：

  ```
  C:\Users\<用户名>\AppData\Local\TimeClock\TimeClock\Logs
  ```
  ```
  %localappdata%\TimeClock\TimeClock\Logs
  ```


---

## 💡 未来展望

- [ ] 增加更多字体选择  
- [ ] 支持自定义日期格式  
- [ ] 优化 CPU/内存占用  
- [ ] 增加多语言支持  

---

## 📄 许可证

本项目采用 [MIT License](LICENSE)。


## ✉️ 联系
如果您在使用过程中遇到任何问题、有任何功能建议，或发现了 Bug，欢迎通过 GitHub Issues 提交。

---
本项目代码均由[ChatGPT](https://chatgpt.com/)生成，代码详细注释由[Gemini](https://gemini.google.com/)生成
