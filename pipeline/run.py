"""Запуск скрапинга по нескольким площадкам и сборка двух итоговых файлов.

Примеры:
    python -m pipeline.run --input data.xlsx --out results
    python -m pipeline.run --sites bergab.ru,etm.ru --limit 20
    python -m pipeline.run --workers 4          # не более 4 площадок одновременно
    python -m pipeline.run --no-progress        # без живого дашборда
    python -m pipeline.run --verbose            # старый режим: весь вывод в консоль
    python -m pipeline.run --assemble-only
    python -m pipeline.run --list-sites

Устройство:
    results/raw/<site>.jsonl   — чекпоинт площадки (дописывается построчно,
                                 поэтому Ctrl+C и повторный запуск не теряют прогресс);
    results/logs/<site>.log    — весь вывод скрапера площадки (в тихом режиме);
    results/processed.xlsx     — по одной лучшей записи на цепь;
    results/unprocessed.xlsx   — исходные строки, для которых ничего не принято.

Площадки сканируются параллельно: каждая в своём потоке, со своим экземпляром
скрапера и своим чекпоинтом, поэтому потоки не делят ни состояние, ни файлы.
Входной xlsx разбирается один раз до старта потоков. Загрузка почти целиком
сетевая, так что GIL не мешает. `--workers` ограничивает число одновременных
площадок (по умолчанию — сколько площадок выбрано).

Прогресс по умолчанию показывается живым блоком (площадка, полоска, строки,
найдено, ETA); болтливые `print` скраперов уходят в `results/logs/<site>.log`.
Когда stdout не терминал (файл, консоль IDE), вместо живого блока раз в
30 секунд печатается снимок. `--verbose` возвращает прежнее поведение:
всё в консоль, без дашборда и лог-файлов.

Повторный запуск по умолчанию продолжает с места остановки (--fresh — начать заново).
"""

from __future__ import annotations

import argparse
import json
import sys
import threading
import time
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from pathlib import Path

import pandas as pd

from pipeline import progress
from pipeline.assemble import assemble, read_input
from pipeline.registry import SITES, resolve_sites
from scrapper.chains.data.chain_mapper import ChainScrapperMapper
from scrapper.chains.data.chain_model import ChainData
from scrapper.scrapper_mapper import ScrapperMapper

#: Пишет в консоль, пока идёт скрапинг; None — обычный print.
_console: progress.Console | None = None


def _log(message: str, *, error: bool = False) -> None:
    if _console is not None:
        _console.log(message, error=error)
    else:
        print(message, file=sys.stderr if error else sys.stdout, flush=True)


def _load_done(path: Path) -> set[str]:
    """Номера, которые уже успешно обработаны в этом чекпоинте.

    Ключ — `ChainData['id']` (колонка «Номер материала»), отдельного поля `no`
    в записи нет: оно дублировало бы `id`.
    """
    done: set[str] = set()
    if not path.exists():
        return done
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            done.add(str(json.loads(line).get("id", "")))
        except json.JSONDecodeError:
            # недописанная строка после аварийного завершения — просто перезапишем
            continue
    return done


def prepare_inputs(df: pd.DataFrame, mapper: ScrapperMapper) -> list[ChainData]:
    """Материализует входные строки в главном потоке.

    Потоки не должны делить DataFrame: `iterrows()` в pandas правит внутренние
    ссылки менеджера блоков. Один раз разбираем xlsx здесь — дальше потоки
    читают только неизменяемый список.
    """
    return [mapper.from_row(row) for _, row in df.iterrows()]


