"""Command-line entry point; --help and list-functions never open USB."""

from cli import main

if __name__ == "__main__":
    raise SystemExit(main())
