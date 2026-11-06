"""Ручное прохождение JS-проверки браузера («Проверяем поддержку браузера...»).

Сайт отдаёт вместо страницы заглушку со статусом 200: её скрипт ставит cookie
`pa_js_passed` (подписанный токен) и перезагружает страницу уже с ним. `requests`
JavaScript не исполняет, поэтому проверку проходим один раз в браузере, а
полученную строку Cookie переиспользуем в запросах.

Здесь только этот ручной путь:

- `looks_like_challenge` — распознать заглушку вместо разметки;
- `apply_cookies` — положить строку Cookie из браузера в `requests.Session`.

Cookie живут ограниченное время: когда протухнут, скрапер скажет об этом
(`ChallengeError`), и строку нужно будет скопировать из браузера заново.
"""

from __future__ import annotations

import os
from urllib.parse import urlparse

#: Признаки заглушки в тексте ответа. Заглушка короткая, поэтому ищем только
#: в начале документа — настоящие страницы эти фразы не содержат.
MARKERS = (
    "проверяем поддержку браузера",
    "проверяем ваш браузер",
    "проверка браузера",
    "проверяем браузер",
    "проверяем, что вы не робот",
    "подтвердите, что вы не робот",
    "checking your browser",
    "just a moment",
    "enable javascript and cookies to continue",
    "cf-browser-verification",
    "ddos-guard",
)


class ChallengeError(RuntimeError):
    """Проверку браузера пройти не удалось."""


def looks_like_challenge(payload: str | bytes) -> bool:
    """Похоже ли, что вместо страницы пришла заглушка антибота.

    Принимает и `str`, и сырые байты ответа: у заглушки может не быть
    `charset` в заголовках, и тогда `response.text` ломает кириллицу.
    """
    if not payload:
        return False
    if isinstance(payload, bytes):
        probe = payload[:20000].decode("utf-8", errors="ignore")
    else:
        probe = payload[:20000]
    probe = probe.lower()
    return any(marker in probe for marker in MARKERS)


def parse_cookies(raw: str) -> dict[str, str]:
    """Разбирает строку `a=1; b=2` (значение заголовка Cookie)."""
    cookies: dict[str, str] = {}
    for part in raw.split(";"):
        name, _, value = part.partition("=")
        name = name.strip()
        value = value.strip()
        if name and value:
            cookies[name] = value
    return cookies


def apply_cookies(
    session,
    url: str,
    *,
    cookie_raw: str = "",
    cookie_env: str | None = None,
) -> None:
    """Кладёт в сессию cookie из браузера, после которых приходят настоящие страницы.

    `cookie_raw` — строка Cookie, вставленная прямо в код; `cookie_env` — имя
    переменной окружения с такой же строкой (используется, только если
    `cookie_raw` пустая).
    """
    host = urlparse(url).hostname or ""
    raw = (cookie_raw or "").strip()
    source = "COOKIES"
    if not raw and cookie_env:
        raw = (os.environ.get(cookie_env) or "").strip()
        source = cookie_env
    cookies = parse_cookies(raw) if raw else {}
    if not cookies:
        raise ChallengeError(
            "сайт требует проверку браузера, а cookie не заданы. Откройте "
            "euromehanika.ru в браузере, скопируйте заголовок Cookie "
            "(F12 → Network → любой запрос → Request Headers) и вставьте его "
            "в константу COOKIES скрапера или в переменную EUROMEHANIKA_COOKIE."
        )

    # Старые cookie (например PHPSESSID из ответа с заглушкой) заменяем целиком.
    for stale in list(session.cookies):
        session.cookies.clear(stale.domain, stale.path, stale.name)
    for name, value in cookies.items():
        session.cookies.set(name, value, domain=host)
    print(f"Антибот: применены cookie из {source} ({len(cookies)} шт.)")
