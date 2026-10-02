import re

import regex
from pandas import Series

from utills import CleanBearingData, DirtyBearingData


def split_description(description: str) -> tuple[list[str], list[str]]:
    name_split = description.split(' ')
    type_parts = []
    name_parts = []
    for n_part in name_split:
        if regex.search(r'\p{IsCyrillic}', n_part) is not None and not re.search(r'\d', n_part):
            type_parts.append(n_part)
        else:
            name_parts.append(n_part)

    return type_parts, name_parts


def dirty_from_row(table_item: Series) -> DirtyBearingData:
    type_parts, name_parts = split_description(table_item["Description"])
    return DirtyBearingData(
        No_=str(table_item["No_"]),
        Description=table_item["Description"],
        Blocked=table_item['Blocked'],
        b_type=' '.join(type_parts),
    )

def from_clean_bearing(table_item: Series) -> CleanBearingData:
    return CleanBearingData(
        no=table_item['no'],
        description=table_item['description'],
        type=table_item['type'],
        dirty_type=table_item['dirty_type'],
        series=table_item['series'],
        internal_d=table_item['internal_d'],
        external_d=table_item['external_d'],
        width=table_item['width'],
        factory=table_item['factory'],
        c=table_item['c'],
        source_name=table_item['source_name'],
        source_link=table_item['source_link'],
        bearing_similarity=table_item['bearing_similarity']
    )


def from_dirty_bearing(row: DirtyBearingData) -> CleanBearingData:
    return CleanBearingData(
        no=row['No_'],
        description=row['Description'],
        type='',
        dirty_type=row['b_type'],
        series='',
        internal_d=0,
        external_d=0,
        width=0,
        factory='',
        c='',
        source_name='',
        source_link='',
        bearing_similarity=0.0
    )