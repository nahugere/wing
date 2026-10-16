import sys
import signal
import asyncio
import argparse
import httpx
import websockets
from .wing import Wing
# from pynput import keyboard
from ._version import __version__
from .integrations.flutter_preset import FlutterPreset

WING = Wing()
flutter_preset = None

def build_parser():
    parser = argparse.ArgumentParser(
        prog="wing",
        description=(
            "Wing is a CLI tool that can forward your ports using one line of code.\n"
            "Run 'wing start <port-number>' to start forwarding, "
            "or 'wing start --flutter <path-to-flutter-project>' to start a Flutter preview."
        )
    )
    parser.add_argument(
        "-v", "--version",
        action="version",
        help="Get which version of wing you're running"
    )
    parser.add_argument(
        "action",
        choices=["start"],
        help="Start port forwarding"
    )
    parser.add_argument(
        "target",
        nargs="?",
        help="The port number you want to forward"
    )
    parser.add_argument(
        "-f", "--flutter",
        action="store_true",
        help="Build and serve a Flutter web project"
    )
    return parser

def handle_start(target, flutter=False):
    if flutter:
        try:
            flutter_preset = FlutterPreset(target)
            flutter_preset.run_build()
            target = flutter_preset.start_server()
        except ValueError as e:
            print(f"\n\033[31mError: {e}\033[0m")
            return
        except Exception:
            print(
                "\n\033[31mAn error occurred while setting up your Flutter project.\033[0m"
                f" Check \033[33m{WING.log_file}\033[0m for details"
            )
            return

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    main_task = None

    def handle_sigint():
        if main_task and not main_task.done():
            main_task.cancel()
        loop.stop()

    loop.add_signal_handler(signal.SIGINT, handle_sigint)

    def _loop_exception_handler(loop, context):
        exc = context.get("exception")
        if exc and not isinstance(exc, asyncio.CancelledError):
            if isinstance(exc, (OSError, httpx.HTTPError, websockets.WebSocketException)):
                return
            WING.logger.exception("Unhandled exception in event loop")

    loop.set_exception_handler(_loop_exception_handler)


    try:
        main_task = loop.create_task(WING.start(target))
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        WING.logger.exception("Unexpected error")
        print(f"\n{WING.RED}An unexpected error occurred{WING.RESET}. "
              f"Check {WING.YELLOW}{WING.log_file}{WING.RESET} for details")
    finally:
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.remove_signal_handler(sig)

        try:
            pending = [t for t in asyncio.all_tasks(loop) if not t.done()]
            for task in pending:
                task.cancel()
            if pending:
                loop.run_until_complete(
                    asyncio.wait(pending, timeout=3.0)
                )
            loop.run_until_complete(WING.http_client.aclose())
            loop.run_until_complete(loop.shutdown_asyncgens())
        except KeyboardInterrupt:
            pass
        finally:
            asyncio.set_event_loop(None)
            loop.close()

def main():
    parser = build_parser()
    args = parser.parse_args()

    if "start" in args.action:
        handle_start(args.target, args.flutter)

if __name__ == "__main__":
    main()