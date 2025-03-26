import platform
import re
import shutil
import sys
from pathlib import Path

import httpx
import orjson
from rich import progress

from lib.config import MapoConfig, Script
from lib.helper import client, download_helper, grant, link_latest, remove_helper, update_helper_github
from lib.log import LogLevel, console, log, log_error, print_list, print_heading

# https://github.com/EFForg/apkeep


def update(ipc_progress: dict, config: MapoConfig, task: dict) -> dict:
    GITHUB_REPO = "EFForg/apkeep"
    asset_by_os = {
        "Linux": {
            "x86_64": r"^apkeep-x86_64-unknown-linux-gnu$",
        },
        "Windows": {
            "AMD64": r"^apkeep-x86_64-pc-windows-msvc.exe$",
        },
    }
    args = {
        "url": f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest",
        "regex_version": re.compile(r"(?P<version>[\d.]+)"),
        "regex_asset": re.compile(asset_by_os[platform.system()][platform.machine()]),
    }
    v0, v1 = update_helper_github(ipc_progress, config, task, args)
    return {"name": task["name"], "v0": v0, "v1": v1}


def upgrade(ipc_progress: dict, config: MapoConfig, task: dict) -> dict:
    # download
    dl_file_path = download_helper(ipc_progress, config, task)
    VERSION_DIR = dl_file_path.parent
    # install
    file_path = dl_file_path.rename(dl_file_path.with_stem("apkeep"))
    if platform.system() == "Linux":
        grant([file_path], mode=0o755)
    # finish
    link_latest(VERSION_DIR)
    ipc_progress[task["task_id"]] = (ipc_progress[task["task_id"]][1], ipc_progress[task["task_id"]][1])
    return {"name": task["name"], "v1": dl_file_path.parent.name}


# def uninstall(ipc_progress: dict, config: MapoConfig, task: dict) -> dict:
#     single_uninstall(_p_stats, task_id, script, config, cache)
