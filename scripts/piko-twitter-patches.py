import re
import shutil
import sys
from pathlib import Path

import httpx
import orjson
import rich.progress

client = httpx.Client()


def update_link(target: Path):
    path_latest = target.parent / "latest"
    if path_latest.exists():
        path_latest.unlink()
    path_latest.symlink_to(target, target_is_directory=True)


def update(script: Path, config: dict, cache: dict):
    # fetch remote
    url = "https://api.github.com/repos/crimera/piko/releases/latest"
    response = client.get(url, follow_redirects=True)
    response.raise_for_status()
    data = response.json()

    # remote_version
    remote_version = data["tag_name"].lower().replace("v", "")
    cache["remote_version"] = remote_version

    # opt: download_url
    download_url = None
    pattern = re.compile(r"^piko-twitter-patches-(\d|\.)+\.jar$")
    for asset in data["assets"]:
        if pattern.match(asset["name"]):
            download_url = asset["browser_download_url"]
            break
    if download_url is None:
        print("download_url not found")
        sys.exit(1)
    cache["download_url"] = download_url

    cache.save()


def install(script: Path, config: dict, cache: dict):
    # args
    path_app = Path(config["path"]["data"]) / script.stem

    # prepare remote dir
    path_remote = path_app / cache["remote_version"]
    path_remote.mkdir(parents=True)

    # download
    path_tempFile = path_app / f"temp_{cache['remote_version']}"
    path_tempFile.unlink(missing_ok=True)
    with open(path_tempFile, "wb") as f:
        with client.stream("GET", cache["download_url"], follow_redirects=True) as response:
            total = int(response.headers["Content-Length"])

            with rich.progress.Progress(
                "[progress.description]{task.description}",
                rich.progress.BarColumn(bar_width=None),
                "[progress.percentage]{task.percentage:>3.0f}%",
                rich.progress.DownloadColumn(),
                rich.progress.TransferSpeedColumn(),
            ) as progress:
                download_task = progress.add_task(path_app.name, total=total)
                for chunk in response.iter_bytes():
                    f.write(chunk)
                    progress.update(download_task, completed=response.num_bytes_downloaded)

    # install
    path_tempFile.rename(path_remote / f"{path_app.name}.jar")
    update_link(path_remote)


def uninstall(script: Path, config: dict, cache: dict):
    # args
    path_app = Path(config["path"]["data"]) / script.stem

    shutil.rmtree(path_app)


def upgrade(script: Path, config: dict, cache: dict):
    install(script, config)


if __name__ == "__main__":
    mapping = {
        "update": update,
        "install": install,
        "uninstall": uninstall,
        "upgrade": upgrade,
    }
    mapping.get(sys.argv[1], lambda: print("Invalid command"))(sys.argv[2:])
