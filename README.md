# PaperVaultQR

PaperVaultQR splits any UTF-8 text file into multiple QR codes, generates a printable Word document, and recovers the original text from scanned QR image folders. It is designed for offline paper backup of high-entropy encrypted data.

## Screenshots

Below is a screenshot of the software's GUI. The image is located in the `Picture` folder:

- English UI: `Picture/PaperVaultQR_EN.png`

![PaperVaultQR English GUI](Picture/PaperVaultQR_EN.png)

## Features

- Encode any text file into QR codes using plain slicing mode
- Generate a Word document with a `4 x 6` QR layout and `1.0 cm` page margins
- Automatically embed the original filename in the final QR for name-preserving recovery
- Decode scanned `png`, `jpg`, and `jpeg` images from a folder and restore text in order
- CLI and Windows GUI support
- Console and GUI language options: `auto`, `zh`, `en`

## Files

- `auto_split_qr.py`: encode a text file and generate printable QR pages
- `scanner_decoder.py`: decode scanned QR image folders and recover the original text
- `gui.py`: Windows GUI with drag-and-drop and button control
- `build_gui_exe.bat`: helper script to build a GUI executable

## Requirements

Install the required Python packages:

```bash
pip install segno python-docx pillow pyzbar customtkinter
```

Note: `pyzbar` may require the system `zbar` library. On Linux install `zbar` via your package manager.

## Usage

### 1) Generate printable QR pages

```bash
python auto_split_qr.py path/to/input.txt
```

- Output is created in the same directory as the input file.
- Example output filename: `input_ColdStorage.docx`.
- The script reads the input file as UTF-8 text and slices it into 500-character QR chunks.

### 2) Decode scanned images and recover text

```bash
python scanner_decoder.py path/to/scanned_images_folder
```

- Scans `png`, `jpg`, and `jpeg` files in the target folder.
- If no folder argument is provided, it defaults to `scanned_pages`.
- If the QR stream contains an embedded filename, the recovered file is saved as `originalname_Recovered.ext`.
- Otherwise the output is saved as `foldername_Recovered.txt`.

### 3) Run the Windows GUI

```bash
python gui.py
```

The GUI supports:

- encoding a text file to QR pages
- decoding a scanned image folder
- native drag-and-drop input for files and folders
- choosing the language mode (`auto`, `zh`, `en`)

### 4) Language options

```bash
python auto_split_qr.py --lang zh path/to/input.txt
python auto_split_qr.py --lang en path/to/input.txt
python auto_split_qr.py --lang auto path/to/input.txt
```

```bash
python scanner_decoder.py --lang zh path/to/scanned_images_folder
python scanner_decoder.py --lang en path/to/scanned_images_folder
python scanner_decoder.py --lang auto path/to/scanned_images_folder
```

## Output

- Encoder: creates a printable Word document containing QR codes.
- Decoder: writes a recovered text file to the parent directory of the scanned image folder.

## Default parameters

- Characters per chunk: `500`
- QR error correction level: `M`
- Page layout: `4 x 6`
- Page margin: `1.0 cm`

## Notes

- `auto` language mode detects Chinese or English based on the system locale.
- For best scanning results, use `300` or `600 DPI` in grayscale or black-and-white mode.
- Keep printed QR pages protected from moisture and handle them as encrypted backups.
