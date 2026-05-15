import argparse
from typing import Protocol, TypedDict, Unpack
from misc_obsidian_helpers.filesystem import parse_existing_dir
from misc_obsidian_helpers.runners import obsidian
from misc_obsidian_helpers.runners.obsidian import ObjectType


class _CoreKwargs(TypedDict, total=False):
    prog: str | None
    description: str | None


# Really, needs replacement
class MakesParser[R](Protocol):
    def __call__(self, **kwargs: Unpack[_CoreKwargs]) -> R:
        ...


def build_argument_parser(
    prog: str | None = None,
    description: str | None = None,
    default_executable: str | None = 'obsidian'
) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog=prog, description=description)
    parser.add_argument(
        "--vault-name", nargs='?', type=str, default=None,
        help="The name of the Obsidian vault to use")
    parser.add_argument(
        "--vault-path", nargs='?', type=parse_existing_dir, default=None,
        help="The path of the Obsidian vault to use")
    parser.add_argument(
        '--obsidian-executable', nargs='?', type=str, default=default_executable
    )
    parser.add_argument(
        '--list', nargs='?', type=ObjectType, default=None, help="list something"
    )
    parser.add_argument(
        '--info', nargs='?', type=ObjectType, default=None, help="show stats about something"
    )
    parser.add_argument(
        '--name', nargs='?', type=str, default=None, help="name minus extension",
    )
    return parser


def main(
    argv: list[str] | None = None,
    # TODO: finish removing typer or make it optional
    parser_builder: MakesParser[argparse.ArgumentParser] = build_argument_parser # type: ignore
):
    parser = parser_builder(prog="obsidian-util", description="Vault access")
    namespace = parser.parse_args(args=argv)
    runner = obsidian.get_runner(namespace.obsidian_executable)

    if namespace.list:
        match namespace.list:
            case ObjectType.VAULT:
                for vault_entry in runner.get_vaults():
                    print(f"{vault_entry.name}\t{str(vault_entry.path)}")
            case _:
                raise NotImplementedError("Not yet bound")
    elif namespace.info:
        match namespace.info:
            case ObjectType.FILE:
                vault = runner.get_current_vault()
                file = vault.get_file_by_name(name=namespace.name)
                print(file)


if __name__ == "__main__":
    main()
