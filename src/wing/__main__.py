import sys
import asyncio
import argparse
import signal
from .wing import Wing
from ._version import __version__

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

def main():
    parser = build_parser()
    args = parser.parse_args()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    main_task = None

    def handle_sigint():
        if main_task and not main_task.done():
            main_task.cancel()
        loop.stop()

    loop.add_signal_handler(signal.SIGINT, handle_sigint)

    try:
        if "start" in args.action:
            main_task = loop.create_task(WING.start(args.target))
            loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        # Cancel all remaining tasks (vmService, ws_from_local, etc.)
        pending = asyncio.all_tasks(loop)
        for task in pending:
            task.cancel()

        # Wait for all tasks to finish
        if pending:
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))

        # Close the HTTP client
        loop.run_until_complete(WING.http_client.aclose())

        loop.close()
        print("\nByeeee")

if __name__ == "__main__":
    main()