from scrapper.chains.mapper import ChainScrapperMapper
from scrapper.chains.model import ChainData
from scrapper.scrapper import Scrapper


class ChainScrapper(Scrapper[ChainData]):

    def __init__(self, url: str, host: str, name: str):
        super().__init__(url, host, name, ChainScrapperMapper())