def run_site(
        name: str,
        scraper_cls: type,
        rows: list[ChainData],
        raw_dir: Path,
        *,
        limit: int = 0,
        fresh: bool = False,
        stop: threading.Event | None = None,
        board: progress.ProgressBoard | None = None,
        log_path: Path | None = None,
) -> dict:
    """Проходит площадку по входным строкам, дописывая найденное в jsonl.

    Выполняется в отдельном потоке (по одному на площадку). Всё состояние
    локальное: свой скрапер, свой чекпоинт, свои счётчики. `rows` только
    читается, `stop` позволяет главному потоку попросить площадку
    завершиться после текущей строки.

    `board` получает прогресс по строкам, а `log_path` забирает болтливые
    `print` скрапера: его вывод в этом потоке перенаправляется в файл.
    """
    path = raw_dir / f"{name}.jsonl"
    done = set() if fresh else _load_done(path)
    scraper = scraper_cls()
    total = len(rows)
    goal = min(limit, total) if limit else total
    scanned = skipped = found = no_variants = 0
    scrape_errors = 0
    started = time.time()

    log_handle = None
    log_handler = None
    if log_path is not None and progress.router_active():
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_handle = log_path.open("w" if fresh else "a", encoding="utf-8")
        progress.bind_worker_log(log_handle)
        log_handler = progress.attach_log_handler(name)

    if board is not None:
        board.update(name, status=progress.RUNNING, total=goal)

    try:
        with path.open("w" if fresh else "a", encoding="utf-8") as handle:
            for chain in rows:
                if stop is not None and stop.is_set():
                    break
                if limit and scanned >= limit:
                    break
                scanned += 1
                if board is not None:
                    board.update(name, scanned=scanned, found=found, skipped=skipped)
                elif scanned % 25 == 0:
                    _log(f"[{name}] {scanned}/{total}, найдено {found}")
                record_id = str(chain['id'])
                if record_id in done:
                    skipped += 1
                    continue

                try:
                    result = scraper.scrap(chain)
                except Exception as exc:  # noqa: BLE001 — одна строка не должна ронять площадку
                    scrape_errors += 1
                    if log_handle is not None:
                        # печать в этом потоке уходит в лог площадки, а не в консоль
                        print(f"[{name}] {record_id}: ошибка скрапинга: {exc}")
                    else:
                        _log(f"[{name}] {record_id}: ошибка скрапинга: {exc}", error=True)
                    result = None

                if result:
                    record = dict(result)
                    # ключ записи — `id` из ChainData, отдельное поле `no` не пишем
                    record["site"] = name
                    handle.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
                    handle.flush()
                    found += 1
    finally:
        progress.detach_log_handler(name, log_handler)
        if log_handle is not None:
            progress.unbind_worker_log()
            log_handle.close()

    return {
        "site": name,
        "scanned": scanned,
        "skipped": skipped,
        "found": found,
        "no_variants": no_variants,
        # плюс ошибки, которые скрапер проглотил внутри себя (запрос/разбор страницы)
        "errors": scrape_errors + getattr(scraper, "errors", 0),
        "stopped": stop is not None and stop.is_set() and scanned < goal,
        "seconds": time.time() - started,
    }


