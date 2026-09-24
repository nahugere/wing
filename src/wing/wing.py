import os
import json
import httpx
import struct
import urllib3
import asyncio
import logging
import requests
import threading
import websockets
from datetime import datetime
from .config import DEFAULT_PORT, DEFAULT_SERVER_URL, DEFAULT_TIMEOUT

class Wing:

    URI = DEFAULT_SERVER_URL
    WS_URI = f"ws://localhost:{DEFAULT_PORT}"
    VM_WS_URI = "ws://localhost:"
    VM_WS_PORT = 5432

    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    RESET = "\033[0m"
    
    DB_NAME = "projects.db"

    def __init__(self):
        self._setup_logger()
        self.http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(DEFAULT_TIMEOUT),
            follow_redirects=False
        )

    def _reg_session(self):
        try:
            response = requests.post(f"{self.URI}/api/create")
            data = response.json()
        except Exception as e:
            self.logger.exception("Session registration failed")
            self.log(
                f"{self.RED}Error: {e}{self.RESET}. Check {self.YELLOW}{self.log_file}{self.RESET} for details"
            )
            return None, None

        if data.get("statusCode") != 200:
            return None, None

        return data.get("data")["project_id"], data.get("data")["secret"]

    def _setup_logger(self):
        os.makedirs("logs", exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = f"logs/error_{timestamp}.log"

        self.logger = logging.getLogger(f"wing_{timestamp}")
        self.logger.setLevel(logging.ERROR)

        handler = logging.FileHandler(self.log_file)
        handler.setFormatter(logging.Formatter(
            "%(asctime)s\n%(levelname)s\n%(message)s\n"
        ))

        self.logger.addHandler(handler)

    def log(self, message):
        now = datetime.now()
        print(f"\t[{now}] {message}")

    async def send_binary(self, ws, mid, status, headers, chunk, isLast, meta=None):
        # Binary type
        if not meta:
            meta = json.dumps({
                "messageId": mid,
                "status": status,
                "headers": dict(headers),
                "isLast": isLast
            }).encode('utf-8')
        
        # Big-Endian notation to package the header
        meta_len = len(meta)
        header = struct.pack(">I", meta_len)

        # Sending the payload
        payload = chunk if chunk else b""
        await ws.send(header + meta + payload)

    async def vmListen(self, local_ws, tunnel_ws, client_id):
        try:
            async for message in local_ws:
                isBinary = isinstance(message, bytes)
                await tunnel_ws.send(json.dumps({
                    'clientId': client_id,
                    'isBinary': isBinary,
                    'message': message.decode('base64') if isBinary else message
                }))
        except Exception as e:
            self.logger.exception("Dart VM listen failed")
            self.log(
                f"{self.RED}Error: {e}{self.RESET}. Check {self.YELLOW}{self.log_file}{self.RESET} for details"
            )

    async def vmService(self, project_id, preset):
        local_connections = {}

        try:
            async with websockets.connect(f"{self.VM_WS_URI}{self.VM_WS_PORT}/{project_id}", additional_headers={"X-Wing-Role": "agent"}) as ws:
                while True:
                    m = await ws.recv()
                    message = json.loads(m)
                    port = message['port']

                    if port not in local_connections:
                        local_ws = await websockets.connect(f"ws://localhost:{port}/{'/'.join(message['params'])}")
                        asyncio.create_task(self.vmListen(local_ws, ws, message['clientId']))
                        local_connections[port] = local_ws

                    raw = message['message']
                    if message['isBinary']:
                        await local_connections[port].send(bytes(raw, 'base64'))
                    else:
                        await local_connections[port].send(raw)

        except Exception as e:
            self.logger.exception("Dart VM forward failed")
            self.log(
                f"{self.RED}Error: {e}{self.RESET}. Check {self.YELLOW}{self.log_file}{self.RESET} for details"
            )

    async def streamReqs(self, port, message, ws):
        method = message["method"]
        location = message["path"]
        mid = message["messageId"]

        headers = dict(message["headers"])

        headers["x-forwarded-for"] = message.get("ip", "")
        headers["x-forwarded-host"] = message["headers"].get("host", "")
        headers["x-forwarded-proto"] = "http"
        headers["x-forwarded-by"] = "wing-tunnel"

        body = message["body"]
        if isinstance(body, dict) and body.get("type") == "Buffer":
            body = bytes(body["data"])

        self.log(f"Received: [{method}] {self.YELLOW}http://127.0.0.1:{port}{location}{self.RESET}")
        async with self.http_client.stream(
            method,
            f"http://localhost:{port}{location}",
            params=message.get("query", None),
            headers=headers,
            cookies=message.get("cookies", None),
            data=body,
        ) as response:

                try:
                    response.headers["Transfer-Encoding"] = "chunked"
                    del response.headers["Content-Length"]
                except:
                    pass

                response_headers = list(response.headers.multi_items())

                await self.send_binary(
                    ws, mid, response.status_code, response_headers, b"", False)

                async for chunk in response.aiter_bytes():
                    await self.send_binary(
                        ws, mid, response.status_code, response_headers, chunk, False)

                await self.send_binary(
                    ws, mid, response.status_code, response_headers, b"", True)

    async def start(self, port, wsForwarding=True, *args, **kwargs):
        project_id, secret = self._reg_session()
        if not(project_id and secret):
            print(f"{self.RED}Session registration failed{self.RESET}")
            return

        headers = {"Authorization": f"Bearer {secret}"}

        if wsForwarding:
            try:
                asyncio.create_task(self.vmService(project_id, wsForwarding))
                print(f"Forwarding Dart VM services")

            except Exception as e:
                pass
                self.logger.exception("Forwarding failed")
                self.log(
                    f"{self.RED}Error: {e}{self.RESET}. Check {self.YELLOW}{self.log_file}{self.RESET} for details"
                )

        async with websockets.connect(f"{self.WS_URI}/{project_id}", additional_headers=headers) as ws:
            print("Connection to server established")
            print(f"Forwarding port {self.YELLOW}{port}{self.RESET}\n")
            print(f"Project url: {self.URI}/tunnel/{project_id}/")

            while True:
                try:
                    m = await ws.recv()
                    message = json.loads(m)

                    await self.streamReqs(port, message, ws)
                    
                except Exception as e:
                    self.logger.exception("Forwarding failed")
                    self.log(
                        f"{self.RED}Error: {e}{self.RESET}. Check {self.YELLOW}{self.log_file}{self.RESET} for details"
                    )

            # await self.vmService(args[1])