"""ScanSnap USB wireless setup. Importing this module never opens a device."""

from common import SetupError
from core import CommandError
from device import SetupDevice, connect

__all__ = ["SetupDevice", "connect", "SetupError", "CommandError"]


if __name__ == "__main__":
    from cli import main

    raise SystemExit(main())
