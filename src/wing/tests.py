import pytest
import asyncio
from .wing import Wing

class FakeWS:

    def __init__(self):
        self.sent = []

    async def send(self, data):
        self.sent.append(data)

@pytest.mark.asyncio
async def test_multiple_chunks():
    ws = FakeWS()
    w = Wing()

    await w.send_binary(ws, "abc", 200, {}, b"Hello", False)
    await w.send_binary(ws, "abc", 304, {}, b"World", True)
    await w.send_binary(ws, "abc", 200, {}, b"!", False)
    await w.send_binary(ws, "abc", 200, {}, b"", True)

    print(ws.sent)

    assert len(ws.sent) == 4

# @pytest.mark.asyncio
# async def test_ws_datatype():