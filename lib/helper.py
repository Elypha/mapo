import importlib.util
import multiprocessing
import os
import platform
import re
import subprocess
import shutil
import sys
import time
from concurrent.futures import Future, ProcessPoolExecutor
from pathlib import Path
from typing import Callable

import httpx
import orjson
from rich import progress

from lib.config import MapoConfig, Script
from lib.log import console, log

client = httpx.Client(
    headers={
        "User-Agent": f"Mapo/0.1 (Python {platform.python_version()}, httpx/{httpx.__version__}; {platform.system()} {platform.release()}) +github.com/Elypha/Mapo",
    }
)


def update_helper_github(ipc_progress: dict, config: MapoConfig, task: dict, args: dict) -> tuple[str, str]:
    # supports:
    # api.github.com
    #
    # args:
    url: str = args["url"]
    regex_asset: re.Pattern = args["regex_asset"]
    regex_version: re.Pattern = args["regex_version"]  # use group: version

    script: Script = task["data"]["script"]

    # fetch remote
    ipc_progress[task["task_id"]] = (0, 2)
    response = client.get(url, follow_redirects=True)

    # process data
    ipc_progress[task["task_id"]] = (1, 2)
    response.raise_for_status()
    data = response.json()
    if isinstance(data, list):
        data = data[0]

    # remote version
    remote_version = regex_version.search(data["tag_name"]).group("version")
    if remote_version is None:
        log.error(f"{task['name']}: no matched version")
        exit(1)
    old_remote_version = script.cache.get("remote_version", None)
    script.cache["remote_version"] = remote_version

    # download_url
    for asset in data["assets"]:
        if regex_asset.match(asset["name"]):
            download_url = asset["browser_download_url"]
            break
    else:
        log.error(f"{task['name']}: no matched download_url")
        exit(1)
    script.cache["download_url"] = download_url

    script.save_cache()
    ipc_progress[task["task_id"]] = (2, 2)

    return (old_remote_version, script.cache["remote_version"])


def download_helper(ipc_progress: dict, config: MapoConfig, task: dict) -> Path:
    script: Script = task["data"]["script"]

    dl_file_dir: Path = script.app_path / script.cache["remote_version"]
    dl_file_dir.mkdir(parents=True, exist_ok=True)

    _ext = script.cache["download_url"].split(".")[-1]
    dl_file_path = dl_file_dir / f"dl_{script.cache['remote_version']}.{_ext}"
    dl_file_path.unlink(missing_ok=True)

    # download
    with open(dl_file_path, "wb") as f:
        ipc_progress[task["task_id"]] = (0, 1)
        with client.stream("GET", script.cache["download_url"], follow_redirects=True) as response:
            if "Content-Length" in response.headers:
                total = int(response.headers["Content-Length"]) + 1
                for chunk in response.iter_bytes():
                    f.write(chunk)
                    ipc_progress[task["task_id"]] = (response.num_bytes_downloaded, total)
            else:
                for chunk in response.iter_bytes():
                    f.write(chunk)
                    total = response.num_bytes_downloaded
                    ipc_progress[task["task_id"]] = (total, total + 1)

    return dl_file_path


def remove_helper(_p_stats: dict, task_id: int, script: Path, config: dict, cache: dict):
    # args
    path_app = Path(config["path"]["data"]) / script.stem

    # uninstall
    shutil.rmtree(path_app)


class SummaryProgress(progress.Progress):
    def get_renderables(self):
        for task in self.tasks:
            if task.fields.get("progress_type") == "summary":
                self.columns = (
                    # aquamarine3
                    progress.TextColumn(
                        "[bright_cyan]Total task" + ("s" if task.total > 1 else ""),
                        justify="right",
                    ),
                    progress.BarColumn(bar_width=None),
                    "[progress.percentage][steel_blue1]{task.percentage:>3.1f}%",
                    "•",
                    progress.TextColumn(
                        "[bright_cyan]{task.completed} / {task.total}",
                        justify="right",
                    ),
                )
            if task.fields.get("progress_type") == "download":
                self.columns = (
                    progress.TextColumn("[blue]{task.description}", justify="right"),
                    progress.BarColumn(bar_width=None),
                    "[progress.percentage][steel_blue3]{task.percentage:>3.1f}%",
                    "•",
                    progress.DownloadColumn(),
                    "•",
                    progress.TransferSpeedColumn(),
                    "•",
                    progress.TimeRemainingColumn(),
                )
            yield self.make_tasks_table([task])


def import_script(script: Script, target: str) -> Callable[..., dict]:
    name = f"{script.name}"
    spec = importlib.util.spec_from_file_location(name, script.script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    action = eval(f"module.{target}")
    return action


def symlink_latest(target: Path, name: str = "latest"):
    path_latest = target.parent / name
    if path_latest.exists():
        path_latest.rmdir()
    path_latest.symlink_to(target, target_is_directory=True)


def junction_latest(target: Path, name: str = "latest"):
    path_latest = target.parent / name
    if path_latest.exists():
        path_latest.rmdir()
    try:
        subprocess.run(["mklink", "/J", path_latest, target], shell=True, capture_output=True, check=True)
    except Exception as e:
        log.exception(e)
        exit(1)


def grant(files: list[Path], user: int = None, group: int = None, mode: int = None):
    if user == -1:
        user = os.getuid()
    if group == -1:
        group = os.getgid()

    for file in files:
        if (user is not None) and (group is not None):
            file.resolve().chown(user, group)
        if mode is not None:
            file.resolve().chmod(mode)


def extract(archive_path: Path, target_dir: Path = None, remove_archive: bool = True):
    # extract
    target_dir = target_dir or archive_path.parent
    shutil.unpack_archive(archive_path, target_dir)
    # remove archive
    if remove_archive:
        archive_path.unlink()
