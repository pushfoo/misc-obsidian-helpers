"""Exceptions and helpers for file system operations."""
from enum import StrEnum, auto
from pathlib import Path


class NotAFileError(OSError):
    ...


class DirectoryDoesNotExistError(OSError):
    ...


class DirectoryExistsError(OSError):
    ...


class PathState(StrEnum):
    DOES_NOT_EXIST = auto()
    DIRECTORY = auto()
    FILE = auto()
    """File-like."""
    UNKNOWN = auto()


def expand_resolve_path(path: str | Path) -> Path:
    """Expand any ~, then resolve symlinks and make it absolute.

    Remember, I'd rewrite this in something other than Python if
    maximum speed was crucial. Convenience is key.

    Arguments:
        path: a system path as a string or pathlib Path.

    Returns:
        The absolute version of the path with any (~) expanded and symlinks resolved.
    """
    return Path(path).expanduser().resolve()


def get_path_type(path: str | Path, skip_resolve: bool = False) -> PathState:
    """Take the path"""
    as_pathlib: Path
    if skip_resolve:
        as_pathlib = path # type: ignore
    else:
        as_pathlib = expand_resolve_path(path)
    if not as_pathlib.exists():
        return PathState.DOES_NOT_EXIST
    elif as_pathlib.is_dir():
        return PathState.DIRECTORY
    elif as_pathlib.is_file():
        return PathState.FILE
    else:
        return PathState.UNKNOWN


def parse_existing_dir(
    maybe_matches: str | Path,
) -> Path:
    as_pathlib = expand_resolve_path(maybe_matches)
    current_state = get_path_type(as_pathlib)
    if current_state != PathState.DIRECTORY:
        match current_state:
            case PathState.DOES_NOT_EXIST:
                raise DirectoryDoesNotExistError(f"{str(as_pathlib)!r} does not exist")
            case _:
                raise NotADirectoryError(f"f{str(as_pathlib)!r} is a {current_state.value}")

    return as_pathlib


__all__ = [
    "NotAFileError",
    "DirectoryExistsError",
    "DirectoryDoesNotExistError",
    "PathState",
    "expand_resolve_path",
    "get_path_type"
]