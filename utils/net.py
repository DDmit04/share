"""Сетевые настройки по умолчанию.

Корпоративный прокси прописывается в переменные окружения, которые читает
`requests` (`trust_env=True` по умолчанию). Уже заданные снаружи значения не
перетираются — прокси можно переопределить перед запуском:

    set HTTP_PROXY=http://10.0.0.1:3128
    python -m pipeline.run ...
"""

from __future__ import annotations

import os

import urllib3

DEFAULT_PROXY = "http://172.31.24.36:8090"


def configure_proxies(proxy: str = DEFAULT_PROXY) -> None:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    for name in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
        if not os.environ.get(name):
            os.environ[name] = proxy
