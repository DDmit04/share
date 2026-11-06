"""Живой прогресс скрапинга и тихие логи площадок.

Зачем: скрапер печатает несколько строк на каждую цепь (`Поиск`,
`Варианты`, `Поиск по URL`...). Когда площадки идут параллельно, консоль
превращается в кашу, и понять, сколько уже пройдено и сколько осталось,
невозможно. Поэтому:

* `Console` — единственный писатель в терминал. Держит блок строк прогресса,
  перерисовывает его на месте (ANSI) и печатает обычные сообщения так, чтобы
  не рвать этот блок.
* `ThreadStreamRouter` — подмена `sys.stdout`: каждый рабочий поток пишет в
  свой файл `logs/<site>.log`, остальные потоки идут в консоль. Болтливые
  `print` внутри скраперов больше не забивают прогресс.
* `ProgressBoard` — состояние площадок (строк пройдено, найдено, ETA) и
  отрисовка строк.

Если терминал не умеет двигать курсор (вывод в файл, консоль IDE), живой блок
заменяется обычным снимком раз в `PLAIN_SNAPSHOT_SECONDS`.
"""

from __future__ import annotations

import io
import logging
import os
import shutil
import sys
import threading
import time
from dataclasses import dataclass

#: Ширина колонки с именем площадки.
NAME_WIDTH = 22
#: Ширина полоски прогресса в символах.
BAR_WIDTH = 20
#: Как часто перерисовывать живой блок.
LIVE_REFRESH_SECONDS = 0.5
#: Как часто печатать снимок, когда живой блок недоступен.
PLAIN_SNAPSHOT_SECONDS = 30.0

WAITING = "ожидание"
RUNNING = "поиск"
DONE = "готово"
STOPPED = "остановлено"
FAILED = "ошибка"


