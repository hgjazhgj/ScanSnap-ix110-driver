#!/usr/bin/env python3
"""Generate a host Manager ID without connecting to a scanner."""

from __future__ import annotations

import argparse
import secrets


def generate_manager_id() -> str:
    while True:
        value = secrets.token_bytes(8)
        if any(value):
            return value.hex()


def main(argv: list[str] | None = None) -> int:
    argparse.ArgumentParser(description=__doc__).parse_args(argv)
    print(generate_manager_id())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
