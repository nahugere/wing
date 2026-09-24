import sys
import asyncio
import argparse
from .wing import Wing
from ._version import __version__
# from presets import Preset, Presets

WING = Wing()

def build_parser():
    parser = argparse.ArgumentParser(
        prog="wing",
        description="Wing is a CLI tool that can forward your ports using one line of code.\nRun 'wing start <port-number>' to start forwarding."
    )
    parser.add_argument(
        "-v", "--version",
        action="version",
        help="Get which version of wing you're running"
    )
    parser.add_argument(
        "action",
        choices=["start"],
        help="Start port forwarding by specifying the port you want to work on"
    )
    parser.add_argument(
        "target",
        type=int,
        help="The port number you want to work on"
    )
    return parser

if __name__ == "__main__":
    parser = build_parser()
    args = parser.parse_args()

    try:
        if "start" in args.action:
                asyncio.run(WING.start(args.target))
    except KeyboardInterrupt:
        print("\nByeeee")