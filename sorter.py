import json
import shutil
from pathlib import Path

CATCH_ALL = "*"

SCRIPT_DIR = Path(__file__).parent

CONFIG_FILE = "config.json"
DEFAULT_CONFIG_FILE = "default_config.json"

_DEFAULT_CONFIG = {
    "downloads_path": "",
    "poll_interval_sec": 3,
    "stability_checks": 2,
    "skip_extensions": [".part", ".crdownload", ".tmp", ".temp", ".download", ".partial"],
    "folders": {
        "Images": [".png", ".jpg", ".jpeg", ".gif"],
        "Videos": [".mp4", ".mov", ".avi"],
        "Audio": [".mp3", ".wav"],
        "Documents": [".pdf", ".docx", ".txt"],
        "Unsorted": ["*"],
    },
}


def should_skip(entry, skip_extensions):
    name_lower = entry.name.lower()
    if name_lower == "desktop.ini" or name_lower.startswith("~$"):
        return True
    return any(name_lower.endswith(ext) for ext in skip_extensions)


def init_config(config_path=None):
    config_path = Path(config_path or SCRIPT_DIR / CONFIG_FILE)
    if config_path.exists():
        return
    config_path.parent.mkdir(parents=True, exist_ok=True)
    default_path = SCRIPT_DIR / DEFAULT_CONFIG_FILE
    if default_path.exists():
        shutil.copy(str(default_path), str(config_path))
    else:
        with open(config_path, "w") as f:
            json.dump(_DEFAULT_CONFIG, f, indent=4)
    with open(config_path) as f:
        config = json.load(f)
    config["downloads_path"] = str(Path.home() / "Downloads")
    with open(config_path, "w") as f:
        json.dump(config, f, indent=4)
    downloads_path = Path(config["downloads_path"])
    for folder_name in config.get("folders", {}):
        (downloads_path / folder_name).mkdir(parents=True, exist_ok=True)


_config_cache = {}


def configure(config_path=None):
    if config_path is None:
        config_path = SCRIPT_DIR / CONFIG_FILE
    config_path = Path(config_path)
    init_config(config_path)

    cache_path = config_path.resolve()

    try:
        current_mtime = config_path.stat().st_mtime_ns
    except OSError:
        current_mtime = None

    if (
        current_mtime is not None
        and cache_path == _config_cache.get("path")
        and current_mtime == _config_cache.get("mtime")
    ):
        return (
            _config_cache["downloads_path"],
            _config_cache["skip_extensions"],
            _config_cache["extension_to_folder"],
            _config_cache["unsorted_folder"],
        )

    with open(config_path) as f:
        config = json.load(f)

    downloads_path = Path(config["downloads_path"])
    skip_extensions = {
        ext.lower()
        for ext in config.get(
            "skip_extensions",
            [".part", ".crdownload", ".tmp", ".temp", ".download", ".partial"],
        )
    }

    extension_to_folder = {}
    unsorted_folder = None
    for folder_name, extensions in config["folders"].items():
        if CATCH_ALL in extensions:
            unsorted_folder = folder_name
        else:
            for ext in extensions:
                extension_to_folder[ext.lower()] = folder_name

    _config_cache.update(
        path=cache_path,
        mtime=current_mtime,
        downloads_path=downloads_path,
        skip_extensions=skip_extensions,
        extension_to_folder=extension_to_folder,
        unsorted_folder=unsorted_folder,
    )

    return downloads_path, skip_extensions, extension_to_folder, unsorted_folder


def get_target_folder(entry, extension_to_folder, unsorted_folder):
    folder_name = extension_to_folder.get(entry.suffix.lower())
    if not folder_name and unsorted_folder:
        folder_name = unsorted_folder
    return folder_name


def _unique_path(path):
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    parent = path.parent
    counter = 1
    while True:
        new_path = parent / f"{stem}_{counter}{suffix}"
        if not new_path.exists():
            return new_path
        counter += 1


def move_file(entry, folder_name, downloads_path):
    folder_path = downloads_path / folder_name
    folder_path.mkdir(parents=True, exist_ok=True)
    dest = _unique_path(folder_path / entry.name)
    try:
        shutil.move(str(entry), str(dest))
        return True
    except OSError as e:
        print(f"Failed to move {entry.name}: {e}")
        return False


def organize(config_path=None):
    downloads_path, skip_extensions, extension_to_folder, unsorted_folder = configure(config_path)
    for entry in downloads_path.iterdir():
        if not entry.is_file():
            continue
        if should_skip(entry, skip_extensions):
            continue
        folder_name = get_target_folder(entry, extension_to_folder, unsorted_folder)
        if folder_name:
            move_file(entry, folder_name, downloads_path)
        else:
            print(f"{entry.name} has no matching folder in config")
