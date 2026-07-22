# PaperVaultQR

[![CI](https://github.com/100pangci/PaperVaultQR/actions/workflows/ci.yml/badge.svg)](https://github.com/100pangci/PaperVaultQR/actions/workflows/ci.yml)
[![License: MPL-2.0](https://img.shields.io/badge/License-MPL_2.0-blue.svg)](LICENSE)
![Platform: Windows | Linux](https://img.shields.io/badge/Platform-Windows%20|%20Linux-lightgrey)

> **English** [README.md](README.md) · **日本語** [README.jp.md](README.jp.md) · **Русский** [README.ru.md](README.ru.md) · **조선어** [README.ko_kp.md](README.ko_kp.md)

PaperVaultQR 可将文本文件切分为多个二维码，生成适合打印的 Word 文档；也可以从扫描后的二维码图片目录恢复原始内容。适合用于高熵加密数据的离线纸质备份，例如 Bitwarden 导出库、加密钱包助记词、GPG/PGP 密文等。

---

## 界面截图

![中文界面](Picture/PaperVaultQR_zh_cn.png)

## Logo

| 浅色背景 | 深色背景 |
|---|---|
| ![浅色](Picture/LOGO_dark_white.png) | ![深色](Picture/LOGO_white_dark.png) |

---

## 核心功能

- 将输入文件按 `500` 字符切片并编码为二维码
- 非 UTF-8 输入自动转为 `base64` 再编码，恢复时自动还原
- 生成 A4、`1.0 cm` 页边距、多列表格布局的可打印 Word 文档
- 在二维码序列中保留原始文件名，便于恢复时沿用原命名
- 从扫描图片目录按文件名顺序解析 `png`、`jpg`、`jpeg` 并恢复文本或二进制数据
- 跨块 Reed-Solomon 纠错 — 添加冗余 QR 块（0–100%），可在部分二维码丢失或损坏时恢复
- 桌面 GUI（customtkinter）和 CLI，语言支持 `auto` 以及 22 个内置 locale

## 重要说明

- UTF-8 文本直接切片 + QR 编码；非 UTF-8 文件先转为 `base64`，再按同样流程处理
- QR 码使用纠错等级 `M`，提升轻微污损、折痕、洇墨场景下的识别率
- 输出文件名附加本地化后缀，例如 `_冷存储`、`_ColdStorage`、`_コールドストレージ`
- 恢复后的文件保存在扫描目录的上一级目录中；若识别到原始文件名，会尽量保留原名与恢复后缀
- **本工具仅适用于已加密的内容**

---

## 安装依赖

- Python 3.10+

```bash
pip install segno python-docx pillow pyzbar customtkinter numpy reedsolo
```

> **注意：** Linux 需要额外安装系统层面的 `zbar` 驱动（`sudo apt-get install libzbar0`）。如需本地打包 GUI，可再安装 `pyinstaller`。

---

## 快速开始

### 生成打印文档

```bash
python src/core/auto_split_qr.py path/to/input.txt
```

支持一次传入多个文件。输出保存在输入文件同目录，文件名附加当前语言对应的后缀。

### 恢复扫描内容

```bash
python src/core/scanner_decoder.py path/to/scanned_images_folder
```

默认扫描 `./scanned_pages` 文件夹。自动读取 `png`、`jpg`、`jpeg` 图片。

### 启动桌面 GUI

```bash
python src/gui.py
```

---

## CLI 用法

### 语言选择

```bash
python src/core/auto_split_qr.py --lang zh_cn path/to/input.txt
python src/core/auto_split_qr.py --lang en_us path/to/input.txt
python src/core/auto_split_qr.py --lang auto path/to/input.txt
```

```bash
python src/core/scanner_decoder.py --lang zh_cn path/to/scanned_images_folder
python src/core/scanner_decoder.py --lang auto path/to/scanned_images_folder
```

### 支持的语言

`auto`, `bo`, `da_dk`, `de_de`, `en_us`, `es_es`, `fr`, `he_il`, `hi_in`, `it_it`, `ja_jp`, `ko_kp`, `ko_kr`, `pt_br`, `ru_ru`, `th_th`, `tr`, `ug_cn`, `uk_ua`, `vi_vn`, `zh_cn`

---

## GUI 功能

- 选择一个或多个文件进行编码
- 选择一个文件夹进行解码
- 语言模式 `auto` / 各内置 locale
- 编码前调整**二维码排版参数**：

| 参数 | 说明 |
|---|---|
| 分片字符数 | 每个 QR 码包含的字符数 |
| 二维码纠错级别 | `L` / `M` / `Q` / `H` |
| 跨块纠错强度 | RS 冗余 0–100%（0 = 关闭） |
| 二维码宽度 (cm) | 页面上每个 QR 码的宽度 |
| 标签字号 | 二维码标签的字体大小 |
| 每页列数 | Word 表格列数 |
| 页面边距 (cm) | 文档页边距 |

点击**恢复默认**一键恢复为内置默认参数。

---

## 默认参数

| 参数 | 默认值 |
|---|---|
| 每块字符数 | 500 |
| QR 纠错等级 | `M` |
| 跨块 RS 纠错 | 0（关闭） |
| 页面边距 | 1.0 cm |
| 页面大小 | A4 |
| 布局列数 | 4 |

---

## 扫描建议

- 推荐使用 **300 DPI** 或 **600 DPI** 扫描
- 优先使用灰度或黑白模式
- 保持二维码完整，不要裁掉边缘
- 若某一张识别失败，单独截取那一张二维码后重试

---

## 实测记录

- 使用 **313 KB** 内容编码，共生成 **642** 个二维码
- 打印后按顺序扫描，仅 **2** 个二维码首次未识别；单独截图重试后完整恢复

---

## 安全建议

- 喷墨打印不防水，请使用防水自封袋或过塑保存
- 纸质备份仅适合**已加密的数据**；未加密内容仍可直接读取
- 恢复所需的密码必须妥善保管，否则即便二维码完好也无法还原

---

## 项目结构

```
PaperVaultQR/
├── src/
│   ├── core/
│   │   ├── auto_split_qr.py    # 将输入编码为 QR 码并生成 Word 文档
│   │   └── scanner_decoder.py  # 解析扫描图片并恢复原始内容
│   ├── i18n/
│   │   ├── core_texts.py       # CLI 国际化字符串
│   │   ├── ui_texts.py         # GUI 国际化字符串
│   │   └── locales/            # JSON 翻译文件（22 种语言）
│   ├── gui.py                  # 桌面 GUI（customtkinter）
│   ├── app_version.py          # 版本号辅助工具
│   └── icon/                   # 应用图标
├── Picture/                    # 截图和 Logo 资源
├── scripts/                    # 开发辅助脚本
├── build/                      # 构建产物
├── build_gui_exe.bat           # Windows PyInstaller 构建脚本
├── build_gui_linux.sh          # Linux PyInstaller 构建脚本
├── gui.spec                    # PyInstaller spec 文件（旧版）
└── .github/workflows/
    ├── ci.yml                  # 语法检查和导入检查
    └── release.yml             # v* 标签推送时构建并发布
```

---

## 构建

### Windows

```bat
build_gui_exe.bat
```

### Linux

```bash
chmod +x build_gui_linux.sh
./build_gui_linux.sh
```

### GitHub Actions

推送 `v*` 标签触发 **release.yml**，自动构建 Windows 和 Linux 可执行文件并创建 GitHub Release。

---

## 开发

```bash
git clone https://github.com/100pangci/PaperVaultQR.git
cd PaperVaultQR
python -m venv .venv
# .venv\Scripts\activate  (Windows)
# source .venv/bin/activate (Linux)
pip install segno python-docx pillow pyzbar customtkinter numpy reedsolo
```

### 代码风格

遵循 PEP 8，行长度限制 120 字符，使用 [Flake8](.flake8) 检查：

```bash
python -m flake8 src/ --max-line-length=120
```

---

## Roadmap

> TODO：可在此处列出未来计划，例如批量扫描、Web UI 或纯 CLI 轻量构建等。

---

## FAQ

> TODO：常见问题可在此处补充。

---

## 许可证

[Mozilla Public License 2.0](LICENSE)

---

## 致谢

- [segno](https://github.com/heuer/segno) — QR 码生成
- [python-docx](https://github.com/python-openxml/python-docx) — Word 文档创建
- [customtkinter](https://github.com/TomSchimansky/CustomTkinter) — 现代 GUI 工具包
- [pyzbar](https://github.com/NaturalHistoryMuseum/pyzbar) — QR / 条码解码
- [reedsolo](https://github.com/tomerfiliba-org/reedsolo) — Reed-Solomon 纠错
- [Pillow](https://python-pillow.org/) — 图像处理
- [NumPy](https://numpy.org/) — 数值计算
