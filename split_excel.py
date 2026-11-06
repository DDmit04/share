"""Разбивает 2_Ремень.xlsx на файлы по 50 строк и кладёт их в папку chunks.

Заголовок из первой строки копируется в каждый файл, 50 строк считаются
строками данных (без заголовка).
"""

from pathlib import Path

import openpyxl

BASE_DIR = Path(__file__).resolve().parent
SOURCE = BASE_DIR / "4_Цепь.xlsx"
OUT_DIR = BASE_DIR / "chunks"
CHUNK_SIZE = 50


def main():
    wb = openpyxl.load_workbook(SOURCE)
    ws = wb.active

    rows = list(ws.iter_rows(values_only=True))
    header, data = rows[0], rows[1:]

    if not data:
        print(f"В файле {SOURCE.name} нет данных.")
        return

    OUT_DIR.mkdir(exist_ok=True)

    files = 0
    for number, start in enumerate(range(0, len(data), CHUNK_SIZE), start=1):
        part = data[start:start + CHUNK_SIZE]

        out_wb = openpyxl.Workbook()
        out_ws = out_wb.active
        out_ws.title = ws.title
        out_ws.append(header)
        for row in part:
            out_ws.append(row)

        name = f"2_Цепи_{number:03d}.xlsx"
        out_wb.save(OUT_DIR / name)
        files += 1
        print(f"{name}: строк данных {len(part)}")

    print(f"Готово: {files} файлов в {OUT_DIR}")


if __name__ == "__main__":
    main()
