"""Перенос оформления входного xlsx на итоговые файлы.

Значения пишет pandas, а внешний вид — этот модуль: ширины колонок, оформление
шапки и строк, форматы чисел, закрепление шапки. Без него `processed.xlsx`
выглядит как «сырая» выгрузка pandas, а не как таблица, с которой работают.

Колонки сопоставляются по заголовкам, а не по позициям: набор колонок у входа
и выхода одинаковый, но опираться на порядок всё равно не стоит.
"""

from __future__ import annotations

from copy import copy
from pathlib import Path

from openpyxl import load_workbook
from openpyxl.cell.cell import Cell
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet


def _titles(sheet: Worksheet) -> dict[int, str]:
    """Заголовки колонок: индекс колонки -> текст шапки."""
    titles: dict[int, str] = {}
    for column in range(1, sheet.max_column + 1):
        value = sheet.cell(row=1, column=column).value
        if value is not None:
            titles[column] = str(value).strip()
    return titles


def _copy_cell_style(source: Cell, target: Cell) -> None:
    """Переносит оформление ячейки, не трогая её значение."""
    target.font = copy(source.font)
    target.fill = copy(source.fill)
    target.border = copy(source.border)
    target.alignment = copy(source.alignment)
    target.protection = copy(source.protection)
    target.number_format = source.number_format


def copy_style(source: str | Path, target: str | Path) -> None:
    """Переносит оформление входной книги на итоговый файл.

    `target` уже содержит значения (его записал pandas); меняется только вид:
    ширина и видимость колонок, оформление шапки, оформление и формат чисел
    обычных строк, закреплённая шапка, высота её строки и автофильтр.

    Оформление строк берётся из первой строки данных источника: таблицы такого
    вида обычно оформлены ровно так, без чередования и отдельных исключений.
    """
    # Первый лист — тот же, что читает и пишет pandas (sheet_name=0).
    source_sheet = load_workbook(source).worksheets[0]
    target_book = load_workbook(target)
    target_sheet = target_book.worksheets[0]

    source_columns = {title: column for column, title in _titles(source_sheet).items()}
    for target_column, title in _titles(target_sheet).items():
        source_column = source_columns.get(title)
        if source_column is None:
            # колонки нет во входном файле — оставляем оформление pandas
            continue

        source_letter = get_column_letter(source_column)
        source_dimension = source_sheet.column_dimensions.get(source_letter)
        if source_dimension is not None and source_dimension.width:
            target_letter = get_column_letter(target_column)
            target_sheet.column_dimensions[target_letter].width = source_dimension.width
            target_sheet.column_dimensions[target_letter].hidden = source_dimension.hidden

        _copy_cell_style(
            source_sheet.cell(row=1, column=source_column),
            target_sheet.cell(row=1, column=target_column),
        )
        # Обычные строки оформлены как первая строка данных источника.
        if source_sheet.max_row > 1 and target_sheet.max_row > 1:
            template = source_sheet.cell(row=2, column=source_column)
            for row in range(2, target_sheet.max_row + 1):
                _copy_cell_style(template, target_sheet.cell(row=row, column=target_column))

    if source_sheet.freeze_panes:
        target_sheet.freeze_panes = source_sheet.freeze_panes
    header_height = source_sheet.row_dimensions[1].height
    if header_height:
        target_sheet.row_dimensions[1].height = header_height
    if source_sheet.auto_filter.ref:
        target_sheet.auto_filter.ref = target_sheet.dimensions

    target_book.save(target)
