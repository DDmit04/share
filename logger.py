import logging
from rich.logging import RichHandler

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-7s | %(threadName)-25s | %(name)s | %(message)s',
    datefmt='%H:%M:%S',
    handlers=[
    ],
)
