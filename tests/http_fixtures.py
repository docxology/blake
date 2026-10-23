"""Finite loopback HTTP responses for real downloader tests."""

import asyncio
import io
from collections import Counter
from dataclasses import dataclass

from aiohttp import web
from aiohttp.test_utils import TestServer
import numpy as np
from PIL import Image
import pytest_asyncio


@dataclass
class LocalResponses:
    base: str
    calls: Counter
    headers: list
    png: bytes


@pytest_asyncio.fixture
async def local_responses():
    pixels = np.arange(16 * 12 * 3, dtype=np.uint8).reshape((12, 16, 3))
    buffer = io.BytesIO()
    Image.fromarray(pixels).save(buffer, format="PNG")
    png = buffer.getvalue()
    calls = Counter()
    headers = []

    async def respond(request):
        calls[request.path] += 1
        headers.append(dict(request.headers))
        if request.path == "/bad":
            return web.Response(status=503, text="unavailable")
        if request.path == "/flaky" and calls[request.path] == 1:
            return web.Response(status=503)
        if request.path == "/slow":
            await asyncio.sleep(0.15)
        if request.path == "/truncated":
            response = web.StreamResponse(headers={"Content-Length": "10000"})
            await response.prepare(request)
            await response.write(b"partial")
            request.transport.close()
            return response
        if request.path == "/empty":
            return web.Response(body=b"")
        if request.path == "/image.png":
            return web.Response(body=png, content_type="image/png")
        if request.path == "/rgba.png":
            image = Image.new("RGBA", (16, 12), (10, 20, 30, 100))
            rgba = io.BytesIO()
            image.save(rgba, format="PNG")
            return web.Response(body=rgba.getvalue(), content_type="image/png")
        if request.path == "/html":
            return web.Response(
                text="<html><body><main><p>A &amp; B</p><p>Second.</p></main></body></html>",
                content_type="text/html",
            )
        return web.Response(body=b"complete payload")

    app = web.Application()
    app.router.add_route("GET", "/{path:.*}", respond)
    async with TestServer(app) as server:
        yield LocalResponses(str(server.make_url("/")).rstrip("/"), calls, headers, png)
