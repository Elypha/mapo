import datetime
import logging
from enum import IntEnum
from typing import Optional, Type

from rich.console import Console
from rich.logging import RichHandler
from rich.style import Style
from rich.theme import Theme


class LogLevel(IntEnum):
    NOTSET = 0
    TRACE = 5  # custom
    DEBUG = 10
    SUCCESS = 15  # custom
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50


class RichLogger(logging.Logger):
    def trace(self, msg, *args, **kwargs) -> None:
        pass

    def success(self, msg, *args, **kwargs) -> None:
        pass


def get_logger(name: str, level: Type[LogLevel] = LogLevel.TRACE) -> tuple[RichLogger, Console]:
    from rich.default_styles import DEFAULT_STYLES

    # methods
    def _log_time_fmt(dt: datetime.datetime) -> str:
        # benchmark: x1000000
        # f"{dt:%H:%M:%S}.{str(dt.microsecond)[:3]}"          2.792601199999808
        # f"{dt:%H:%M:%S}.{dt.microsecond // 1000:03}"        2.9164577000001373
        # f"{dt:%H:%M:%S.%f}"[:-3]                            3.3833028999997623
        return f"{dt:%H:%M:%S}.{str(dt.microsecond)[:3]}"

    # setup console
    DEFAULT_STYLES["logging.level.debug"] = Style(color="sky_blue2")
    DEFAULT_STYLES["logging.level.info"] = Style(color="cyan3")
    DEFAULT_STYLES["logging.level.warning"] = Style(color="gold3")
    DEFAULT_STYLES["logging.level.error"] = Style(color="light_coral", bold=True)
    DEFAULT_STYLES["logging.level.critical"] = Style(color="red", bold=True, reverse=True)

    DEFAULT_STYLES["logging.level.trace"] = Style(color="light_slate_grey")
    DEFAULT_STYLES["logging.level.success"] = Style(color="sea_green1")
    console = Console(
        log_time=True,
        # log_time_format="%H:%M:%S",
        log_time_format=_log_time_fmt,
        theme=Theme(DEFAULT_STYLES),
    )
    if console.width > 120:
        console.width = 120

    # get logger
    log = logging.getLogger(name)

    # handler
    rich_handler = RichHandler(
        # level=LogLevel.NOTSET,
        console=console,
        omit_repeated_times=False,
        rich_tracebacks=True,
        tracebacks_word_wrap=False,
        tracebacks_show_locals=True,
        tracebacks_suppress=[],
        locals_max_length=24,
        # log_time_format="%H:%M:%S",
        log_time_format=_log_time_fmt,
    )
    log.addHandler(rich_handler)

    # formatter
    rich_formatter = logging.Formatter(
        fmt="%(message)s",
    )
    rich_handler.setFormatter(rich_formatter)

    # custom level
    def _trace(self, msg, *args, **kwargs):
        if self.isEnabledFor(LogLevel.TRACE):
            self._log(LogLevel.TRACE, msg, args, **kwargs)

    def _success(self, msg, *args, **kwargs):
        if self.isEnabledFor(LogLevel.SUCCESS):
            self._log(LogLevel.SUCCESS, msg, args, **kwargs)

    logging.addLevelName(LogLevel.TRACE, "TRACE")
    logging.Logger.trace = _trace
    logging.addLevelName(LogLevel.SUCCESS, "SUCCESS")
    logging.Logger.success = _success

    # level
    log.setLevel(level)

    return log, console


log, console = get_logger("avalon", LogLevel.TRACE)


def log_title(title: str):
    console.print(f"\n> {title}", style="bright_cyan bold")


def log_list(items: list[str]):
    for item in items:
        console.print(f"+ {item}", style="bright_cyan")


def log_error(msg: str):
    console.print(f"Error: {msg}", style="light_coral")
    exit(1)
