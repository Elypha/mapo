import argparse
import importlib.util
import os
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import tomlkit

from cmd_install import do_install
from cmd_update import do_update
from cmd_upgrade import do_upgrade
from lib.log import LogLevel, console, log, log_error, log_list, log_title

parser = argparse.ArgumentParser()
parser.add_argument("-c", "--config", type=str, default=None, help="config file path")
parser.add_argument("command", type=str, help="command to run")
parser.add_argument("args", nargs=argparse.REMAINDER, help="args for command")
args = parser.parse_args()

if (args.config is None) or (not Path(args.config).exists):
    log.error("Config file not found")
    sys.exit(1)
with open(args.config, "r", encoding="utf8") as f:
    config = tomlkit.parse(f.read())

HOME = Path(config["path"]["home"]).resolve()


def save_config(config: dict):
    with open(args.config, "w", encoding="utf8") as f:
        tomlkit.dump(config, f)


def _enable(config: dict, scripts: list[Path], args: list[str]):
    enabled = []
    if args == []:
        enabled = [x.stem for x in scripts]
    else:
        for script in args:
            path = HOME / "scripts" / f"{script}.py"
            if not path.exists():
                log.warning(f"Script {script} not found")
                continue
            enabled.append(script)
    enabled = [x for x in enabled if x not in config["script"]["enabled"]]
    if len(enabled) > 0:
        config["script"]["enabled"].extend(enabled)
        log_title("Enabled scripts")
        log_list(enabled)
        save_config(config)
    else:
        log.warning("Nothing to enable")
        sys.exit(0)


def _disable(config: dict, scripts: list[Path], args: list[str]):
    disabled = []
    if args == []:
        disabled = config["script"]["enabled"]
        config["script"]["enabled"] = []
    else:
        for script in args:
            if script not in config["script"]["enabled"]:
                continue
            config["script"]["enabled"].remove(script)
            disabled.append(script)
    if len(disabled) > 0:
        log_title("Disabled scripts")
        log_list(disabled)
        save_config(config)
    else:
        log.warning("Nothing to disable")
        sys.exit(0)


def _list(scripts: list[Path], config: dict, args: list[str]):
    log_title("Available scripts")
    for script in scripts:
        item = script.stem
        if item in config["script"]["enabled"]:
            console.print(f"+ {item}", style="bright_green")
        else:
            console.print(f"- {item}", style="light_coral")


def main(command: str, args: list[str]):
    scripts = [*(HOME / "scripts").glob("**/*.py")]
    enabled_scripts = [x for x in scripts if x.stem in config["script"]["enabled"]]

    if command == "update":
        do_update(enabled_scripts, config, args)
    elif command == "install":
        if len(args) == 0:
            filtered_scripts = enabled_scripts
        else:
            filtered_scripts = [x for x in enabled_scripts if x.stem in args]
        do_install(filtered_scripts, config, args)
    elif command == "upgrade":
        if len(args) == 0:
            filtered_scripts = enabled_scripts
        else:
            filtered_scripts = [x for x in enabled_scripts if x.stem in args]
        do_upgrade(filtered_scripts, config, args)
    elif command == "enable":
        _enable(config, scripts, args)
    elif command == "disable":
        _disable(config, scripts, args)
    elif command == "list":
        _list(scripts, config, args)
    else:
        log.error(f"Command {command} not found")
        sys.exit(1)


if __name__ == "__main__":
    main(args.command, args.args)
