import platform
import re
import shutil
import sys
from pathlib import Path

import httpx
import orjson
from rich import progress

from lib.helper import client, grant, download_helper, single_uninstall, symlink_latest, update_helper_github, extract
from lib.log import LogLevel, console, log, log_error, print_list, print_title
from lib.config import MapoConfig, Script


def update(ipc_dict: dict, config: MapoConfig, task: dict) -> dict:
    args = {
        "url": "https://api.github.com/repos/taurusxin/ncmdump/releases/latest",
        # ncmdump-1.5.0-windows-amd64-msvc.zip
        "regex_asset": re.compile(r"^ncmdump-[\d.]+-windows-amd64-msvc\.zip$"),
        # 1.5.0
        "regex_version": re.compile(r"(?P<version>[\d.]+)"),
    }
    v0, v1 = update_helper_github(ipc_dict, config, task, args)
    return {"name": task["name"], "v0": v0, "v1": v1}


def upgrade(ipc_dict: dict, config: MapoConfig, task: dict) -> dict:
    # download
    dl_file_path = download_helper(ipc_dict, config, task)
    VERSION_DIR = dl_file_path.parent
    # install
    extract(dl_file_path)
    file_path = VERSION_DIR.glob("ncmdump*", case_sensitive=False)
    symlink_latest(VERSION_DIR)
    ipc_dict[task["task_id"]] = {"completed_size": ipc_dict[task["task_id"]]["total_size"], "total_size": ipc_dict[task["task_id"]]["total_size"]}
    return {"name": task["name"], "v1": VERSION_DIR.name}


# def uninstall(ipc_dict: dict, config: dict, task: dict) -> dict:
#     single_uninstall(_p_stats, task_id, script, config, cache)
