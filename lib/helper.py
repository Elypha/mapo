import importlib.util
import os
import platform
import re
import shutil
import sys
from pathlib import Path

import httpx
import orjson
from rich import progress

from lib.log import console, log

client = httpx.Client(
    headers={
        "User-Agent": f"Mapo/0.1 (Python {platform.python_version()}, httpx/{httpx.__version__}; {platform.system()} {platform.release()}) +github.com/Elypha/Mapo",
    }
)


class Cache(dict):
    def __init__(self, cache_file: Path):
        self.file = cache_file
        if not self.file.parent.exists():
            self.file.parent.mkdir(parents=True, exist_ok=True)
        if not self.file.exists():
            self.data = {}
            self.save()
        self.load()

    def load(self):
        with open(self.file, "rb") as f:
            self.data = orjson.loads(f.read())

    def save(self):
        with open(self.file, "wb") as f:
            f.write(orjson.dumps(self.data, option=orjson.OPT_INDENT_2))

    # setter
    def __setitem__(self, key, value):
        self.data[key] = value

    # getter
    def __getitem__(self, key):
        if key in self.data:
            return self.data[key]
        else:
            return None

    # deleter
    def __delitem__(self, key):
        del self.data[key]

    # iterator
    def __iter__(self):
        return iter(self.data)

    # length
    def __len__(self):
        return len(self.data)


class SummaryProgress(progress.Progress):
    def get_renderables(self):
        for task in self.tasks:
            if task.fields.get("progress_type") == "summary":
                self.columns = (
                    progress.TextColumn(
                        "[aquamarine3]Downloading file" + ("s" if task.total > 1 else ""),
                        justify="right",
                    ),
                    progress.BarColumn(bar_width=None),
                    "[progress.percentage][steel_blue1]{task.percentage:>3.1f}%",
                    "•",
                    progress.TextColumn(
                        "[aquamarine3]{task.completed} of {task.total} completed",
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


def load_script(script: Path):
    name = f"{script.stem}"
    spec = importlib.util.spec_from_file_location(name, str(script))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def update_link(target: Path, name: str = "latest"):
    path_latest = target.parent / name
    if path_latest.exists():
        path_latest.unlink()
    path_latest.symlink_to(target, target_is_directory=True)


def single_update(_p_stats: dict, task_id: int, script: Path, config: dict, cache: dict, args: dict):
    # args
    url: str = args["url"]
    regex_asset: re.Pattern = args["regex_asset"]
    regex_version: re.Pattern = args["regex_version"]

    # fetch remote
    _p_stats[task_id] = (0, 2)
    response = client.get(url, follow_redirects=True)
    response.raise_for_status()

    # process data
    _p_stats[task_id] = (1, 2)
    data = response.json()

    # [+] github
    if "api.github.com" in url:
        if isinstance(data, list):
            data = data[0]
        # remote version
        remote_version = regex_version.search(data["tag_name"]).group("version")
        if remote_version is None:
            log.error(f"no matching remote_version for {script.stem}")
            sys.exit(1)
        cache["remote_version"] = remote_version
        # download_url
        download_url = None
        for asset in data["assets"]:
            if regex_asset.match(asset["name"]):
                download_url = asset["browser_download_url"]
                break
        if download_url is None:
            log.error(f"no matching download_url for {script.stem}@{remote_version}")
            sys.exit(1)
        cache["download_url"] = download_url

    # finish
    cache.save()
    _p_stats[task_id] = (2, 2)


def single_install_move(_p_stats: dict, task_id: int, script: Path, config: dict, cache: dict, args: dict):
    # args
    save_name: str = args["save_name"]

    # prepare remote dir
    _p_stats[task_id] = (0, 1)
    path_app = Path(config["path"]["data"]) / script.stem
    path_remote = path_app / cache["remote_version"]
    path_remote.mkdir(parents=True)

    # download
    path_tempFile = path_app / f"temp_{cache['remote_version']}"
    path_tempFile.unlink(missing_ok=True)
    with open(path_tempFile, "wb") as f:
        with client.stream("GET", cache["download_url"], follow_redirects=True) as response:
            if "Content-Length" in response.headers:
                total = int(response.headers["Content-Length"]) + 1
                for chunk in response.iter_bytes():
                    f.write(chunk)
                    _p_stats[task_id] = (response.num_bytes_downloaded, total)
            else:
                for chunk in response.iter_bytes():
                    f.write(chunk)
                    total = response.num_bytes_downloaded
                    _p_stats[task_id] = (total, total + 1)

    # install
    path_tempFile.rename(path_remote / save_name)
    update_link(path_remote)
    _p_stats[task_id] = (total + 1, total + 1)


def single_uninstall(_p_stats: dict, task_id: int, script: Path, config: dict, cache: dict):
    # args
    path_app = Path(config["path"]["data"]) / script.stem

    # uninstall
    shutil.rmtree(path_app)


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
