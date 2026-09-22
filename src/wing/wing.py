import asyncio
from datetime import datetime
import json
import logging
import os
import struct
import requests
import websockets
import threading
import urllib3

class Wing:

    URI = "http://localhost:4000"
    WS_URI = "ws://localhost:4000"
    VM_WS_URI = "ws://localhost:"
    VM_WS_PORT = 5432

    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    RESET = "\033[0m"
    
    DB_NAME = "projects.db"

    def __init__(self):
        self._setup_logger()

    def _reg_session(self):
        response = requests.post(f"{self.URI}/api/create")
        data = response.json()

        if data.get("statusCode") != 200:
            return

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
        async for message in local_ws:
            isBinary = isinstance(message, bytes)
            await tunnel_ws.send(json.dumps({
                'clientId': client_id,
                'isBinary': isBinary,
                'message': message.decode('base64') if isBinary else message
            }))

    async def vmService(self, project_id, preset, port):
        local_connections = {}

        async with websockets.connect(f"{self.VM_WS_URI}{self.VM_WS_PORT}/{project_id}", additional_headers={"X-Wing-Role": "agent"}) as ws:
            while True:
                m = await ws.recv()
                message = json.loads(m)
                if preset.name != "FLUTTER":
                    port = message['port']
            
                try:

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
                    self.logger.exception("Forwarding failed")
                    self.log(
                        f"{self.RED}Error: {e}{self.RESET}. Check {self.YELLOW}{self.log_file}{self.RESET} for details"
                    )

    async def start(self, project_id, port, preset=None, *args, **kwargs):
        project_id, secret = self._reg_session()
        if not(project_id and secret):
            print(f"{self.RED}Session registration failed{self.RESET}")
            return

        headers = {"Authorization": f"Bearer {secret}"}

        if preset:
            try:
                asyncio.create_task(self.vmService(project_id, preset, port))
                print(f"Forwarding Dart VM services")

            except Exception as e:
                self.logger.exception("Forwarding failed")
                self.log(
                    f"{self.RED}Error: {e}{self.RESET}. Check {self.YELLOW}{self.log_file}{self.RESET} for details"
                )

        async with websockets.connect(f"{self.WS_URI}/{project_id}", additional_headers=headers) as ws:
            print("Connection to server established")
            print(f"Forwarding port {self.YELLOW}{port}{self.RESET}")

            while True:
                try:
                    # TODO: Implement error catching and logging
                    m = await ws.recv()
                    message = json.loads(m)

                    method = message["method"]
                    location = message["path"]

                    self.log(f"Received: [{method}] {self.YELLOW}http://127.0.0.1:{port}{location}{self.RESET}")
                    
                    headers = dict(message["headers"])

                    headers["x-forwarded-for"] = message.get("ip", "196.191.61.106")
                    headers["x-forwarded-host"] = message["headers"].get("host", "")
                    headers["x-forwarded-proto"] = "http"
                    headers["x-forwarded-by"] = "wing-tunnel"

                    body = message["body"]

                    if isinstance(body, dict) and body.get("type") == "Buffer":
                        body = bytes(body["data"])

                    response = requests.request(
                        method,
                        f"http://localhost:{port}{location}",
                        params=message.get("query", None),
                        headers=headers,
                        cookies=message.get("cookies", None),
                        data=body,
                    )

                    try:
                        response.headers["Transfer-Encoding"] = "chunked"
                        del response.headers["Content-Length"]
                    except:
                        pass

                    response.headers["Project-Id"] = project_id
                    headers_dict = dict(response.headers)
                    set_cookies = response.raw.headers.getlist("Set-Cookie")
                    
                    if set_cookies:
                        headers_dict["Set-Cookie"] = set_cookies

                    chunks = list(response.iter_content(64*1024))

                    if response.status_code == 304:
                        await self.send_binary(ws, message["messageId"], response.status_code, headers_dict, b"", True)

                    for i, chunk in enumerate(chunks):
                        if chunk:
                            await self.send_binary(ws, message["messageId"], response.status_code, response.headers, chunk, i==len(chunks)-1)
                    
                    self.log(f"Sent [{self.GREEN}{response.status_code}{self.RESET}] {response.headers.get('Content-Type', '')} @ {location}")

                except Exception as e:
                    self.logger.exception("Forwarding failed")
                    self.log(
                        f"{self.RED}Error: {e}{self.RESET}. Check {self.YELLOW}{self.log_file}{self.RESET} for details"
                    )

            # await self.vmService(args[1])

    def create(self, project_name):
        response = requests.post(f"{self.URI}/api/create", json={"name": project_name})
        data = response.json()
        print(data)
        if (data["statusCode"]==200):
            project_id = data['data']['project_id']
            self._save_to_sql(project_name, project_id)
            print(f"Project created with project id {self.YELLOW}{project_id}{self.RESET}")
        elif (data["statusCode"]==500):
            print(f"{self.RED}Server error please try again later{self.RESET}")
        return
    
    def help(self):
        # TODO: Add random dad joke generator
        print("WINGGGGGGGGGGGG\n\n")

    def version(self):
        print("Still a beta")