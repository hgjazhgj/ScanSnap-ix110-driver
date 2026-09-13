"""One CLI subcommand per public device operation, generated from API signatures."""

from __future__ import annotations

import argparse
import getpass
import inspect
import json
from pathlib import Path
import sys
from types import UnionType
from typing import get_args, get_origin, get_type_hints

from device import SetupDevice, connect


_PROMPT = object()
SECRET_WORDS = ("password", "secret", "key", "pwdcode", "credential", "token", "pin")


def operations() -> dict:
    return {name: method for name, method in inspect.getmembers(SetupDevice, inspect.isfunction)
            if hasattr(method, "operation_description")}


def public_value(value, *, show_secrets: bool = False, name: str = ""):
    sensitive = any(word in name.lower() for word in SECRET_WORDS)
    # Required/present flags and lengths reveal no password contents.
    metadata = name.endswith(("_required", "_present", "_enabled", "_display", "_size", "_length"))
    if sensitive and not metadata and not show_secrets:
        return "<redacted>" if value else value
    if isinstance(value, dict):
        return {str(k): public_value(v, show_secrets=show_secrets, name=str(k)) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [public_value(v, show_secrets=show_secrets, name=name) for v in value]
    if isinstance(value, bytes):
        return {"size": len(value), "hex": value.hex() if show_secrets else "<redacted binary>"}
    return value


def _parameter_type(annotation):
    if get_origin(annotation) in (UnionType, __import__("typing").Union):
        annotation = next((t for t in get_args(annotation) if t is not type(None)), str)
    return get_origin(annotation) or annotation


def _connection_options(parser):
    parser.add_argument("--backend", choices=("auto", "usbscan", "libusb"), default="auto",
                        help="USB backend; auto falls back only while opening")
    parser.add_argument("--usbscan-port", help=r"explicit Windows port, e.g. \\.\Usbscan3")
    parser.add_argument("--timeout", type=float, default=30.0, help="setup-operation timeout in seconds")
    parser.add_argument("--io-timeout", type=float, default=120.0, help="libusb I/O timeout in seconds")
    parser.add_argument("--encoding", default="utf-8", help="device text encoding (default: utf-8)")
    parser.add_argument("--legacy-key", action="store_true", help="use newer-model pFus secret seed; iX100/iX110 default is aQwe")
    parser.add_argument("--show-secrets", action="store_true", help="explicitly include decoded secrets and binary data")
    parser.add_argument("--output-file", type=Path, help="write the result JSON (same redaction policy as stdout)")
    parser.add_argument("--binary-output-file", type=Path,
                        help="explicitly save raw bytes from get-eeprom/get-device-file; batch saves the last binary result")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Independent ScanSnap iX100/iX110 USB wireless setup. "
                                    "Device subcommands open USB and may change settings; --help and list-functions are offline.")
    subs = parser.add_subparsers(dest="subcommand", required=True)
    catalog = subs.add_parser("list-functions", help="list API/CLI mappings without opening USB")
    catalog.add_argument("--json", action="store_true")
    batch = subs.add_parser("run-file", help="execute an explicit JSON command list in one setup session")
    batch.add_argument("--commands-file", type=Path, required=True)
    _connection_options(batch)
    for name, method in operations().items():
        cli_name = name.replace("_", "-")
        sub = subs.add_parser(cli_name, help=method.operation_description,
                              description=method.__doc__ or method.operation_description,
                              formatter_class=argparse.RawDescriptionHelpFormatter)
        sub.set_defaults(method_name=name)
        _connection_options(sub)
        hints = get_type_hints(method)
        input_files = {}
        for parameter in inspect.signature(method).parameters.values():
            if parameter.name == "self":
                continue
            annotation = _parameter_type(hints.get(parameter.name, str))
            flag = "--" + parameter.name.replace("_", "-")
            required = parameter.default is inspect.Parameter.empty
            kwargs = {"dest": parameter.name, "default": argparse.SUPPRESS}
            if annotation is bool:
                kwargs.update(action=argparse.BooleanOptionalAction, required=required)
            elif annotation in (bytes, dict, list):
                flag += "-file"
                kwargs.update(type=Path, required=required,
                              help="binary input file" if annotation is bytes else "UTF-8 JSON input file")
                input_files[parameter.name] = annotation
            elif annotation in (int, float):
                kwargs.update(type=annotation, required=required)
            else:
                kwargs.update(type=str, required=required)
                if any(word in parameter.name.lower() for word in SECRET_WORDS):
                    kwargs.update(nargs="?", const=_PROMPT,
                                  help="omit the value to enter it without terminal echo")
            if parameter.default is not inspect.Parameter.empty:
                kwargs["help"] = (kwargs.get("help", "") + f" (API default: {parameter.default!r})").strip()
            sub.add_argument(flag, **kwargs)
        sub.set_defaults(input_files=input_files)
    return parser


