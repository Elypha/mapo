import re
import shutil
import sys
from pathlib import Path

import httpx
import orjson
from rich import progress

client = httpx.Client()


def update_link(target: Path):
    path_latest = target.parent / "latest"
    if path_latest.exists():
        path_latest.unlink()
    path_latest.symlink_to(target, target_is_directory=True)


def update(_p_stats: dict, task_id: int, script: Path, config: dict, cache: dict):
    # fetch remote
    _p_stats[task_id] = (0, 2)
    url = "https://api.github.com/repos/revanced/revanced-cli/releases/latest"
    response = client.get(url, follow_redirects=True)
    _p_stats[task_id] = (1, 2)
    response.raise_for_status()
    data = response.json()
    # data = data[0]

    # remote_version
    remote_version = data["tag_name"].lower().replace("v", "")
    cache["remote_version"] = remote_version

    # opt: download_url
    download_url = None
    pattern = re.compile(r"^revanced-cli-.+-all\.jar$")
    for asset in data["assets"]:
        if pattern.match(asset["name"]):
            download_url = asset["browser_download_url"]
            break
    if download_url is None:
        print("download_url not found")
        sys.exit(1)
    cache["download_url"] = download_url

    cache.save()
    _p_stats[task_id] = (2, 2)


def install(_p_stats: dict, task_id: int, script: Path, config: dict, cache: dict):
    _p_stats[task_id] = (0, 1)
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
            total = int(response.headers["Content-Length"]) + 1
            for chunk in response.iter_bytes():
                f.write(chunk)
                _p_stats[task_id] = (response.num_bytes_downloaded, total)

    # install
    path_tempFile.rename(path_remote / f"{path_app.name}.jar")
    update_link(path_remote)
    _p_stats[task_id] = (total + 1, total + 1)


def uninstall(_p_stats: dict, task_id: int, script: Path, config: dict, cache: dict):
    # args
    path_app = Path(config["path"]["data"]) / script.stem

    shutil.rmtree(path_app)


def upgrade(_p_stats: dict, task_id: int, script: Path, config: dict, cache: dict):
    install(_p_stats, task_id, script, config, cache)


if __name__ == "__main__":
    mapping = {
        "update": update,
        "install": install,
        "uninstall": uninstall,
        "upgrade": upgrade,
    }
    mapping.get(sys.argv[1], lambda: print("Invalid command"))(sys.argv[2:])