def format_duration(seconds: float) -> str:
    """Секунды -> 'ММ:СС' или 'Ч:ММ:СС'; для неизвестного значения — '--:--'."""
    if seconds != seconds or seconds < 0:  # NaN или отрицательное
        return "--:--"
    total = int(round(seconds))
    hours, rest = divmod(total, 3600)
    minutes, secs = divmod(rest, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def format_bar(fraction: float, width: int = BAR_WIDTH, unicode: bool = True) -> str:
    """Полоска прогресса: 0.0 -> пустая, 1.0 -> заполненная."""
    fraction = 0.0 if fraction != fraction else min(max(fraction, 0.0), 1.0)
    filled = int(round(fraction * width))
    if unicode:
        return "█" * filled + "░" * (width - filled)
    return "#" * filled + "-" * (width - filled)


def _can_encode(stream, text: str) -> bool:
    encoding = getattr(stream, "encoding", None) or "utf-8"
    try:
        text.encode(encoding)
    except (UnicodeEncodeError, LookupError):
        return False
    return True


def _enable_vt(stream) -> bool:
    """Включает ANSI-последовательности в консоли Windows (идемпотентно)."""
    if os.name != "nt":
        return True
    try:
        import ctypes
        import msvcrt

        kernel32 = ctypes.windll.kernel32
        handle = msvcrt.get_osfhandle(stream.fileno())
        mode = ctypes.c_uint32()
        if not kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            return False
        enable_vt = 0x0004  # ENABLE_VIRTUAL_TERMINAL_PROCESSING
        if mode.value & enable_vt:
            return True
        return bool(kernel32.SetConsoleMode(handle, mode.value | enable_vt))
    except Exception:  # noqa: BLE001 — нет консоли, нет и ANSI
        return False


def should_use_live(stream) -> bool:
    """Можно ли рисовать перерисовывающийся блок в этом потоке."""
    try:
        if not stream.isatty():
            return False
    except Exception:  # noqa: BLE001
        return False
    # Консоль PyCharm понимает цвета, но не двигает курсор вверх.
    if os.environ.get("PYCHARM_HOSTED"):
        return False
    return _enable_vt(stream)


class Console:
    """Потокобезопасный писатель: сообщения не рвут блок прогресса."""

    def __init__(self, stream, *, live: bool = False):
        self._stream = stream
        self._lock = threading.RLock()
        self._live = bool(live) and _enable_vt(stream)
        self._lines: list[str] = []
        self._drawn = 0
        #: Терминал/файл умеет выводить █ и ░.
        self.unicode = _can_encode(stream, "█░")

    @property
    def live(self) -> bool:
        return self._live

    @property
    def width(self) -> int:
        """Ширина терминала в символах (для снимков/файлов — 120)."""
        try:
            return shutil.get_terminal_size((120, 24)).columns
        except Exception:  # noqa: BLE001
            return 120

    def log(self, message: str, *, error: bool = False) -> None:
        """Обычное сообщение: блок прогресса стирается, потом рисуется заново."""
        stream = sys.stderr if error else self._stream
        with self._lock:
            self._erase()
            for line in str(message).rstrip("\n").splitlines() or [""]:
                stream.write(line + "\n")
            stream.flush()
            self._draw()

    def block(self, lines: list[str]) -> None:
        """Несколько строк одним куском (снимок прогресса в не-live режиме)."""
        with self._lock:
            self._erase()
            for line in lines:
                self._stream.write(line + "\n")
            self._stream.flush()
            self._draw()

    def set_lines(self, lines: list[str]) -> None:
        """Новый блок прогресса; в не-live режиме просто запоминается."""
        with self._lock:
            self._lines = list(lines)
            if not self._live:
                return
            self._erase()
            self._draw()

    def close(self) -> None:
        """Стереть блок прогресса (перед итоговыми сообщениями)."""
        with self._lock:
            self._erase()
            self._lines = []
            self._stream.flush()

    def _erase(self) -> None:
        if self._live and self._drawn:
            # CPL: на `_drawn` строк вверх, в начало строки; ED: стереть до конца экрана.
            self._stream.write(f"\x1b[{self._drawn}F\x1b[J")
            self._drawn = 0

    def _draw(self) -> None:
        if self._live and self._lines:
            self._stream.write("\n".join(self._lines) + "\n")
            self._drawn = len(self._lines)
            self._stream.flush()


class ThreadStreamRouter(io.TextIOBase):
    """`sys.stdout`-прокси: поток со своим потоком вывода пишет в него, иначе — в общий."""

    def __init__(self, default_stream):
        self._default = default_stream
        self._local = threading.local()

    def bind(self, stream) -> None:
        """Направить вывод текущего потока в `stream`."""
        self._local.stream = stream

    def unbind(self) -> None:
        self._local.stream = None

    def _target(self):
        return getattr(self._local, "stream", None) or self._default

    # --- интерфейс текстового потока -------------------------------------
    def write(self, text: str) -> int:
        if not text:
            return 0
        try:
            self._target().write(text)
        except Exception:  # noqa: BLE001 — лог площадки не должен ронять скрапинг
            pass
        return len(text)

    def flush(self) -> None:
        try:
            self._target().flush()
        except Exception:  # noqa: BLE001
            pass

    def writable(self) -> bool:
        return True

    def readable(self) -> bool:
        return False

    def seekable(self) -> bool:
        return False

    def isatty(self) -> bool:
        return False

    @property
    def encoding(self) -> str:
        return getattr(self._default, "encoding", None) or "utf-8"

    def __getattr__(self, name):
        return getattr(self._default, name)


_router: ThreadStreamRouter | None = None
#: Куда вернуть `sys.stdout` при снятии маршрутизатора.
_previous_stdout = None


def install_router(default_stream=None) -> ThreadStreamRouter:
    """Подменить `sys.stdout` маршрутизатором; вернуть его же.

    `default_stream` — куда писать потокам без своего лога (по умолчанию —
    прежний `sys.stdout`). Прежний поток запоминается: `uninstall_router`
    вернёт именно его, а не переданный `default_stream`.
    """
    global _router, _previous_stdout
    _previous_stdout = sys.stdout
    _router = ThreadStreamRouter(_previous_stdout if default_stream is None else default_stream)
    sys.stdout = _router
    return _router


def uninstall_router() -> None:
    global _router, _previous_stdout
    if _router is not None:
        sys.stdout = _previous_stdout if _previous_stdout is not None else _router._default  # noqa: SLF001
        _router = None
        _previous_stdout = None


def router_active() -> bool:
    return _router is not None


def bind_worker_log(stream) -> None:
    if _router is not None:
        _router.bind(stream)


def unbind_worker_log() -> None:
    if _router is not None:
        _router.unbind()


class RouterLogHandler(logging.Handler):
    """Записи logger'а — в поток текущего рабочего потока, т.е. в лог его площадки."""

    def __init__(self, router: ThreadStreamRouter, level: int = logging.INFO):
        super().__init__(level)
        self._router = router
        self.setFormatter(logging.Formatter("%(asctime)s %(levelname)-5s %(message)s", "%H:%M:%S"))

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self._router.write(self.format(record) + "\n")
            self._router.flush()
        except Exception:  # noqa: BLE001
            self.handleError(record)


def attach_log_handler(name: str, level: int = logging.INFO) -> logging.Handler | None:
    """Логи `logging.getLogger(name)` в лог площадки; None, если маршрутизатор выключен."""
    if _router is None:
        return None
    handler = RouterLogHandler(_router, level)
    logger = logging.getLogger(name)
    logger.addHandler(handler)
    if logger.level == logging.NOTSET or logger.level > level:
        logger.setLevel(level)
    return handler


def detach_log_handler(name: str, handler: logging.Handler | None) -> None:
    if handler is None:
        return
    logging.getLogger(name).removeHandler(handler)
    handler.close()


@dataclass
class _SiteState:
    name: str
    total: int = 0
    scanned: int = 0
    found: int = 0
    skipped: int = 0
    status: str = WAITING
    error: str = ""
    started: bool = False
    started_at: float | None = None
    finished_at: float | None = None


class ProgressBoard:
    """Состояние площадок и отрисовка блока прогресса."""

    def __init__(
        self,
        console: Console,
        sites: list[str],
        *,
        total: int = 0,
        live: bool | None = None,
        interval: float | None = None,
    ):
        self._console = console
        self._order = list(sites)
        self._states = {name: _SiteState(name, total=total) for name in sites}
        self._lock = threading.Lock()
        self._live = console.live if live is None else live
        self._interval = interval or (LIVE_REFRESH_SECONDS if self._live else PLAIN_SNAPSHOT_SECONDS)
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._started_at = time.time()

    # --- данные -----------------------------------------------------------
    def update(
        self,
        site: str,
        *,
        scanned: int | None = None,
        total: int | None = None,
        found: int | None = None,
        skipped: int | None = None,
        status: str | None = None,
        error: str | None = None,
    ) -> None:
        with self._lock:
            state = self._states.get(site)
            if state is None:
                return
            if total is not None:
                state.total = total
            if scanned is not None:
                state.scanned = scanned
                state.started = True
            if found is not None:
                state.found = found
            if skipped is not None:
                state.skipped = skipped
            if error is not None:
                state.error = str(error)
            if status is not None:
                state.status = status
                if status == RUNNING:
                    state.started = True
                    if state.started_at is None:
                        state.started_at = time.time()
                elif status in (DONE, STOPPED, FAILED):
                    state.started = True
                    state.finished_at = state.finished_at or time.time()
                    if state.started_at is None:
                        state.started_at = state.finished_at

    # --- отрисовка --------------------------------------------------------
    def render(self) -> list[str]:
        with self._lock:
            states = [self._states[name] for name in self._order]
        lines = [self._summary(states)] + [self._site_line(state) for state in states]
        limit = max(self._console.width - 1, 10)
        # Строка длиннее терминала переносится и ломает позиционирование курсора.
        return [line[:limit] for line in lines]

    def _summary(self, states: list[_SiteState]) -> str:
        total = sum(state.total for state in states)
        scanned = sum(state.scanned for state in states)
        found = sum(state.found for state in states)
        running = sum(1 for state in states if state.status == RUNNING)
        finished = sum(1 for state in states if state.status in (DONE, STOPPED))
        errors = sum(1 for state in states if state.status == FAILED)
        percent = scanned / total * 100 if total else 0.0
        parts = [f"в работе {running} из {len(states)}", f"прошло {format_duration(time.time() - self._started_at)}"]
        if finished:
            parts.insert(1, f"готово {finished}")
        if errors:
            parts.insert(2 if finished else 1, f"ошибок {errors}")
        parts.append(f"строк {percent:.0f}%")
        parts.append(f"найдено {found}")
        full = "площадки: " + " · ".join(parts)
        limit = max(self._console.width - 1, 10)
        if len(full) <= limit:
            return full
        # Узкий терминал: оставляем самое важное, но без переноса строки.
        short = f"в работе {running} из {len(states)} · строк {percent:.0f}% · найдено {found}"
        return short[:limit]

    def _site_line(self, state: _SiteState) -> str:
        limit = max(self._console.width - 1, 10)
        name = state.name[:NAME_WIDTH].ljust(NAME_WIDTH)
        if not state.started and state.status == WAITING:
            return f"{name} ожидание"[:limit]
        total = max(state.total, 1)
        fraction = min(state.scanned / total, 1.0)
        percent = int(fraction * 100)
        elapsed = (state.finished_at or time.time()) - (state.started_at or time.time())

        tail = ""
        if state.status == RUNNING and state.scanned > 0:
            remaining = max(total - state.scanned, 0)
            tail = f"  ~{format_duration(elapsed / state.scanned * remaining)}"
        elif state.status == FAILED:
            tail = f"  ошибка: {state.error}"[:120]
        elif state.status == STOPPED:
            tail = "  остановлено"
        elif state.status == DONE:
            tail = "  готово"

        head = f"{name} "
        rest = (
            f" {percent:>3}% {state.scanned:>6}/{total:<6} найдено {state.found:>5} "
            f"{format_duration(elapsed):>7}"
        )
        # Полоска подстраивается, чтобы строка не переносилась в узком терминале:
        # перенос ломает перерисовку блока.
        available = limit - len(head) - len(rest) - len(tail)
        bar_width = max(5, min(BAR_WIDTH, available))
        bar = format_bar(fraction, bar_width, self._console.unicode)
        # Строка длиннее терминала переносится и ломает позиционирование курсора.
        return f"{head}{bar}{rest}{tail}"[:limit]

    def _snapshot(self) -> list[str]:
        """Текстовый снимок для не-live режима (файл, консоль IDE)."""
        with self._lock:
            states = [self._states[name] for name in self._order]
        now = time.strftime("%H:%M:%S")
        lines = [f"[{now}] {self._summary(states)}"]
        for state in states:
            if state.started:
                lines.append("  " + self._site_line(state))
        return lines
    # --- жизнь ------------------------------------------------------------
    def start(self) -> None:
        if self._thread is not None:
            return
        if self._live:
            self._console.set_lines(self.render())
        self._thread = threading.Thread(target=self._loop, name="progress", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None

    def _loop(self) -> None:
        while not self._stop.wait(self._interval):
            if self._live:
                self._console.set_lines(self.render())
            else:
                self._console.block(self._snapshot())
