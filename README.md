# PinClip 📌

一款轻量级的截图、贴图与看图效率工具，帮助您在阅读和工作时轻松对比图文信息。
A lightweight screenshot, sticker, and viewing productivity tool that helps you easily compare graphic information while reading and working.
【借助gemini开发】

**在ubuntu20.04LTS python3.8上经过验证**
## ✨ 主要功能

- **快捷截图**: 使用 `Ctrl+Alt+P` 快速截取屏幕任意区域。
- **置顶贴图**: 截图或图片会以置顶窗口的形式“钉”在屏幕上。
- **强大交互**:
    - **缩放**: 鼠标滚轮在图上滚动。
    - **移动**: 鼠标左键拖动窗口。
    - **拖动**: 按住鼠标中键（滚轮）拖动图片内容。
    - **调整大小**: 拖动窗口边缘。
- **万能输入**:
    - 支持从浏览器或文件管理器**拖拽**图片到贴图窗口。
    - 支持**右键菜单**打开本地图片。
- **安全易用**: 提供系统托盘图标，可随时退出，打包后无需Python环境即可运行。

## 🚀 安装与使用

1.  克隆本仓库: `git clone https://github.com/YourUsername/YourRepoName.git`
2.  创建并激活虚拟环境。
3.  安装依赖: `pip install -r requirements.txt` 
4.  运行主程序: `python main.py`
5.  [可选]导出为可执行文件pyinstaller --name PinClip --onefile --noconsole --icon=icon.png --hidden-import=pynput.keyboard._xorg main.py
6.  使用 `Ctrl+Alt+P` 开始截图，或通过托盘菜单交互
7.  对网页上可拖动的图片可以拖动到当前窗口上【原截图会被覆盖】
8.  点击截图窗口，ESC关闭

**requirements中的依赖仅供参考。项目很简单，环境配置很容易**
**由于使用了PyQt架构，因此打包后的软件比较大，不建议打包。**
