"""Abstractions over on-disk Obsidian primitives.

This currently implements very rough versions of:
1. An Obsidian CLI wrapper
2. Vaults
3. Files

As a warning, the Obsidian's CLI is still fairly new. Accepting
ugly code to avoid rewriting what might change tomorrow avoids
wasting work. The prime ugliness is in:

1. Forward references enabled by from __future__ import annotations
2. Badly resolved frozen sets and inline tuples for int conversion on fields
"""
from __future__ import annotations
from collections import UserList
from enum import StrEnum, auto
from io import StringIO
from pathlib import Path
import re
import subprocess
from typing import Final, Generator, Iterable, Protocol, Self, TypeVar, TypedDict

import yaml

from misc_obsidian_helpers.filesystem import expand_resolve_path


# Emoji / ZWJ https://pypi.org/project/regex/
USING_3RD_PARTY_RE_MODULE: bool
try:
    import regex as re  # type: ignore  # pylance does not respect # pyright: ignore[reportMissingImports]
    USING_3RD_PARTY_RE_MODULE = True
except ImportError as _:
    import re
    USING_3RD_PARTY_RE_MODULE = False  # noqa


FRONTMATTER_PREFIX = re.compile(r"""---\n(?P<yaml>(?:[^\n]+\n)+)---""", re.X)


class ObsidianPropertyBuiltinType(StrEnum):
    """text|list|number|checkbox|date|datetime"""
    TEXT = auto()
    LIST = auto()
    NUMBER = auto()
    CHECKBOX = auto()
    date = auto()
    datetime = auto()

    # TODO: implement a cleaner default approach
    @classmethod
    def parse_optional_kwarg(cls, raw: str | None) -> Self | None:
        """Parse an optional value or leave it as None"""
        if raw is not None:
            return cls(raw)
        else:
            return None


class SupportsStrDunder(Protocol):
    def __str__(self) -> str:
        ...

S = TypeVar('S', bound=SupportsStrDunder)
T = TypeVar('T')


# We don't need the OOP csv module readers since we only have to columns.
def _strip_and_split_tsv_row(
    row: str,
    sep: str = '\t'
) -> list[str]:
    return row.strip().split(sep)


OBSIDIAN_CLI_VERSIONS = re.compile(
r"""
(?P<application>[0-9]+(?:\.[0-9]+)+)
(?:
        (?:\ \(installer\ )
        (?P<installer>[0-9]+(?:\.[0-9]+)+)
        \)
)?
""", re.X | re.UNICODE)


class HasRunnerContext:
    """Base class for types with an Obsidian runner."""
    def __init__(self, runner: ObsidianRunner | None = None):
        self._runner = runner or get_runner()


class FileInfoDict(TypedDict):
    path: Path | str
    name: str
    extension: str
    size: int
    created: int
    modified: int


# TODO: find better solution
_fileinfodict_int_fields: Final[frozenset[str]] = frozenset((
    'size',
    'created',
    'modified'
))


class FileAndPathExistentialCheck(HasRunnerContext):
    """Verifies the path given and runner are valid."""

    def __init__(
        self,
        name: str,
        path: Path | str | None = None,
        runner: ObsidianRunner | None = None
    ):
        super().__init__(runner=runner)
        if not isinstance(name, str):
           raise TypeError(f"name must be a string, not {name=!r}")
        self._name = name
        if path:
           use_path = expand_resolve_path(path)
        else:
           use_path = None
        self._path = use_path

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r}, path={self.path!r})"

    @property
    def path(self) -> Path | None:
        return self._path

    @property
    def name(self) -> str | None:
        return self._name

    def _get_file_or_path_arg(self) -> str:
        if path := self.path:
            return f"path={str(path)}"
        else:
            return f"name={self._name}"

    def info(self) -> FileInfoDict:
        args = ('file', self._get_file_or_path_arg)
        raw = self._runner._run_command_stdout(args)
        if raw.startswith("Error"):
            raise FileNotFoundError(f"File does not appear t exist")

        return dict((line.split('\t') for line in raw.splitlines()))  # type: ignore

    def exists(self) -> bool:
        return self._path is not None and self._path.exists()


class ObsidianVault(FileAndPathExistentialCheck):

    def __init__(
        self,
        name: str,
        files: int = 0,
        folders: int = 0,
        size: int = 0,
        path: Path | str | None = None,
        runner: ObsidianRunner | None = None
    ):
        super().__init__(name=name, path=path, runner=runner)
        self.files = files
        self.folders = folders
        self.size = size

    def get_file_by_name(self, name: str) -> ObsidianFile:
        kwargs = self._runner.get_file_kwargs_by_name(name=name)
        return ObsidianFile(vault=self, **kwargs)


