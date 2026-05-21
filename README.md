# PaperVaultQR

> 中文文档 [README.zh.md](README.zh.md) | 日本語 [README_jp.md](README_jp.md)

PaperVaultQR converts any text file into multiple QR codes, generates a printable Word document, and restores the original content from a folder of scanned QR images. It is designed for offline paper backup of high-entropy encrypted data.

## Screenshots

The interface screenshot is located in the `Picture` folder:

- English UI: `Picture/PaperVaultQR_EN.png`

![PaperVaultQR English GUI](Picture/PaperVaultQR_EN.png)

## Logo

- Light mode / dark text: `Picture/LOGO_dark_white.png`
- Dark mode / light text: `Picture/LOGO_white_dark.png`

![PaperVaultQR logo (light background)](Picture/LOGO_dark_white.png)

![PaperVaultQR logo (dark background)](Picture/LOGO_white_dark.png)

## Features

- Split any UTF-8 text file into 500-character QR chunks and encode them
- Auto-detect non-UTF-8 input and convert it to base64 before encoding
- Generate a printable Word document with a `4 x 6` QR layout and `1.0 cm` page margins
- Embed the original filename in the final QR for filename-preserving recovery
- Decode `png`, `jpg`, and `jpeg` images from a scanned folder and restore the original data in order
- Auto-detect base64-marked content during recovery and restore the original bytes if needed
- Supports both CLI and Windows GUI, with language options for `auto`, `zh`, `jp`, and `en`

## Important Notes

- UTF-8 input is processed with direct text slicing and QR encoding.
- Non-UTF-8 files are converted to base64 before slicing and encoding.
- QR codes use error correction level `M` to improve recognition under light damage, stains, or folds.
- This tool is intended for storing already-encrypted ciphertext, such as exported Bitwarden vaults, encrypted wallet seeds, or GPG/PGP encrypted text.

## Files

- `auto_split_qr.py`: encode text/binary input into QR codes and produce printable Word pages
- `scanner_decoder.py`: decode scanned image folders and recover original text or bytes
- `gui.py`: Windows GUI with drag-and-drop file and folder support
- `build_gui_exe.bat`: Windows helper script to build the GUI executable
- `build_gui_linux.sh`: Linux helper script to build the GUI executable
- `.github/workflows/build-linux.yml`: GitHub Actions workflow for Linux builds

## Requirements

Install the required Python packages:

```bash
pip install segno python-docx pillow pyzbar customtkinter
```

> Note: `pyzbar` may require the system `zbar` library. On Linux, install `zbar` using your package manager.

## Build

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

The Linux build workflow runs on every push/PR to `main`/`master`, and can also be started manually from Actions.

## Usage

### 1) Generate printable QR pages

```bash
python auto_split_qr.py path/to/input.txt
```

- Output is created in the same directory as the input file.
- The script attempts to read the input as UTF-8 and encodes it in chunks.
- If UTF-8 decoding fails, the file is converted to base64 before encoding.
- The final QR code includes the original filename for recovery.

### 2) Decode scanned images and recover content

```bash
python scanner_decoder.py path/to/scanned_images_folder
```

- Scans `png`, `jpg`, and `jpeg` files in the specified directory.
- If no folder is given, it defaults to `scanned_pages`.
- If the QR stream contains an embedded filename, the recovered output is saved as `originalname_Recovered.ext`.
- Otherwise the result is saved as `foldername_Recovered.txt`.
- If the content was base64-encoded before encoding, it will be decoded back to original bytes.

### 3) Run the Windows GUI

```bash
python gui.py
```

The GUI supports:

- encoding a file to printable QR pages
- decoding a scanned image folder to recover data
- drag-and-drop input for files and folders
- selecting language mode: `auto`, `zh`, `jp`, or `en`

### 4) Language options

```bash
python auto_split_qr.py --lang zh path/to/input.txt
python auto_split_qr.py --lang jp path/to/input.txt
python auto_split_qr.py --lang en path/to/input.txt
python auto_split_qr.py --lang auto path/to/input.txt
```

```bash
python scanner_decoder.py --lang zh path/to/scanned_images_folder
python scanner_decoder.py --lang jp path/to/scanned_images_folder
python scanner_decoder.py --lang en path/to/scanned_images_folder
python scanner_decoder.py --lang auto path/to/scanned_images_folder
```

## Default Parameters

- Characters per chunk: `500`
- QR error correction level: `M`
- Page layout: `4 x 6`
- Page margin: `1.0 cm`

## Scanning Recommendations

- Use `300 DPI` or `600 DPI` for scanning
- Prefer grayscale or black-and-white modes
- Keep QR edges clear and avoid cutting off any part of the code
- If decoding fails for one QR, take a separate screenshot of that unreadable QR and place it in the same folder.

## Security Tips

- Printed ink is not waterproof; store pages in sealed protective sleeves.
- Paper backups should only contain encrypted ciphertext; unencrypted data can still be read.
- Keep the original decryption secret secure; if it is lost, recovery is not possible even if the QR pages remain intact.
