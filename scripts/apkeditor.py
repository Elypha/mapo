import platform
import re
import shutil
import sys
from pathlib import Path

import httpx
import orjson
from rich import progress

from lib.helper import client, grant, single_install_move, single_uninstall, single_update, update_link
from lib.log import LogLevel, console, log, log_error, log_list, log_title


def update(_p_stats: dict, task_id: int, script: Path, config: dict, cache: dict):
    github_repo = "REAndroid/APKEditor"
    args = {
        "url": f"https://api.github.com/repos/{github_repo}/releases/latest",
        "regex_asset": re.compile(r"^APKEditor-(\d|\.)+\.jar$"),
        "regex_version": re.compile(r"(?P<version>(\d|\.)+)"),
    }
    single_update(_p_stats, task_id, script, config, cache, args)


def install(_p_stats: dict, task_id: int, script: Path, config: dict, cache: dict):
    args = {
        "save_name": f"{script.stem}.jar",
    }
    single_install_move(_p_stats, task_id, script, config, cache, args)


def uninstall(_p_stats: dict, task_id: int, script: Path, config: dict, cache: dict):
    single_uninstall(_p_stats, task_id, script, config, cache)


def upgrade(_p_stats: dict, task_id: int, script: Path, config: dict, cache: dict):
    install(_p_stats, task_id, script, config, cache)
