<h1 align="center">DownloadMate</h1>

<p align="center">
  <img src="assets/Icon_Rounded.png" alt="DownloadMate" width="128">
</p>

<p align="center">Automatically organize your downloads folder into subfolders by file extension.</p>

## Install

Open PowerShell and run:

```powershell
iwr -useb https://raw.githubusercontent.com/Ryn-1/DownloadMate/main/install.ps1 | iex
```

This downloads the latest release, adds it to your PATH, and creates a Start Menu shortcut.

## Usage

Run **DownloadMate** from the Start Menu or terminal. The app sits in your system tray and sorts new files into folders by extension. Configure folders and behavior through the GUI or by editing `%LOCALAPPDATA%\DownloadMate\config.json`.

### Run from source

```powershell
python sorter.py    # one-shot sort
python app.py       # system-tray GUI
```

## Configuration

| Key | Description |
| --- | --- |
| `downloads_path` | Folder to organize |
| `skip_extensions` | Extensions to ignore (in-progress downloads, temp files) |
| `folders` | Map of folder names to file extensions. Use `"*"` in one folder as a catch-all for unlisted types |

Files without a matching extension are skipped unless you define an `Unsorted` folder with `"*"`.

## Requirements

- **Binary install** — No dependencies.
- **Running from source** — Python 3 only. No third-party packages.
