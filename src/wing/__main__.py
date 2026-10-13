import sys
import signal
import asyncio
import argparse
from .wing import Wing
from pynput import keyboard
from ._version import __version__
from .integrations.flutter_preset import FlutterPreset

WING = Wing()

import argparse

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
        except Exception as e:
            print(e)
            return

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    main_task = None

    def handle_sigint():
        if main_task and not main_task.done():
            main_task.cancel()
        loop.stop()

    loop.add_signal_handler(signal.SIGINT, handle_sigint)


    try:
        main_task = loop.create_task(WING.start(target))
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        pending = asyncio.all_tasks(loop)
        for task in pending:
            task.cancel()

        if pending:
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))

        loop.run_until_complete(WING.http_client.aclose())
        loop.close()
        print("\nByeeee")

def on_press(key):
  try:
    print(f"Key {key.char} pressed")
  except AttributeError:
    print(f"Special key {key} pressed")

def on_release(key):
  if key == keyboard.Key.esc:
    return False

def main():
    parser = build_parser()
    args = parser.parse_args()

    if "start" in args.action:
        with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
            listener.join()
        handle_start(args.target, args.flutter)

if __name__ == "__main__":
    main()