def _kwargs(args, method):
    result = {}
    for name in inspect.signature(method).parameters:
        if name == "self" or not hasattr(args, name):
            continue
        value = getattr(args, name)
        kind = args.input_files.get(name)
        if kind is bytes:
            value = value.read_bytes()
        elif kind in (list, dict):
            value = json.loads(value.read_text(encoding="utf-8-sig"))
        elif value is _PROMPT:
            value = getpass.getpass(name.replace("_", " ") + ": ")
        result[name] = value
    return result


def main(argv=None) -> int:
    # Windows pipe encodings can differ from the language used in help/JSON.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = build_parser()
    args = parser.parse_args(argv)
    available = operations()
    if args.subcommand == "list-functions":
        rows = [{"function": name, "cli": name.replace("_", "-"),
                 "signature": str(inspect.signature(method)),
                 "changes_device": method.operation_mutates,
                 "description": method.operation_description}
                for name, method in available.items()]
        if args.json:
            print(json.dumps(rows, ensure_ascii=False, indent=2))
        else:
            for row in rows:
                print(f"{row['cli']}: {row['description']}")
        return 0
    results = []
    active_operation = None
    binary_result = None
    try:
        if args.subcommand == "run-file":
            # Parse the complete file and resolve methods before opening USB.
            items = json.loads(args.commands_file.read_text(encoding="utf-8-sig"))
            calls = []
            for item in items:
                name = item["command"].replace("-", "_")
                method = available[name]
                values = item.get("arguments", {})
                # Binary arguments in a batch are file paths relative to its JSON.
                hints = get_type_hints(method)
                values = {key: (args.commands_file.parent / value).read_bytes()
                          if _parameter_type(hints.get(key)) is bytes else value
                          for key, value in values.items()}
                calls.append((name, values))
        else:
            calls = [(args.method_name, _kwargs(args, available[args.method_name]))]
        with connect(args.backend, usbscan_port=args.usbscan_port, timeout=args.timeout,
                     io_timeout=args.io_timeout, encoding=args.encoding,
                     legacy_key=args.legacy_key) as device:
            for name, values in calls:
                active_operation = name
                value = getattr(device, name)(**values)
                if isinstance(value, bytes):
                    binary_result = value
                elif isinstance(value, dict) and isinstance(value.get("data"), bytes):
                    binary_result = value["data"]
                results.append({"operation": name, "result": public_value(
                    value, show_secrets=args.show_secrets,
                    name=name if isinstance(value, str) else "")})
                active_operation = None
        if args.binary_output_file:
            if binary_result is None:
                raise ValueError("no binary result is available for --binary-output-file")
            args.binary_output_file.write_bytes(binary_result)
        result = results if args.subcommand == "run-file" else results[0]
        text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
        if args.output_file:
            args.output_file.write_text(text, encoding="utf-8")
        else:
            print(text, end="")
        return 0
    except KeyboardInterrupt:
        print("interrupted; setup-session cleanup was attempted", file=sys.stderr)
        if results:
            print(json.dumps({"completed": results, "interrupted_operation": active_operation},
                             ensure_ascii=False), file=sys.stderr)
        return 130
    except Exception as error:
        # Never print argument values, response bodies, or traceback locals.
        print(f"{type(error).__name__}: {error}", file=sys.stderr)
        if results or active_operation:
            print(json.dumps({"completed": results, "failed_operation": active_operation,
                              "changes_rolled_back": False}, ensure_ascii=False), file=sys.stderr)
        for note in getattr(error, "__notes__", ()):
            print(note, file=sys.stderr)
        return 1
