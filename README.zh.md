# PaperVaultQR

PaperVaultQR 可将文本文件切分为多个二维码，生成适合打印的 Word 文档；也可以从扫描后的二维码图片目录恢复原始内容。适合用于高熵加密数据的离线纸质备份。

## 📷 界面截图

以下为软件界面截图，图片位于 `Picture` 目录：

- 中文界面：`Picture/PaperVaultQR_zh_cn.png`

![PaperVaultQR 中文界面](Picture/PaperVaultQR_zh_cn.png)

## 🖼️ Logo

- 浅色模式 / 深色文字：`Picture/LOGO_dark_white.png`
- 深色模式 / 浅色文字：`Picture/LOGO_white_dark.png`

<table>
  <tr>
    <td align="center">
      <img src="Picture/LOGO_dark_white.png" alt="PaperVaultQR logo (light background)" width="200" />
    </td>
    <td align="center">
      <img src="Picture/LOGO_white_dark.png" alt="PaperVaultQR logo (dark background)" width="200" />
    </td>
  </tr>
</table>

## 🌟 核心功能

- 将输入文件按 `500` 字符切片并编码为二维码
- 非 UTF-8 输入会自动转为 `base64` 再编码，恢复时也会自动还原
- 生成 A4、`1.0 cm` 页边距、`4` 列表格布局的可打印 Word 文档
- 在二维码序列中保留原始文件名，便于恢复时尽可能沿用原命名
- 从扫描图片目录按文件名顺序解析 `png`、`jpg`、`jpeg` 并恢复文本或二进制数据
- 支持桌面 GUI 和 CLI，语言支持 `auto` 以及所有内置 locale

## 📌 重要说明

- UTF-8 文本采用直接切片 + QR 编码。
- 非 UTF-8 文件会先转为 `base64`，再按同样流程切片。
- QR 码使用纠错等级 `M`，可提升轻微污损、折痕、洇墨场景下的识别率。
- 输出 Word 文档会附加本地化后缀，例如 `_冷存储`、`_ColdStorage`、`_コールドストレージ`。
- 恢复后的文件默认保存在扫描目录的上一级目录中；若识别到原始文件名，会尽量保留原名与恢复后缀。
- 纸质备份更适合存储已加密内容，例如 Bitwarden 导出库、加密钱包助记词、GPG/PGP 密文等。

## 📂 文件说明

- `src/core/auto_split_qr.py`：将文本/二进制输入编码为二维码并生成打印文档
- `src/core/scanner_decoder.py`：解析扫描图片目录并恢复原始文本或原始字节
- `src/gui.py`：桌面 GUI，支持选择文件或文件夹执行编码/解码
- `build_gui_exe.bat`：Windows 下打包 GUI 可执行文件的辅助脚本
- `build_gui_linux.sh`：Linux 下打包 GUI 可执行文件的辅助脚本
- `.github/workflows/build-linux.yml`：Linux 构建的 GitHub Actions 工作流

## ⚙️ 安装依赖

```bash
pip install segno python-docx pillow pyzbar customtkinter numpy
```

> 💡 Linux 需要额外安装系统层面的 `zbar` 驱动（例如 `sudo apt-get install libzbar0`）。
>  
> 💡 如需本地打包 GUI，可再安装 `pyinstaller`。

## 🔨 构建

### Windows

```bash
build_gui_exe.bat
```

### Linux

```bash
chmod +x build_gui_linux.sh
./build_gui_linux.sh
```

### GitHub Actions

推送 `v*` 标签或手动触发 `workflow_dispatch` 时会构建 Linux 产物，输出到 `release/`。

## 🚀 使用方式

### 1. 命令行生成打印文档

```bash
python src/core/auto_split_qr.py path/to/input.txt
```

- 支持一次传入多个文件。
- 输出文件保存在输入文件同目录，文件名会附加当前语言对应的后缀。
- 例如：`input_冷存储.docx`、`input_ColdStorage.docx`、`input_コールドストレージ.docx`。

### 2. 命令行恢复扫描内容

```bash
python src/core/scanner_decoder.py path/to/scanned_images_folder
```

- 默认扫描 `scanned_pages` 文件夹。
- 自动读取目录中的 `png`、`jpg`、`jpeg` 图片。
- 恢复结果保存在扫描目录的上一级目录中。
- 若识别到原始文件名，会按 `原名 + 恢复后缀 + 扩展名` 保存；否则按 `目录名 + 恢复后缀` 保存。
- 若内容先被转为 `base64`，恢复后会自动还原为原始字节。

### 3. 运行桌面 GUI

```bash
python src/gui.py
```

GUI 支持：

- 选择一个或多个文件进行编码
- 选择一个文件夹进行解码
- 语言模式 `auto` / 各内置 locale
- 在编码前调整**二维码排版参数**：
  - **分片字符数**
  - **二维码纠错级别**（下拉：`L` / `M` / `Q` / `H`）
  - **二维码宽度 (cm)**
  - **标签字号**
  - **每页列数**
  - **页面边距 (cm)**
- 点击**恢复默认**可一键恢复为代码内置默认参数

### 4. 语言选项

CLI 只接受实际 locale code，例如 `zh_cn`、`en_us`、`ja_jp`、`ko_kr`；`auto` 为自动检测。

```bash
python src/core/auto_split_qr.py --lang zh_cn path/to/input.txt
python src/core/auto_split_qr.py --lang en_us path/to/input.txt
python src/core/auto_split_qr.py --lang ja_jp path/to/input.txt
python src/core/auto_split_qr.py --lang auto path/to/input.txt
```

```bash
python src/core/scanner_decoder.py --lang zh_cn path/to/scanned_images_folder
python src/core/scanner_decoder.py --lang en_us path/to/scanned_images_folder
python src/core/scanner_decoder.py --lang ja_jp path/to/scanned_images_folder
python src/core/scanner_decoder.py --lang auto path/to/scanned_images_folder
```

## 📄 默认参数

- 每个块：`500` 字符
- QR 纠错等级：`M`
- 页面边距：`1.0 cm`
- 页面：`A4`
- 表格：`4` 列，Word 自动跨页排版
- GUI 模式下可在编码前修改这些参数，点击“恢复默认”会还原为以上内置值

## 🔧 扫描建议

- 推荐使用 `300 DPI` 或 `600 DPI` 扫描
- 优先使用灰度或黑白模式
- 保持二维码完整，尽量不要裁掉边缘
- 如果某一张识别失败，可单独截取那一张二维码后再次尝试

## 🧪 实测记录

- 使用 `313 KB` 内容进行编码，共生成 `642` 个二维码。
- 打印后按顺序扫描时，有 `2` 个二维码首次未识别。
- 将这 `2` 个出错二维码单独截图并放入同一文件夹后，恢复流程可完整跑通。

## ⚠️ 安全建议

- 喷墨打印纸张不防水，请使用防水自封袋或过塑保存。
- 纸质备份仅适合已加密的数据；未加密内容仍可直接读取。
- 恢复所需的原密码必须妥善保管，否则即便二维码完好也无法还原加密内容。
