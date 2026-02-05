# 机械臂控制 (Robot-Arm-Control)

这是一个用于控制和演示机器人手臂与夹爪（含瑞尔曼/RM 系列与 RH 系列示例）的桌面应用和控制库集合。

<!-- TOC -->
- 概要
- 特性
- 目录结构
- 依赖与安装
- 运行与使用
- 配置文件说明
- 开发与贡献
- 许可证
- 联系方式
<!-- /TOC -->

## 概要

本仓库包含用于机械臂与夹爪控制的工具、示例代码和 GUI 应用：

- `core/`：核心控制逻辑、控制器与串口管理等模块。
- `GUI/`：基于 PyQt 的桌面应用及打包结果文件（用于演示与操作机械臂）。
- `Document/`：厂家 SDK、示例代码（C/C++/Python）和硬件说明文档。
- `config/`：动作序列、按键绑定和运行时配置样例。

目标用户：机器人开发者、研究人员与需要集成夹爪/手臂控制到上层应用的工程师。

## 特性

- 多语言示例：C、C++、Python、C# 等。
- 支持多种通信接口（串口/485/CAN，视设备而定）。
- 图形化控制面板：手动控制、动作序列播放、力/传感器数据可视化。
- 可扩展的自适应抓取控制策略模块。

## 目录结构（摘要）

- `GUI/` - PyQt 应用源码与已打包的构建输出。
- `core/` - 应用核心模块（`arm_controller.py`、`action_manager.py` 等）。
- `Document/` - 厂家 SDK、示例项目与说明文档。
- `config/` - JSON 格式的动作与设置文件。
- `data/` 和 `resources/` - 运行所需的静态资源与界面资源。

完整目录请参阅仓库根目录。

## 依赖与安装

推荐使用 Python 3.8+ 虚拟环境。

安装依赖：

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r GUI\requirements.txt
```

（若要仅运行核心库或示例，请在相应子目录下查看对应的 `requirements.txt` 或说明文档。）

## 运行与使用

快速运行 GUI（开发模式）：

```powershell
cd GUI
python main.py
```

主要功能：

- 在串口页（Serial）选择并打开设备串口。
- 使用动作管理页（Action Manager）载入与播放动作序列。
- 在自适应抓取页（Adaptive Grasp）调整抓取参数并执行自动化抓取。

示例脚本：

- `Document/RM_API2/Python/Robotic_Arm/` 下包含厂家 Python 示例代码，可参考硬件接入流程。

## 配置文件说明

主要配置位于 `config/`：

- `settings.json`：应用的全局设置（界面、串口默认等）。
- `actions.json` 与 `action_sequences.json`：动作定义与序列文件，JSON 格式，编辑后可以在 GUI 中加载。

修改配置后建议重启应用以确保生效。

## 开发与贡献

欢迎贡献：请先在 Issue 中描述你的改进建议或 Bug，再提交 Pull Request。

开发小贴士：

- 遵循现有编码风格（PEP8）并在提交前运行基础测试或手动验证主要功能。
- 若增加新的硬件支持，请在 `Document/` 下添加对应说明，并在 `core/serial_manager.py` 中扩展通信适配层。

## 许可证

本项目使用 MIT 许可证（如需更改或补充许可证信息，请在此处注明）。

## 联系方式

如需帮助或商业合作，请在仓库 Issue 中联系或直接发送邮件到项目维护者。

---

如果你希望我根据仓库内容进一步细化 README（添加示例截图、常见问题或运行演示 GIF），请告诉我想要突出哪些部分，我会继续完善并提交更新。
