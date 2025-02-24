import importlib.util
import multiprocessing
import sys
import time
from concurrent.futures import Future, ProcessPoolExecutor
from pathlib import Path
from typing import Callable

from rich import progress

from lib.config import MapoConfig, Script
from lib.helper import import_script


def task_runner(ipc_dict: dict, config: MapoConfig, task: dict) -> dict:
    try:
        action = import_script(task["data"]["script"], task["data"]["target"])
        result = action(ipc_dict, config, task)
        return result
    except Exception as e:
        raise Exception(f"{task['data']}: {e=}")


def batch_task_runner(
    p_bar: progress.Progress,
    executor: ProcessPoolExecutor,
    ipc_dict: dict,
    config: MapoConfig,
    tasks: list,
) -> list[Future]:
    task_total_progress = p_bar.add_task("summary", total=len(tasks), progress_type="summary")

    futures: list[Future] = []
    for i in range(0, len(tasks)):
        # add task to p_bar
        task_id = p_bar.add_task(
            tasks[i]["name"],
            visible=False,
            progress_type="download",
        )
        tasks[i]["task_id"] = task_id
        # add task to executor
        futures.append(executor.submit(task_runner, ipc_dict, config, tasks[i]))
    p_bar.update(task_total_progress, total=len(futures))

    while True:
        # check if any futures are done
        futures_finished = [x for x in futures if x.done()]
        try:
            for future in futures_finished:
                future.result()
        except Exception as e:
            for future in [x for x in futures if not x.done()]:
                future.cancel()
            raise e
        # update progress
        p_bar.update(
            task_total_progress,
            completed=len(futures_finished),
            total=len(futures),
        )
        for task_id, data in ipc_dict.items():
            p_bar.update(
                task_id,
                completed=data["completed_size"],
                total=data["total_size"],
                visible=data["completed_size"] < data["total_size"],
            )
        # stop if all futures are done
        if len(futures_finished) == len(futures):
            break

    return futures