def _report(name: str, future: Future, board: progress.ProgressBoard | None = None) -> None:
    """Печатает итог площадки; падение одной площадки не мешает остальным."""
    try:
        stats = future.result()
    except Exception as exc:  # noqa: BLE001 — например, нет прав на запись чекпоинта
        if board is not None:
            board.update(name, status=progress.FAILED, error=str(exc))
        _log(f"[{name}] площадка упала: {exc}", error=True)
        return
    if board is not None:
        board.update(
            name,
            scanned=stats["scanned"],
            found=stats["found"],
            skipped=stats["skipped"],
            status=progress.STOPPED if stats.get("stopped") else progress.DONE,
        )
    _log(
        f"[{name}] просканировано {stats['scanned']}, "
        f"пропущено {stats['skipped']}, найдено {stats['found']}, "
        f"{stats['seconds']:.0f} c"
    )
    if stats.get("errors"):
        _log(
            f"[{name}] ошибок скрапинга: {stats['errors']} "
            f"(подробности — {name}.log)"
        )
    if stats["no_variants"]:
        _log(
            f"[{name}] без вариантов поиска в мэппинге: {stats['no_variants']} "
            f"(эти строки уйдут в unprocessed)"
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m pipeline.run",
        description="Скрапинг нескольких площадок и сборка processed/unprocessed.",
    )
    parser.add_argument("--input", default="data.xlsx", help="входной xlsx с цепями (колонки из ChainScrapperMapper)")
    parser.add_argument("--out", default="results", help="каталог результатов (по умолчанию results)")
    parser.add_argument("--sites", default="all", help="'all' или список через запятую")
    parser.add_argument("--limit", type=int, default=0, help="строк на площадку, 0 — все")
    parser.add_argument(
        "--workers",
        type=int,
        default=0,
        help="сколько площадок сканировать одновременно, 0 — все выбранные",
    )
    parser.add_argument(
        "--no-progress",
        action="store_true",
        help="без живого дашборда, только периодические снимки прогресса",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="старый режим: весь вывод скраперов в консоль, без дашборда и лог-файлов",
    )
    parser.add_argument("--assemble-only", action="store_true", help="только собрать файлы из чекпоинтов")
    parser.add_argument("--fresh", action="store_true", help="игнорировать чекпоинты площадок")
    parser.add_argument("--list-sites", action="store_true", help="показать известные площадки")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.list_sites:
        for name in SITES:
            print(name)
        return 0

    # Модель данных задаётся маппером: его `DIMENSIONS`, `COLUMN_TITLES` и
    # `score` использует и разбор входа, и сборка результатов. Для другого
    # товара здесь достаточно подставить другой маппер.
    mapper = ChainScrapperMapper()

    df = read_input(args.input, mapper)
    raw_dir = Path(args.out) / "raw"
    logs_dir = Path(args.out) / "logs"
    raw_dir.mkdir(parents=True, exist_ok=True)

    print(f"Входных строк: {len(df.index)}; площадок: {len(SITES)}; чекпоинты: {raw_dir}")

    interrupted = False
    logs_used = False
    if not args.assemble_only:
        sites = resolve_sites(args.sites)
        if not sites:
            _log("Не выбрано ни одной площадки — скрапинг пропущен.", error=True)

        workers = args.workers if args.workers > 0 else len(sites)
        workers = max(1, min(workers, len(sites)))

        # Входной xlsx разбираем один раз в главном потоке: дальше df не нужен.
        rows = prepare_inputs(df, mapper)
        goal = min(args.limit, len(rows)) if args.limit else len(rows)

        # Тихий режим: болтливые print скраперов уходят в logs/<site>.log,
        # а в консоли остаётся только живой прогресс.
        global _console
        quiet = not args.verbose
        live = quiet and not args.no_progress and progress.should_use_live(sys.stdout)
        _console = progress.Console(sys.stdout, live=live)
        router_installed = False
        if quiet:
            progress.install_router()
            router_installed = True

        board = None
        if quiet and not args.no_progress and sites:
            board = progress.ProgressBoard(_console, [name for name, _ in sites], total=goal)
            board.start()
        logs_used = quiet

        # Площадки идут параллельно: у каждой свой скрапер и свой чекпоинт,
        # строки входа (`rows`) только читаются.
        stop = threading.Event()
        pool = ThreadPoolExecutor(max_workers=workers, thread_name_prefix="site")
        futures = {
            pool.submit(
                run_site,
                name,
                scraper_cls,
                rows,
                raw_dir,
                limit=args.limit,
                fresh=args.fresh,
                stop=stop,
                board=board,
                log_path=(logs_dir / f"{name}.log") if quiet else None,
            ): name
            for name, scraper_cls in sites
        }
        if futures:
            where = f"; логи площадок: {logs_dir}" if quiet else ""
            _log(f"Площадок: {len(futures)}, одновременно {workers}{where}")
        reported: set[Future] = set()
        try:
            # Ждём короткими шагами: блокирующее ожидание «до первой готовой»
            # не прерывается сигналом, и Ctrl+C откладывался бы до конца
            # самой долгой площадки.
            pending = set(futures)
            while pending:
                finished, pending = wait(pending, timeout=0.5, return_when=FIRST_COMPLETED)
                for future in finished:
                    reported.add(future)
                    _report(futures[future], future, board)
        except KeyboardInterrupt:
            interrupted = True
            stop.set()
            for future in futures:
                future.cancel()
            _log(
                "\nПрервано пользователем. Останавливаю площадки на текущей строке "
                "и собираю то, что уже успели найти...",
            )
        finally:
            # Дожидаемся потоков: они дописывают чекпоинты (Ctrl+C — на границе строки),
            # иначе assemble читал бы файлы, которые ещё пишутся.
            try:
                pool.shutdown(wait=True)
            except KeyboardInterrupt:
                # Второй Ctrl+C. Ждать площадки всё равно придётся (join не
                # прерывается), но терять уже собранное из-за этого не нужно:
                # потоки к этому моменту уже остановились, дальше — сборка.
                _log("Повторный Ctrl+C: площадки уже остановлены, дособираю итоги.")
            finally:
                # После Ctrl+C прерванные площадки тоже должны показать свой итог:
                # сколько успели просканировать и найти.
                for future, name in futures.items():
                    if future in reported or future.cancelled() or not future.done():
                        continue
                    _report(name, future, board)
                if board is not None:
                    board.stop()
                _console.close()
                _console = None
                if router_installed:
                    progress.uninstall_router()

    stats = assemble(args.input, raw_dir, args.out, mapper)

    print("\nГотово:")
    print(f"  обработано строк:       {stats['input_rows']}")
    print(f"  найдено кандидатов:     {stats['candidates']}")
    print(f"  отброшено по сходству:  {stats['rejected_low_similarity']}")
    print(f"  без характеристик (0):  {stats['rejected_no_dimensions']}")
    print(f"  processed:              {stats['processed']}  -> {stats['processed_path']}")
    print(f"  unprocessed:            {stats['unprocessed']}  -> {stats['unprocessed_path']}")
    if logs_used:
        print(f"  логи площадок:          {logs_dir}")

    if interrupted:
        print("\nЗапуск был прерван: результаты неполные. Продолжить — повторить команду; "
              "пересобрать — --assemble-only.")
        return 130
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
