import json
import shutil
from pathlib import Path

CATCH_ALL = "*"

SCRIPT_DIR = Path(__file__).parent


def should_skip(entry, skip_extensions):
    name_lower = entry.name.lower()
    if name_lower == "desktop.ini" or name_lower.startswith("~$"):
        return True
    return any(name_lower.endswith(ext) for ext in skip_extensions)


CONFIG_FILE = "config.json"
DEFAULT_CONFIG_FILE = "default_config.json"


def _init_config():
    config_path = SCRIPT_DIR / CONFIG_FILE
    if config_path.exists():
        return
    default_path = SCRIPT_DIR / DEFAULT_CONFIG_FILE
    if default_path.exists():
        shutil.copy(str(default_path), str(config_path))
    with open(config_path) as f:
        config = json.load(f)
    config["downloads_path"] = str(Path.home() / "Downloads")
    with open(config_path, "w") as f:
        json.dump(config, f, indent=4)


def configure(config_path=None):
    _init_config()
    if config_path is None:
        config_path = SCRIPT_DIR / CONFIG_FILE
    with open(Path(config_path)) as f:
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

    return downloads_path, skip_extensions, extension_to_folder, unsorted_folder


def get_target_folder(entry, extension_to_folder, unsorted_folder, skip_extensions):
    if should_skip(entry, skip_extensions):
        return None
    folder_name = extension_to_folder.get(entry.suffix.lower())
    if not folder_name and unsorted_folder:
        folder_name = unsorted_folder
    return folder_name


def move_file(entry, folder_name, downloads_path):
    folder_path = downloads_path / folder_name
    folder_path.mkdir(parents=True, exist_ok=True)
    dest = folder_path / entry.name
    try:
        shutil.move(str(entry), str(dest))
        return True
    except Exception as e:
        print(f"Failed to move {entry.name}: {e}")
        return False


def organize(config_path=None):
    downloads_path, skip_extensions, extension_to_folder, unsorted_folder = configure(config_path)
    for entry in downloads_path.iterdir():
        if not entry.is_file():
            continue
        folder_name = get_target_folder(entry, extension_to_folder, unsorted_folder, skip_extensions)
        if folder_name:
            move_file(entry, folder_name, downloads_path)
        elif not should_skip(entry, skip_extensions):
            print(f"{entry.name} has no matching folder in config")

