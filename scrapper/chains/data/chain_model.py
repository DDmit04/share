from scrapper.model import EntityData


class ChainData(EntityData):
    chain_step: float
    chain_val_d: float
    chain_rol_d: float
    chain_val_len: float
    chain_plate_height: float
    chain_plate_dist: float

    source_name: str
    source_link: str