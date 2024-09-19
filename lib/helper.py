import importlib.util
from pathlib import Path
from rich import progress

import orjson

from lib.log import console, log


def load_script(script: Path):
    name = f"{script.stem}"
    spec = importlib.util.spec_from_file_location(name, str(script))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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
