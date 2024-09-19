import multiprocessing
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from rich import progress

from lib.helper import Cache, SummaryProgress, load_script
from lib.log import LogLevel, console, log, log_error, log_list, log_title


def do_task(_p_stats: dict, task_id: int, script: Path, config: dict, cache: Cache):
    try:
        module = load_script(script)
        module.update(
            _p_stats,
            task_id,
            script,
            config,
            cache,
        )

        # get installed version
        path_latest = Path(config["path"]["data"]) / f"{script.stem}/latest"
        if path_latest.exists():
            latest_version = path_latest.resolve().name
        else:
            latest_version = "None"

        # get remote version
        cache.load()
        remote_version = cache["remote_version"]

        return (script.stem, latest_version, remote_version)

    except Exception as e:
        raise Exception(f"during update: {e=}\n{script=}")


def batch_do_check(_prog: progress.Progress, _p_stats: dict, executor: ProcessPoolExecutor, scripts: list[Path], config: dict):
    p_task_summary = _prog.add_task("summary", total=len(scripts), progress_type="summary")

    futures = []
    for i in range(0, len(scripts)):
        cache = Cache(scripts[i].parent.parent / f"cache/{scripts[i].stem}.json")
        # task
        task_id = _prog.add_task(
            f"{scripts[i].stem}",
            visible=False,
            progress_type="download",
        )
        futures.append(executor.submit(do_task, _p_stats, task_id, scripts[i], config, cache))
    _prog.update(p_task_summary, total=len(futures))

    while True:
        # check if any futures are done
        finished_futures = [x for x in futures if x.done()]
        try:
            for future in finished_futures:
                future.result()
        except Exception as e:
            for future in [x for x in futures if not x.done()]:
                future.cancel()
            raise e
        # update progress
        _prog.update(
            p_task_summary,
            completed=len(finished_futures),
            total=len(futures),
        )
        for task_id, (completed, total) in _p_stats.items():
            _prog.update(
                task_id,
                completed=completed,
                total=total,
                visible=completed < total,
            )
        # stop if all futures are done
        if len(finished_futures) == len(futures):
            break

    return futures


def do_update(scripts: list[Path], config: dict, args: list[str]):
    max_workers = config["worker"]["update"]

    try:
        log_title(f"Checking for updates for {len(scripts)} script")

        with SummaryProgress(
            "[progress.description]{task.description}",
            progress.BarColumn(bar_width=None),
            "[progress.percentage]{task.percentage:>3.0f}%",
            progress.TimeRemainingColumn(),
            progress.TimeElapsedColumn(),
            refresh_per_second=5,
        ) as _prog:
            with ProcessPoolExecutor(max_workers=max_workers) as executor:
                with multiprocessing.Manager() as manager:
                    _p_stats = manager.dict()
                    futures = batch_do_check(_prog, _p_stats, executor, scripts, config)

        # show available updates
        results = []
        for future in futures:
            name, latest_version, remote_version = future.result()
            if remote_version != latest_version:
                results.append((name, latest_version, remote_version))
        log_title(f"{len(results)} available updates")
        log_list([f"{x[0]}: {x[1]} -> {x[2]}" for x in results])

    except Exception as e:
        log.error(e)
        sys.exit(1)
