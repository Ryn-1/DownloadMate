<h1 align="center">DownloadMate</h1>

<p align="center">
  <img src="assets/Icon_Rounded.png" alt="DownloadMate" width="128">
</p>

<p align="center">Automatically organize your downloads folder into subfolders by file extension.</p>

## Install

Open PowerShell and run:

```powershell
iwr -useb https://raw.githubusercontent.com/rynfrfr/DownloadMate/master/install.ps1 | iex
```

This downloads the latest release, adds it to your PATH, and creates a Start Menu shortcut.

## Update

Re-run the same install command to update to the latest version

## Usage

Run **DownloadMate** from the Start Menu or terminal. It sits in your system tray and automatically sorts new files in your Downloads folder into subfolders by file extension (Images, Videos, Documents, etc.). Configure folders and behavior through the GUI.

## Configuration

| Key | Description |
| --- | --- |
| `downloads_path` | Folder to organize |
| `skip_extensions` | Extensions to ignore (in-progress downloads, temp files) |
| `poll_interval_sec` | How often (seconds) the app scans the Downloads folder |
| `stability_checks` | How many scans a file must stay unchanged before being moved |
| `folders` | Map of folder names to file extensions. Use `"*"` in one folder as a catch-all for unlisted types |

Files without a matching extension are skipped unless you define an `Unsorted` folder with `"*"`.
