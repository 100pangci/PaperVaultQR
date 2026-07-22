# PaperVaultQR

[![CI](https://github.com/100pangci/PaperVaultQR/actions/workflows/ci.yml/badge.svg)](https://github.com/100pangci/PaperVaultQR/actions/workflows/ci.yml)
[![License: MPL-2.0](https://img.shields.io/badge/License-MPL_2.0-blue.svg)](LICENSE)
![Platform: Windows | Linux](https://img.shields.io/badge/Platform-Windows%20|%20Linux-lightgrey)

> **English** [README.md](README.md) · **中文** [README.zh.md](README.zh.md) · **日本語** [README.jp.md](README.jp.md) · **조선어** [README.ko_kp.md](README.ko_kp.md)

PaperVaultQR разбивает текстовые файлы на несколько QR-кодов, генерирует документ Word для печати и восстанавливает исходное содержимое из папки отсканированных QR-изображений. Предназначен для **офлайн-бумажного резервного копирования зашифрованных данных с высокой энтропией** — таких как экспортированные хранилища Bitwarden, зашифрованные seed-фразы кошельков или GPG/PGP-шифротекст.

---

## Скриншоты

![Русский интерфейс](Picture/PaperVaultQR_ru_ru.png)

## Логотип

| Светлая тема | Тёмная тема |
|---|---|
| ![Светлый](Picture/LOGO_dark_white.png) | ![Тёмный](Picture/LOGO_white_dark.png) |

---

## Возможности

- Разбивка входных файлов на фрагменты по `500` символов в виде QR-кодов
- Автоматическое преобразование файлов не в UTF-8 в `base64` перед кодированием и восстановление при декодировании
- Генерация документа Word для печати (A4, поля `1.0 см`, многоколоночный макет)
- Сохранение исходного имени файла в последовательности QR-кодов для точного восстановления
- Декодирование `png`, `jpg`, `jpeg` из отсканированной папки в порядке имён и восстановление текста или двоичных данных
- Межблочная коррекция ошибок Рида-Соломона — добавление избыточных QR-блоков (0–100%) для восстановления при потере или повреждении сканов
- Графический интерфейс (customtkinter) и CLI, с `auto` и 22 встроенными локалями

## Примечания

- Ввод в UTF-8 использует прямое нарезание текста и кодирование в QR. Файлы не в UTF-8 сначала преобразуются в `base64`.
- QR-коды используют уровень коррекции ошибок `M` для повышения распознавания при лёгких повреждениях, пятнах или сгибах.
- Выходные файлы используют локализованные суффиксы: `_ColdStorage`, `_冷存储`, `_コールドストレージ`.
- Восстановленные файлы сохраняются в родительской директории папки сканирования; исходное имя файла сохраняется с суффиксом восстановления.
- **Инструмент предназначен только для уже зашифрованных данных.**

---

## Требования

- Python 3.10+

```bash
pip install segno python-docx pillow pyzbar customtkinter numpy reedsolo
```

> **Примечание:** `pyzbar` требует системную библиотеку `zbar` на Linux (`sudo apt-get install libzbar0`). Установите `pyinstaller`, если требуется локальная сборка GUI.

---

## Быстрый старт

### Генерация страниц QR для печати

```bash
python src/core/auto_split_qr.py path/to/input.txt
```

Можно передать несколько файлов одновременно. Вывод сохраняется рядом с входным файлом с локализованным суффиксом.

### Восстановление отсканированного содержимого

```bash
python src/core/scanner_decoder.py path/to/scanned_images_folder
```

По умолчанию используется `./scanned_pages`. Читает `png`, `jpg`, `jpeg`.

### Запуск графического интерфейса

```bash
python src/gui.py
```

---

## CLI

### Выбор языка

```bash
python src/core/auto_split_qr.py --lang zh_cn path/to/input.txt
python src/core/auto_split_qr.py --lang en_us path/to/input.txt
python src/core/auto_split_qr.py --lang ru_ru path/to/input.txt
python src/core/auto_split_qr.py --lang auto path/to/input.txt
```

```bash
python src/core/scanner_decoder.py --lang ru_ru path/to/scanned_images_folder
python src/core/scanner_decoder.py --lang auto path/to/scanned_images_folder
```

### Поддерживаемые локали

`auto`, `bo`, `da_dk`, `de_de`, `en_us`, `es_es`, `fr`, `he_il`, `hi_in`, `it_it`, `ja_jp`, `ko_kp`, `ko_kr`, `pt_br`, `ru_ru`, `th_th`, `tr`, `ug_cn`, `uk_ua`, `vi_vn`, `zh_cn`

---

## GUI

- Выбор одного или нескольких файлов для кодирования
- Выбор папки для декодирования
- Язык: `auto` или любая встроенная локаль
- Редактирование **настроек макета QR** перед кодированием:

| Параметр | Описание |
|---|---|
| Размер фрагмента | Символов на QR-код |
| Уровень ошибки QR | `L` / `M` / `Q` / `H` |
| Межблочная коррекция ошибок | RS избыточность 0–100% (0 = выкл.) |
| Ширина QR (см) | Ширина каждого QR на странице |
| Размер шрифта метки | Размер шрифта подписи QR |
| Колонок на странице | Количество колонок в таблице Word |
| Поля страницы (см) | Поля документа |

Нажмите **Восстановить по умолчанию** для сброса к заводским настройкам.

---

## Параметры по умолчанию

| Параметр | Значение |
|---|---|
| Символов на фрагмент | 500 |
| Уровень коррекции ошибок QR | `M` |
| Межблочная RS-коррекция | 0 (отключено) |
| Поля страницы | 1.0 см |
| Размер страницы | A4 |
| Колонок в макете | 4 |

---

## Рекомендации по сканированию

- Используйте **300 DPI** или **600 DPI**
- Предпочитайте режим оттенков серого или чёрно-белый
- Сохраняйте QR-код полным, избегайте обрезки краёв
- Если один QR не читается, обрежьте его и попробуйте снова

---

## Результаты тестирования

- Нагрузка **313 КБ** → **642** QR-кода
- После печати и сканирования только **2** QR не декодировались; кадрирование и повторная попытка устранили проблему

---

## Советы по безопасности

- Струйная печать **не водостойка**; используйте герметичные конверты или ламинирование
- Бумажные копии должны содержать **только зашифрованные данные**
- Храните секрет расшифровки в безопасности; без него восстановление невозможно

---

## Структура проекта

```
PaperVaultQR/
├── src/
│   ├── core/
│   │   ├── auto_split_qr.py    # Кодирование ввода в QR и генерация Word
│   │   └── scanner_decoder.py  # Декодирование сканов и восстановление
│   ├── i18n/
│   │   ├── core_texts.py       # Строки CLI i18n
│   │   ├── ui_texts.py         # Строки GUI i18n
│   │   └── locales/            # Файлы перевода (22 языка)
│   ├── gui.py                  # GUI (customtkinter)
│   ├── app_version.py          # Утилита версии
│   └── icon/                   # Иконки приложения
├── Picture/                    # Скриншоты и логотипы
├── scripts/                    # Вспомогательные скрипты разработки
├── build/                      # Артефакты сборки
├── build_gui_exe.bat           # Скрипт сборки для Windows (PyInstaller)
├── build_gui_linux.sh          # Скрипт сборки для Linux (PyInstaller)
├── gui.spec                    # Файл спецификации PyInstaller (устар.)
└── .github/workflows/
    ├── ci.yml                  # Проверка синтаксиса и импорта
    └── release.yml             # Сборка и релиз по тегу v*
```

---

## Сборка

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

Пуш тега `v*` запускает **release.yml**, который собирает исполняемые файлы для Windows и Linux и создаёт GitHub Release.

---

## Разработка

```bash
git clone https://github.com/100pangci/PaperVaultQR.git
cd PaperVaultQR
python -m venv .venv
# .venv\Scripts\activate  (Windows)
# source .venv/bin/activate (Linux)
pip install segno python-docx pillow pyzbar customtkinter numpy reedsolo
```

### Стиль кода

PEP 8, ограничение длины строки 120 символов, проверка через [Flake8](.flake8):

```bash
python -m flake8 src/ --max-line-length=120
```

---

## Roadmap

> 

---

## FAQ

> 

---

## Лицензия

[Mozilla Public License 2.0](LICENSE)

---

## Благодарности

- [segno](https://github.com/heuer/segno) — генерация QR-кодов
- [python-docx](https://github.com/python-openxml/python-docx) — создание документов Word
- [customtkinter](https://github.com/TomSchimansky/CustomTkinter) — современный GUI-тулкит
- [pyzbar](https://github.com/NaturalHistoryMuseum/pyzbar) — декодирование QR/штрих-кодов
- [reedsolo](https://pypi.org/project/reedsolo/) — коррекция ошибок Рида-Соломона
- [Pillow](https://pypi.org/project/pillow/) — обработка изображений
- [NumPy](https://numpy.org/) — численные расчёты
