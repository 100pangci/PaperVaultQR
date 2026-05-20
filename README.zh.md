# PaperVaultQR

将文本切分为二维码并生成可打印 Word 文档，随后可通过扫描二维码恢复原始文本。

## 功能

- 将 `split_qr.json` 拆分为多个 QR 码
- 生成适合打印的 Word 文档
- 从扫描后的图片中识别 QR 码并恢复文本
- 支持中文 / English 控制台输出

## 文件说明

- `auto_split_qr.py`：生成二维码打印文档
- `scanner_decoder.py`：解析扫描图片并恢复文本
- `split_qr.json`：输入原文
- `scanned_pages/`：放扫描后的图片
- `冷存储.docx` / `cold_storage.docx`：生成的打印文档
- `decoder.json`：恢复出的文本

## 环境依赖

```bash
pip install segno python-docx pillow pyzbar
```

> `pyzbar` 可能还需要系统安装 `zbar`。

## 用法

### 1. 生成二维码打印文档

把待切分内容放到 `split_qr.json`，然后运行：

```bash
python auto_split_qr.py
```

你也可以将文件拖拽到脚本上（或把文件路径作为参数传入）来对该文件生成二维码：

```bash
python auto_split_qr.py path/to/input.txt
```

如果你拖拽或传入的是一个文件夹路径，脚本会对该文件夹运行解码流程（适用于已将扫描图片保存到某个文件夹的场景）：

```bash
python auto_split_qr.py path/to/scanned_images_folder/
```

指定语言：

```bash
python auto_split_qr.py --lang zh
python auto_split_qr.py --lang en
python auto_split_qr.py --lang auto
```

### 2. 扫描并恢复文本

把扫描后的图片放入 `scanned_pages/`，然后运行：

```bash
python scanner_decoder.py
```

指定语言：

```bash
python scanner_decoder.py --lang zh
python scanner_decoder.py --lang en
python scanner_decoder.py --lang auto
```

你也可以直接指定文件夹调用解码函数：

```bash
python -c "import scanner_decoder; scanner_decoder.decode_folder('scanned_pages', lang='zh')"
```

### 3）图形界面（GUI） — 拖拽支持（Windows）

项目提供了一个简单的 Tkinter GUI，支持在 Windows 上将文件或文件夹直接拖拽到窗口：

```bash
python gui.py
```

拖入文件会对其进行编码（生成打印文档），拖入文件夹会对该文件夹运行解码流程。若平台不支持原生拖拽，可使用窗口中的按钮选择文件或文件夹。

## 输出说明

- 生成端会输出 Word 文档
- 解码端会输出 `decoder.json`

## 默认参数

- 单块字符数：`500`
- QR 纠错级别：`M`
- 每页布局：`4 x 6`
- 页边距：`1.0 cm`

## 备注

- `auto` 会根据系统语言自动选择中文或英文
- 建议扫描使用 `300/600 DPI` 灰度模式，以提高识别率
