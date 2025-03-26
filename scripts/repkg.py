import platform
import re
import shutil
import sys
from pathlib import Path

import httpx
import orjson
from rich import progress

from lib.config import MapoConfig, Script
from lib.helper import client, download_helper, extract, grant, link_latest, remove_helper, update_helper_github
from lib.log import LogLevel, console, log, log_error, print_list, print_heading

# https://github.com/notscuffed/repkg


def update(ipc_progress: dict, config: MapoConfig, task: dict) -> dict:
    GITHUB_REPO = "notscuffed/repkg"
    args = {
        "url": f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest",
        # v0.3.2-alpha
        "regex_version": re.compile(r"(?P<version>[\d.\-\w]+)"),
        # RePKG.zip
        "regex_asset": re.compile(r"^RePKG\.zip$"),
    }
    v0, v1 = update_helper_github(ipc_progress, config, task, args)
    return {"name": task["name"], "v0": v0, "v1": v1}


def upgrade(ipc_progress: dict, config: MapoConfig, task: dict) -> dict:
    # download
    dl_file_path = download_helper(ipc_progress, config, task)
    VERSION_DIR = dl_file_path.parent
    # install
    extract(dl_file_path)
    # finish
    link_latest(VERSION_DIR)
    ipc_progress[task["task_id"]] = (ipc_progress[task["task_id"]][1], ipc_progress[task["task_id"]][1])
    return {"name": task["name"], "v1": VERSION_DIR.name}


# def uninstall(ipc_progress: dict, config: MapoConfig, task: dict) -> dict:
#     single_uninstall(_p_stats, task_id, script, config, cache)
