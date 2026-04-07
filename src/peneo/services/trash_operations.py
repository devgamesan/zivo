"""Service for emptying trash on different platforms."""

import platform
import shutil
from dataclasses import dataclass
from pathlib import Path


class TrashService:
    """Boundary for trash operations."""

    def get_trash_path(self) -> str | None:
        """Return the trash directory path or None if not found."""

    def empty_trash(self) -> tuple[int, str]:
        """Empty trash and return (removed_count, error_message)."""


@dataclass(frozen=True)
class LinuxTrashService:
    """Trash operations for Linux (freedesktop.org standard)."""

    def get_trash_path(self) -> str | None:
        home = Path.home()
        trash_path = home / ".local/share/Trash"
        return str(trash_path) if trash_path.exists() else None

    def empty_trash(self) -> tuple[int, str]:
        trash_path = self.get_trash_path()
        if not trash_path:
            return 0, "Trash directory not found"

        files_path = Path(trash_path) / "files"
        if not files_path.exists():
            return 0, "No items in trash"

        removed_count = 0
        failures = []

        try:
            for item in files_path.iterdir():
                try:
                    if item.is_dir() and not item.is_symlink():
                        shutil.rmtree(item)
                    else:
                        item.unlink()
                    removed_count += 1
                except OSError as e:
                    failures.append(f"{item.name}: {str(e)}")

            # Also clean up metadata directory
            info_path = Path(trash_path) / "info"
            if info_path.exists():
                for metadata_file in info_path.iterdir():
                    try:
                        metadata_file.unlink()
                    except OSError:
                        pass  # Best effort cleanup

            if failures:
                error_msg = f"Removed {removed_count} items with {len(failures)} failures"
                return removed_count, error_msg

            return removed_count, ""

        except Exception as e:
            return 0, f"Failed to empty trash: {str(e)}"


@dataclass(frozen=True)
class MacOsTrashService:
    """Trash operations for macOS."""

    def get_trash_path(self) -> str | None:
        home = Path.home()
        trash_path = home / ".Trash"
        return str(trash_path) if trash_path.exists() else None

    def empty_trash(self) -> tuple[int, str]:
        trash_path = self.get_trash_path()
        if not trash_path:
            return 0, "Trash directory not found"

        trash_dir = Path(trash_path)
        if not trash_dir.exists():
            return 0, "No items in trash"

        removed_count = 0
        failures = []

        try:
            for item in trash_dir.iterdir():
                try:
                    if item.is_dir() and not item.is_symlink():
                        shutil.rmtree(item)
                    else:
                        item.unlink()
                    removed_count += 1
                except OSError as e:
                    failures.append(f"{item.name}: {str(e)}")

            if failures:
                error_msg = f"Removed {removed_count} items with {len(failures)} failures"
                return removed_count, error_msg

            return removed_count, ""

        except Exception as e:
            return 0, f"Failed to empty trash: {str(e)}"


@dataclass(frozen=True)
class UnsupportedPlatformTrashService:
    """Placeholder for unsupported platforms (Windows)."""

    def get_trash_path(self) -> str | None:
        return None

    def empty_trash(self) -> tuple[int, str]:
        return 0, "Empty trash is not supported on this platform"


def resolve_trash_service(
) -> "LinuxTrashService | MacOsTrashService | UnsupportedPlatformTrashService":
    """Return appropriate trash service based on platform."""
    system = platform.system()
    if system == "Linux":
        return LinuxTrashService()
    elif system == "Darwin":
        return MacOsTrashService()
    else:
        return UnsupportedPlatformTrashService()
