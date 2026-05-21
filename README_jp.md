# PaperVaultQR

> 中文文档 [README.zh.md](README.zh.md) | English [README.md](README.md)

PaperVaultQR は、テキストファイルを複数の QR コードに分割して印刷可能な Word 文書を生成し、スキャン済みの QR 画像フォルダから元の内容を復元します。高エントロピーな暗号データのオフライン紙バックアップ向けに設計されています。

## 📷 画面例

以下はソフトウェアの画面例です。画像は `Picture` ディレクトリにあります。

- 日本語 UI: `Picture/PaperVaultQR_JP.png`

![PaperVaultQR Japanese GUI](Picture/PaperVaultQR_JP.png)

## 🖼️ ロゴ

- ライトモード / ダーク文字: `Picture/LOGO_dark_white.png`
- ダークモード / ライト文字: `Picture/LOGO_white_dark.png`

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

## 🌟 主な機能

- 入力ファイルを `500` 文字ごとに分割して QR コード化
- UTF-8 でない入力は自動で `base64` に変換してからエンコードし、復元時も自動で戻す
- A4 用紙、`1.0 cm` 余白、`4` 列の表レイアウトで印刷用 Word 文書を生成
- QR シーケンス内に元のファイル名を保持し、復元時にファイル名をなるべく維持
- スキャン画像フォルダ内の `png`、`jpg`、`jpeg` をファイル名順に解析し、テキストまたはバイナリデータを復元
- デスクトップ GUI と CLI の両方をサポートし、`auto` と内蔵 locale を利用可能

## 📌 重要な注意

- UTF-8 テキストは、直接のテキスト分割 + QR エンコードで処理します。
- UTF-8 でないファイルは、先に `base64` 化してから同じ流れで分割します。
- QR コードは誤り訂正レベル `M` を使用し、軽い傷、汚れ、折れに対する認識率を向上させます。
- 出力される Word 文書にはローカライズされた接尾辞が付きます。例: `_ColdStorage`、`_冷存储`、`_コールドストレージ`
- 復元されたファイルはスキャンフォルダの親ディレクトリに保存されます。元のファイル名が判別できる場合は、復元用接尾辞付きで保持されます。
- 紙のバックアップは、Bitwarden のエクスポート済みボルト、暗号化されたウォレットシード、GPG/PGP 暗号文など、すでに暗号化済みのデータ向けです。

## 📂 ファイル一覧

- `src/core/auto_split_qr.py`：テキスト/バイナリ入力を QR コード化し、印刷用 Word 文書を生成
- `src/core/scanner_decoder.py`：スキャン画像フォルダを復号し、元のテキストまたはバイト列を復元
- `src/gui.py`：ファイルまたはフォルダを選択してエンコード/デコードするデスクトップ GUI
- `build_gui_exe.bat`：Windows 用 GUI 実行ファイル作成補助スクリプト
- `build_gui_linux.sh`：Linux 用 GUI 実行ファイル作成補助スクリプト
- `.github/workflows/build-linux.yml`：Linux ビルド用 GitHub Actions ワークフロー

## ⚙️ 依存関係のインストール

```bash
pip install segno python-docx pillow pyzbar customtkinter numpy
```

> 💡 Linux では、システム側の `zbar` ライブラリも必要です（例: `sudo apt-get install libzbar0`）。
>
> 💡 GUI をローカルでビルドする場合は、`pyinstaller` も追加でインストールしてください。

## 🔨 ビルド

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

`v*` タグの push、または `workflow_dispatch` の手動実行で Linux 版アーティファクトを作成し、`release/` に出力します。

## 🚀 使い方

### 1. コマンドラインで印刷用文書を生成

```bash
python src/core/auto_split_qr.py path/to/input.txt
```

- 複数ファイルをまとめて指定できます。
- 出力は入力ファイルと同じディレクトリに保存され、ファイル名にローカライズされた接尾辞が付きます。
- 例: `input_ColdStorage.docx`、`input_冷存储.docx`、`input_コールドストレージ.docx`

### 2. コマンドラインでスキャン内容を復元

```bash
python src/core/scanner_decoder.py path/to/scanned_images_folder
```

- 何も指定しない場合は `scanned_pages` を既定フォルダとして使います。
- 対象フォルダ内の `png`、`jpg`、`jpeg` を読み込みます。
- 復元結果はスキャンフォルダの親ディレクトリに保存されます。
- 元のファイル名が検出できた場合はその名前を維持し、そうでない場合はフォルダ名を使います。
- 内容が `base64` に変換されていた場合は、元のバイト列に自動で戻します。

### 3. デスクトップ GUI を起動

```bash
python src/gui.py
```

GUI でできること:

- 1 つ以上のファイルを選択してエンコード
- フォルダを選択してデコード
- `auto` と内蔵 locale の利用

### 4. 言語オプション

CLI は `zh_cn`、`en_us`、`ja_jp`、`ko_kr` などの実際の locale code を受け付けます。`auto` は自動判定です。

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

## 📄 デフォルト設定

- 1 チャンクあたりの文字数: `500`
- QR 誤り訂正レベル: `M`
- ページ余白: `1.0 cm`
- 用紙サイズ: `A4`
- レイアウト: `4` 列、Word が行を自動で跨いで配置

## 🔧 スキャン時の推奨事項

- `300 DPI` または `600 DPI` でのスキャンを推奨
- グレースケールまたは白黒モードを優先
- QR コード全体が欠けないようにする
- 1 枚だけ失敗する場合は、その QR を単独で切り出して再試行する

## ⚠️ セキュリティのヒント

- インクジェット印刷は防水ではありません。防水スリーブやラミネートで保管してください。
- 紙のバックアップには暗号化済みデータのみを保存してください。未暗号化データはそのまま読めます。
- 復元に必要な元の秘密情報は安全に保管してください。失われると、QR が残っていても復元できません。
