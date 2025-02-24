import platform
import re
import shutil
import sys
from pathlib import Path

import httpx
import orjson
from rich import progress

from lib.helper import client, grant, download_helper, single_uninstall, symlink_latest, update_helper_github
from lib.log import LogLevel, console, log, log_error, print_list, print_title
from lib.config import MapoConfig, Script


def update(ipc_dict: dict, config: MapoConfig, task: dict) -> dict:
    args = {
        "url": "https://api.github.com/repos/REAndroid/APKEditor/releases/latest",
        "regex_asset": re.compile(r"^APKEditor-[\d.]+\.jar$"),
        "regex_version": re.compile(r"(?P<version>[\d.]+)"),
    }
    v0, v1 = update_helper_github(ipc_dict, config, task, args)
    return {"name": task["name"], "v0": v0, "v1": v1}


def upgrade(ipc_dict: dict, config: MapoConfig, task: dict) -> dict:
    # download
    dl_file_path = download_helper(ipc_dict, config, task)
    # install
    file_path = dl_file_path.rename(dl_file_path.with_stem("APKEditor"))
    symlink_latest(file_path.parent)
    ipc_dict[task["task_id"]] = {"completed_size": ipc_dict[task["task_id"]]["total_size"], "total_size": ipc_dict[task["task_id"]]["total_size"]}
    return {"name": task["name"], "v1": dl_file_path.parent.name}


# def uninstall(ipc_dict: dict, config: dict, task: dict) -> dict:
#     single_uninstall(_p_stats, task_id, script, config, cache)
