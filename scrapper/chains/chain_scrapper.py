from scrapper.chains.data.chain_mapper import ChainScrapperMapper
from scrapper.chains.data.chain_model import ChainData
from scrapper.scrapper import Scrapper


class ChainScrapper(Scrapper[ChainData]):

    def __init__(self, url: str, host: str, name: str):
        super().__init__(url, host, name, ChainScrapperMapper())
