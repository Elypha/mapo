from pathlib import Path

import orjson
import tomlkit


class Script:
    def __init__(self, script_path: Path, config: "MapoConfig"):
        self.name = script_path.stem
        self.enabled = True if self.name in config.enabled_scripts else False

        self.script_path = script_path
        self.cache_path = config.mapo_dir / "cache" / self.script_path.relative_to(config.mapo_dir / "scripts").with_suffix(".json")
        self.load_cache()

        self.app_path = config.userdata_dir / self.script_path.stem
        self.app_path_latest = self.app_path / "latest"
        if not self.app_path.exists():
            self.local_versions = []
            self.local_version_latest = None
        else:
            self.local_versions = [x.name for x in self.app_path.iterdir() if x.is_dir(follow_symlinks=False) and x.name != "latest"]
            self.local_version_latest = self.app_path_latest.resolve().name

        if not self.enabled:
            self.has_update = False
        else:
            self.has_update = self.cache.get("remote_version", None) != self.local_version_latest

    def save_cache(self):
        self.cache_path.write_bytes(orjson.dumps(self.cache, option=orjson.OPT_INDENT_2))

    def load_cache(self):
        if self.cache_path.exists():
            self.cache: dict = orjson.loads(self.cache_path.read_bytes())
        else:
            self.cache = {}


class MapoConfig:
    def __init__(self, path: Path):
        self._config_path = path
        self.load()

    def validate(self):
        self.enabled_scripts = set()
        for x in self._config["script"]["enabled"]:
            if x in self.valid_script_names:
                self.enabled_scripts.add(x)

    def scan_valid_script_names(self):
        self.valid_script_names = [x.stem for x in self.scripts_dir.glob("*.py")]

    def load(self):
        with open(self._config_path, "r", encoding="utf8") as f:
            self._config = tomlkit.parse(f.read())

        self.mapo_dir = Path(self._config["path"]["mapo_dir"]).resolve()
        self.userdata_dir = Path(self._config["path"]["userdata_dir"]).resolve()
        self.scripts_dir = self.mapo_dir / "scripts"
        self.cache_dir = self.mapo_dir / "cache"
        self.worker_update = self._config["worker"]["update"]
        self.worker_upgrade = self._config["worker"]["upgrade"]
        self.scan_valid_script_names()
        self.validate()

    def save(self):
        with open(self._config_path, "w", encoding="utf8") as f:
            self._config["script"]["enabled"] = sorted(list(self.enabled_scripts))
            tomlkit.dump(self._config, f)
