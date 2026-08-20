from __future__ import annotations

import os
from pathlib import Path

NAVIGATION_DIRECTORIES = ("00_index", "05_inbox", "10_projects", "20_areas", "30_resources", "40_sources", "50_tools", "60_maps", "90_meta", "99_archive")


def discover_markdown(root: Path) -> tuple[list[Path], list[Path]]:
    files: list[Path] = []
    symlinks: list[Path] = []
    for directory in NAVIGATION_DIRECTORIES:
        location = root / directory
        if not location.exists():
            continue
        for path in location.rglob("*.md"):
            if path.is_symlink():
                symlinks.append(path)
            else:
                files.append(path)
    return sorted(files), sorted(symlinks)


def destination_is_empty_directory(destination: Path) -> bool:
    return destination.exists() and destination.is_dir() and not destination.is_symlink() and not any(destination.iterdir())


def atomic_publish(staging: Path, destination: Path) -> None:
    # os.replace is atomic on a single filesystem where available. The caller only allows a new path.
    if destination.exists():
        if not destination_is_empty_directory(destination):
            raise FileExistsError(f"Destination is non-empty or unsuitable: {destination}")
        destination.rmdir()
    os.replace(staging, destination)
