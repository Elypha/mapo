import platform
import re
import shutil
import sys
from pathlib import Path

import httpx
import orjson
from rich import progress

from lib.config import MapoConfig, Script
from lib.helper import client, download_helper, grant, junction_latest, remove_helper, symlink_latest, update_helper_github
from lib.log import LogLevel, console, log, log_error, print_list, print_heading


def update(ipc_progress: dict, config: MapoConfig, task: dict) -> dict:
    args = {
        "url": "https://api.github.com/repos/ReVanced/revanced-patches/releases/latest",
        "regex_asset": re.compile(r"^patches-.+\.rvp$"),
        "regex_version": re.compile(r"(?P<version>[\d.]+)"),
    }
    v0, v1 = update_helper_github(ipc_progress, config, task, args)
    return {"name": task["name"], "v0": v0, "v1": v1}


def upgrade(ipc_progress: dict, config: MapoConfig, task: dict) -> dict:
    # download
    dl_file_path = download_helper(ipc_progress, config, task)
    # install
    file_path = dl_file_path.rename(dl_file_path.with_stem("patches"))
    junction_latest(file_path.parent)
    ipc_progress[task["task_id"]] = (ipc_progress[task["task_id"]][1], ipc_progress[task["task_id"]][1])
    return {"name": task["name"], "v1": dl_file_path.parent.name}


# def uninstall(ipc_progress: dict, config: MapoConfig, task: dict) -> dict:
#     single_uninstall(_p_stats, task_id, script, config, cache)
