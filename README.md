<p align="center">
  <img src="assets/Icon_Rounded.png" alt="DownloadMate" width="128">
</p>

# DownloadMate

Automatically organize your downloads folder into subfolders by file extension.

## Setup

1. Install [Python 3](https://www.python.org/downloads/) if you don't have it.
2. Run the app — `config.json` is created automatically with your Downloads path.

## Usage

Run from this folder:

```powershell
cd "DownloadMate"
python sorter.py
```

Or launch `app.py` for the system-tray GUI:

```powershell
python app.py
```

## Configuration

| Key | Description |
| --- | --- |
| `downloads_path` | Folder to organize |
| `skip_extensions` | Extensions to ignore (in-progress downloads, temp files) |
| `folders` | Map of folder names to file extensions. Use `"*"` in one folder as a catch-all for unlisted types |

Files without a matching extension are skipped unless you define an `Unsorted` folder with `"*"`.

## Requirements

Python 3 only. No third-party packages.
