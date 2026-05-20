# PaperVaultQR

English (default). For the Chinese version, see: [README.zh.md](README.zh.md)

PaperVaultQR splits text into multiple QR codes, generates a printable Word document,
and can recover the original text from scanned pages that contain these QR codes.

## Features

- Split `split_qr.json` into multiple QR codes
- Generate a Word document suitable for printing
- Decode scanned images to recover the original text
- Console output supports Chinese and English

## Files

- `auto_split_qr.py`: create printable QR pages
- `scanner_decoder.py`: decode scanned pages and recover text
- `split_qr.json`: input text to be split
- `scanned_pages/`: folder for scanned images
- `冷存储.docx` / `cold_storage.docx`: generated printable document
- `decoder.json`: recovered output

## Requirements

Install the required Python packages:

```bash
pip install segno python-docx pillow pyzbar
```

Note: `pyzbar` may require the system `zbar` library to be installed.

## Usage

1) Generate printable QR pages

Place the input text in `split_qr.json`, then run:

```bash
python auto_split_qr.py
```

You can also drag-and-drop a file onto the script (or pass a file path) to encode that file into QR pages:

```bash
python auto_split_qr.py path/to/input.txt
```

If you drag or pass a folder path, the script will run the decoder on that folder (useful when you have scanned images saved in a folder):

```bash
python auto_split_qr.py path/to/scanned_images_folder/
```

3) GUI (drag-and-drop)

On Windows you can use the provided GUI which accepts native drag-and-drop of files or folders. It will run encoding for files and decoding for folders in background threads:

```bash
python gui.py
```

Use the buttons if your platform doesn't support native drag-and-drop.

Language options:

```bash
python auto_split_qr.py --lang zh
python auto_split_qr.py --lang en
python auto_split_qr.py --lang auto
```

2) Scan and recover text

Place scanned images into `scanned_pages/`, then run:

```bash
python scanner_decoder.py
```

Language options:

```bash
python scanner_decoder.py --lang zh
python scanner_decoder.py --lang en
python scanner_decoder.py --lang auto
```

You can also call the decoder programmatically or point it at a specific folder:

```bash
python scanner_decoder.py --lang en
# or
python -c "import scanner_decoder; scanner_decoder.decode_folder('scanned_pages', lang='en')"
```

## Output

- The generator produces a Word document for printing.
- The decoder writes `decoder.json` with the recovered text.

## Default parameters

- Characters per chunk: `500`
- QR error correction level: `M`
- Page layout: `4 x 6` per page
- Page margin: `1.0 cm`

## Notes

- `auto` chooses Chinese or English according to system language.
- For best recognition, scan at 300 or 600 DPI in grayscale.
