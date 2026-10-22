"""Mac power adapter, charge rate, and time-to-full/empty from the command line."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("chargewatch")
except PackageNotFoundError:
    __version__ = "0+unknown"


def main() -> int:
    from .cli import main as _main

    return _main()
