# ScanSnap iX100 / iX110 的通用第三方驱动程序

[简体中文](README.md) | [English](README.en.md) | [日本語](README.ja.md)

我购买了一个便携式扫描仪，这可能是当前市面上唯一的使用type-c接口的便携式扫描仪  
但是买来后我就发现他的官方驱动一坨狗屎，不光十分臃肿，把各个型号的硬件驱动与后续软件图像处理耦合在一起（可能对于高中肄业就上班的日本牛马来说易于使用而广受好评吧），而且最关键的硬件驱动甚至只能输出 JPG 和 PDF 这两种有损压缩格式，这是我不能接受的  
事实上，硬件本身具有输出未压缩图像的能力

本项目的设计目标是让所有购买此设备的人都完全不需要下载安装官方的应用，并且获得原始的图像数据  
这消费级扫描仪毕竟不是专业相机，硬件本身没有提供输出 raw 数据的功能，只能输出解拜耳后的 bmp 数据

这个扫描仪大约花费了我 24000 JPY，而全部的逆向工作使用的 AI 费用至少需要一个 30000 JPY 的 ChatGPT Pro 20x 订阅  
并且让本项目的各个模块最终能正常工作与对齐需要在开发人员具备一定专业知识的基础上施以相当多的人工指导，期间还需要反复手动维护硬件状态来进行测试  
我真心期待我说一句「给我一个干净的逆向结果」就能一步到位的时代来临


三个独立组件统一放在本目录。每个组件的运行源码位于 `src/`，使用文档位于 `doc/`，Python 依赖位于各组件根目录。

| 组件          | 用途                                     | 使用说明                            |
| ------------- | ---------------------------------------- | ----------------------------------- |
| `usb/`        | USB 单页与连续扫描，保存 BMP             | [USB 扫描](usb/README.md)           |
| `wifi/`       | Wi-Fi 单页、面板触发与连续扫描，保存 BMP | [Wi-Fi 扫描](wifi/README.md)        |
| `wifi-setup/` | 通过 USB 读取和设置扫描仪无线配置        | [Wi-Fi setup](wifi-setup/README.md) |

需要 Python 3.11 或更新版本。进入所选组件目录，按其 README 安装依赖和准备驱动或配置。例如从本目录查看三个组件的离线帮助：

```powershell
python -B usb/src/scan_direct.py --help
python -B wifi/src/scan_direct.py --help
python -B wifi-setup/src/setup_cli.py --help
```

仓库中的剩余部分几乎全部由 AI 生成，有少量删改

## 全部文档 / All documentation / 全ドキュメント

| 文档 | 简体中文 | English | 日本語 |
| --- | --- | --- | --- |
| 项目总览 | [简体中文](README.md) | [English](README.en.md) | [日本語](README.ja.md) |
| USB 扫描 | [简体中文](usb/README.md) | [English](usb/README.en.md) | [日本語](usb/README.ja.md) |
| USB Python API | [简体中文](usb/doc/PYTHON_API.md) | [English](usb/doc/PYTHON_API.en.md) | [日本語](usb/doc/PYTHON_API.ja.md) |
| 驱动与设备权限 | [简体中文](usb/driver/README.md) | [English](usb/driver/README.en.md) | [日本語](usb/driver/README.ja.md) |
| Windows 驱动配置 | [简体中文](usb/driver/WINDOWS.md) | [English](usb/driver/WINDOWS.en.md) | [日本語](usb/driver/WINDOWS.ja.md) |
| Wi-Fi 扫描 | [简体中文](wifi/README.md) | [English](wifi/README.en.md) | [日本語](wifi/README.ja.md) |
| Wi-Fi 配置 | [简体中文](wifi/doc/CONFIGURATION.md) | [English](wifi/doc/CONFIGURATION.en.md) | [日本語](wifi/doc/CONFIGURATION.ja.md) |
| Wi-Fi 运行与分发 | [简体中文](wifi/doc/RUNNING.md) | [English](wifi/doc/RUNNING.en.md) | [日本語](wifi/doc/RUNNING.ja.md) |
| Wi-Fi 连续扫描 | [简体中文](wifi/doc/INTERACTIVE.md) | [English](wifi/doc/INTERACTIVE.en.md) | [日本語](wifi/doc/INTERACTIVE.ja.md) |
| Wi-Fi Python API | [简体中文](wifi/doc/API.md) | [English](wifi/doc/API.en.md) | [日本語](wifi/doc/API.ja.md) |
| Wi-Fi 设置 | [简体中文](wifi-setup/README.md) | [English](wifi-setup/README.en.md) | [日本語](wifi-setup/README.ja.md) |
| 设置函数与 CLI 参考 | [简体中文](wifi-setup/doc/FUNCTIONS.md) | [English](wifi-setup/doc/FUNCTIONS.en.md) | [日本語](wifi-setup/doc/FUNCTIONS.ja.md) |
