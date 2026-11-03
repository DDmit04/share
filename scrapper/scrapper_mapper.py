from abc import ABC

from pandas import Series


class ScrapperMapper[EntityData](ABC):
    def from_row(self, ser: Series) -> EntityData:
        pass

    def get_name_variants(self, data: EntityData) -> list[str]:
        pass