class VaultList(UserList[ObsidianVault]):
    def __init__(self, data):
        super().__init__(data)

    def get_by_name(self, name: str) -> ObsidianVault | None:
        for pair in self.data:
            if pair.name == name:
                return pair
        return None

    def get_by_path(self, path: str | Path) -> ObsidianVault | None:
        path = expand_resolve_path(path)
        for pair in self.data:
            if pair.path == path:
                return pair
        return None


class ObsidianException(Exception):
    ...


class ObsidianRunner:
    """Runs commands against Obsidian's CLI.

    Arguments:
        args: An iterable of strings or string-convertible objects.
        stdout: A subprocess stream status or None (PIPE, DEVNULL)
        stderr: A subprocess stream status for steder (PIPE, DEVNULL, or STDOUT)

    """
    def _run_command_raw(
            self,
            args: Iterable[SupportsStrDunder]|str,
            stdout = subprocess.PIPE,
            stderr = subprocess.DEVNULL
    ):
        if isinstance(args, str):
            _use_args = [self._command, args]
        else:
            _use_args = [self._command, *args]
        full_command = ' '.join([str(s) for s in _use_args])
        raw = subprocess.run(
            full_command, stdout=stdout, stderr=stderr, shell=True)
        return raw

    def _run_command_stdout(
            self,
            args: Iterable[SupportsStrDunder] | str,
            encoding: str = 'utf-8'
        ) -> str:
        """Run a command, get stdout."""
        raw = self._run_command_raw(args, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        decoded = raw.stdout.decode(encoding=encoding)
        return decoded

    def _run_command_iter_lines(self, args: Iterable[SupportsStrDunder] | str) -> Generator[str, None, None]:
        raw = self._run_command_stdout(args)
        if raw.startswith("Error:"):
            raise ObsidianException(raw.strip())
        else:
            yield from StringIO(raw)

    def _run_tsv_command(
        self,
        args: Iterable[SupportsStrDunder] | str,
        sep='\t'
    ) -> Generator[list[str]]:

        for line in self._run_command_iter_lines(args):
            yield _strip_and_split_tsv_row(line,sep=sep)

    def __init__(self, command: str = 'obsidian'):
        self._command = command
        # result = subprocess.run(f"{command} version", stdout=subprocess.PIPE, shell=True)
        raw = self._run_command_stdout(['version'])
        application_version: tuple[str, ...]
        installer_version: tuple[str, ...] | None = None
        stdout = raw.split('\n')[0].strip()
        if (match := OBSIDIAN_CLI_VERSIONS.match(stdout)):
            groups = match.groupdict()
            application_version = tuple(groups['application'].split('.'))
            if _installer_raw := groups.get('installer', None):
                installer_version = tuple(_installer_raw.split('.'))
        else:
            raise RuntimeError("Can't get Obsidian CLI versions?")
        self._command = command
        self._application_version = application_version
        self._installer_version = installer_version

    @property
    def application_version(self) -> tuple[str, ...]:
        return self._application_version

    @property
    def installer_version(self) -> tuple[str, ...] | None:
        return self._installer_version

    def get_file_kwargs_by_name(self, name: str) -> FileInfoDict:
        quoted = f'"{name}"'
        kwargs = {}
        try:
            kwargs = {}
            for k,v in self._run_tsv_command(f"file file={quoted}"):
                if k in _fileinfodict_int_fields:
                    kwargs[k] = int(v)
                else:
                    kwargs[k] = v
        except ObsidianException as e:
            if e.args[0] == "File {quoted} not found.":
                raise FileNotFoundError(e.args[0])
        return kwargs # type: ignore

    def get_current_vault(self) -> ObsidianVault:
        kwargs = {}
        for k, v in self._run_tsv_command(('vault',)):
            if k in ('files', 'folders', 'size'):
                kwargs[k] = int(v)
            else:
                kwargs[k] = v
        return ObsidianVault(**kwargs)

    def get_vaults(self) -> VaultList:
        """Get a list of pairs of (vault_name, system_path).

        If no vaults exist, the list will be empty.
        """
        vaults = []
        for name, raw_path in self._run_tsv_command(('vaults', 'verbose')):
           path = expand_resolve_path(raw_path)
           vault = ObsidianVault(name=name, path=path, runner=self)
           vaults.append(vault)

        return VaultList(vaults)

    def get_commands(self, prefix: str | None = None) -> list[str]:
        args = ['commands']
        if prefix:
            if not isinstance(prefix, str):
                raise TypeError('prefix must be a string')
            args.append(f'prefix="{prefix}"')
        return [s.strip() for s in self._run_command_iter_lines(args)]

    def execute_command(self, command: str):
        self._run_command_stdout(('commmand', command))

    def restart(self) -> None:
        self._run_command_raw('restart')


DEFAULT_RUNNER: ObsidianRunner | None = None
RUNNER_CACHE: Final[dict[str, ObsidianRunner]] = {}
"""Module-wide runner cache for runner instances."""


# Avoiding functools.cache allows clearing the RUNNER_CACHE above for tests
def get_runner(executable: str | Path = 'obsidian') -> ObsidianRunner:
    """Get a runner for the given Obsidian CLI alias or path.

    NOTE: pathlib.Path instances are flattened to strings internally because:
    1. It doesn't matter if hash(Path("name")) == hash("name")
    2. hash(Path("name")) != hash("name")
    3. That's gonna hurt someone using ==

    Arguments:
        command: The command string to use
    """
    if isinstance(executable, Path):
        use_command = str(expand_resolve_path(executable))
    elif isinstance(executable, str):
        use_command = executable
    else:
        raise TypeError(f"get_runner takes str or Path, not {executable=!r}")

    runner = RUNNER_CACHE.get(use_command, None)
    if runner is None:
        runner = ObsidianRunner(command=use_command)
        RUNNER_CACHE[use_command] = runner

    return runner


class ObsidianFile:

    def __init__(
            self,
            name: str,
            path: str | Path,
            # Should be dynamic, but good enough to demo the idea
            created: int,
            modified: int,
            size: int,
            extension: str,
            lazy: bool = True,
            vault: ObsidianVault | None = None
        ):

            self._system_path = expand_resolve_path(path)
            self._name = name or self._system_path.stem
            self._raw: str | None = None
            self._raw_properties: str | None = None
            self._created = created
            self._modified = modified
            self._extension = extension
            self._size = size
            self._vault = vault
            self._properties: dict | None = None
            self._raw_content: str | None = None
            # Important: tail chasing behavior in change listeners is dangerous, see:
            # https://github.com/pythonarcade/arcade/blob/0b8c2ca558ed6153ee39bd14574fe1b6d8513ad4/util/doc_helpers/vfs.py
            self._stream = StringIO()
            self._content: str | None = None
            self._loaded_at = None
            self._lazy = lazy
            if not lazy:
                 self._load_from_disk()

    def __enter__(self) -> Self:
        return self

    # TODO: proper ctx management or simplification
    def __exit__(self, exc, err, _):
        ...

    @property
    def name(self) -> str:
        return self._name

    def exists(self) -> bool:
        return self._system_path.exists()

    def __repr__(self) -> str:
        lazy = self._lazy
        name = self._name
        system_path = self._system_path
        return f"{self.__class__.__name__}({name=}, {system_path=!r}, {lazy=})"

    @property
    def system_path(self) -> Path:
        return self._system_path

    def _load_from_disk(self):
        _raw = self._system_path.read_text()
        self._raw = _raw

        start_content_at = 0
        have_properties = FRONTMATTER_PREFIX.match(_raw)
        if have_properties:
            gd = have_properties.groupdict()
            _raw_yaml = gd['yaml']
            _raw_stream = StringIO(_raw_yaml)
            _dict = yaml.safe_load(_raw_stream)
            self._properties = _dict
            start_content_at = len(have_properties.group(0))
            _content = _raw[start_content_at:]
        else:
            self._properties = {}
            _content = _raw
        self._raw_content = _content
        self._content = _content

    @property
    def properties(self) -> dict:
        if self._content is None:
             self._load_from_disk()
        if (props := self._properties) is None:
            raise Exception("No properties was loaded?")
        return props

    @property
    def content(self) -> str:
        if self._content is None:
            self._load_from_disk()
        if (content := self._content) is None:
                raise Exception("No content was loaded?")
        return content


class ObjectType(StrEnum):
    """Obsidian resource types to query."""
    VAULT = auto()
    FILE = auto()


__all__ = [
    'USING_3RD_PARTY_RE_MODULE',
    'FRONTMATTER_PREFIX',
    'OBSIDIAN_CLI_VERSIONS',
    'ObsidianRunner',
    'ObsidianPropertyBuiltinType',
    'HasRunnerContext',
    'DEFAULT_RUNNER',
    'RUNNER_CACHE',
    'get_runner',
    'ObsidianVault',
    'ObsidianFile',
    'ObjectType',
]