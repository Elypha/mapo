import argparse
import multiprocessing
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from rich import progress

from lib.batch_task import batch_task_runner, task_runner
from lib.config import MapoConfig, Script
from lib.helper import SummaryProgress
from lib.log import console, log, print_heading, print_list


class Mapo:
    def __init__(self, args: argparse.Namespace):
        self._args = args
        self._config_path = self._get_config_path()
        self.config = MapoConfig(self._config_path)
        self._scan_scripts()

    def _get_config_path(self) -> Path:
        config_paths: list[Path] = []
        config_paths.append(Path(self._args.config))  # add user input path

        # add default paths by os
        # WIP

        # check if any of the paths exist
        for x in config_paths:
            if x.is_file() and x.exists():
                return x
        log.error(f"Cannot find any config file at the following paths: {config_paths}")
        exit(1)

    def _scan_scripts(self) -> list[Script]:
        self.scripts = [Script(x, self.config) for x in self.config.path_scripts.glob("*.py")]

    def enable_script(self, name: str):
        if name not in self.config.valid_script_names:
            log.error(f"Script '{name}' not found")
            exit(1)
        self.config.enabled_scripts.add(name)
        self.config.save()
        self.config.load()
        log.success(f"'{name}' enabled.")

    def disable_script(self, name: str):
        if name not in self.config.valid_script_names:
            log.error(f"Script '{name}' not found")
            exit(1)
        self.config.enabled_scripts.discard(name)
        self.config.save()
        self.config.load()
        log.success(f"'{name}' disabled.")

    def list_scripts(self, include_disabled: bool = False):
        target_scripts = [x for x in self.scripts if include_disabled or x.enabled]
        for x in target_scripts:
            if x.enabled:
                console.print(f"+ {x.name}", style="bright_green")
            else:
                console.print(f"- {x.name}", style="light_coral")

    def run_update(self, target_scripts: list[Script]):
        try:
            console.print(f"Check updates for {len(target_scripts)} scripts ...", style="white")

            # prepare tasks
            tasks = []
            for x in target_scripts:
                tasks.append(
                    {
                        "name": x.name,
                        "task_id": None,
                        "data": {
                            "script": x,
                            "target": "update",
                        },
                    }
                )

            with SummaryProgress(
                "[progress.description]{task.description}",
                progress.BarColumn(bar_width=None),
                "[progress.percentage]{task.percentage:>3.0f}%",
                progress.TimeRemainingColumn(),
                progress.TimeElapsedColumn(),
                refresh_per_second=5,
            ) as p_bar:
                with ProcessPoolExecutor(max_workers=self.config.n_worker_update) as executor:
                    with multiprocessing.Manager() as manager:
                        ipc_progress = manager.dict()
                        futures = batch_task_runner(p_bar, executor, ipc_progress, self.config, tasks)

            # summary
            count = 0
            for future in futures:
                result = future.result()
                if result["v0"] != result["v1"]:
                    console.print(f"> {result['name']}: {result['v0']} -> {result['v1']}", style="bright_cyan")
                    count += 1
            if count == 0:
                console.print("All scripts are up to date.", style="white")
            else:
                console.print(f"{count} scripts updated.", style="white")

            # list has_update
            count = 0
            self._scan_scripts()
            for x in [x for x in self.scripts if x.has_update]:
                console.print(f"> {x.name}: {x.local_version_latest} -> {x.cache.get('remote_version', None)}", style="bright_cyan")
                count += 1
            if count == 0:
                console.print("All packages are up to date.", style="white")
            else:
                console.print(f"{count} packages have updates.", style="white")

        except Exception as e:
            log.exception(e)
            exit(1)

    def run_upgrade(self, target_scripts: list[Script]):
        try:
            console.print(f"Upgrade {len(target_scripts)} scripts ...", style="white")

            # prepare tasks
            tasks = []
            for x in target_scripts:
                tasks.append(
                    {
                        "name": x.name,
                        "task_id": None,
                        "data": {
                            "script": x,
                            "target": "upgrade",
                        },
                    }
                )

            with SummaryProgress(
                "[progress.description]{task.description}",
                progress.BarColumn(bar_width=None),
                "[progress.percentage]{task.percentage:>3.0f}%",
                progress.TimeRemainingColumn(),
                progress.TimeElapsedColumn(),
                refresh_per_second=5,
            ) as p_bar:
                with ProcessPoolExecutor(max_workers=self.config.n_worker_upgrade) as executor:
                    with multiprocessing.Manager() as manager:
                        ipc_progress = manager.dict()
                        futures = batch_task_runner(p_bar, executor, ipc_progress, self.config, tasks)

            # summary
            count = 0
            for future in futures:
                result = future.result()
                console.print(f"> {result['name']}: {x.local_version_latest} -> {result['v1']}", style="bright_cyan")
                count += 1
            if count > 0:
                console.print(f"{count} packages updated", style="white")

        except Exception as e:
            log.exception(e)
            exit(1)

    def run(self):
        entry: str = self._args.command
        args: list = self._args.args

        if entry == "update":
            if "--all" in args or "-a" in args:
                self.run_update(self.scripts)
            else:
                self.run_update([x for x in self.scripts if x.enabled])
        elif entry == "upgrade":
            if len(args) == 0:
                self.run_upgrade([x for x in self.scripts if x.enabled and x.has_update])
            else:
                self.run_upgrade([x for x in self.scripts if (x.name in args) and x.has_update])
        elif entry == "enable":
            for x in args:
                self.enable_script(x)
        elif entry == "disable":
            for x in args:
                self.disable_script(x)
        elif entry == "list":
            if "--all" in args or "-a" in args:
                self.list_scripts(include_disabled=True)
            else:
                self.list_scripts()
        elif entry == "show":
            if "--all" in args or "-a" in args:
                self.list_scripts(include_disabled=True)
            else:
                self.list_scripts()
        else:
            log.error(f"Command {entry} not found")
            sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", type=str, default=None, help="config file path")
    parser.add_argument("command", type=str, help="[update, upgrade, enable, disable, list, show]")
    parser.add_argument("args", nargs=argparse.REMAINDER, help="[--all, -a] or [script names]")
    args = parser.parse_args()

    mapo = Mapo(args)
    mapo.run()
