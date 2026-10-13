import os
import threading
import subprocess
from enum import Enum
from pathlib import Path
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

class QuietHTTPRequestHandler(SimpleHTTPRequestHandler):

  def log_message(self, format, *args):
    pass

class FlutterPreset:

    BUILDING = False
    SERVER = None
    SERVER_THREAD = None

    def __init__(self, location):
        path = Path(location) if location!="." else Path.cwd()
        if not path.exists():
            raise ValueError("Path doesn't exist")
        self.path = path

    def run_build(self):
        if self.BUILDING:
            return "Another build command is already being processed"

        self.BUILDING = True

        try:
            subprocess.run(
                ["flutter", "build", "web"],
                check=True
            )
            print("Flutter Build completed.")
            return True
        except subprocess.CalledProcessError:
            raise subprocess.CalledProcessError("There has been an error running flutter build")
        finally:
            self.BUILDING = False

    def start_server(self, kill_server=False):
        if kill_server:
            self.SERVER.shutdown()
            self.SERVER.close()

        if self.SERVER and self.SERVER_THREAD.is_alive():
            return

        os.chdir(f"{self.path}/build/web")
        self.SERVER = ThreadingHTTPServer(
            ("0.0.0.0", 8374),
            QuietHTTPRequestHandler,
        )
        self.SERVER_THREAD = threading.Thread(
            target=self.SERVER.serve_forever,
            daemon=True,
        )
        self.SERVER_THREAD.start()
        print("Server running on port 8374.")
        return 8374
