"""Owned source pages and an observed, enforced loopback connection boundary."""

import asyncio
import io
import sys
from collections import Counter
from dataclasses import dataclass
from urllib.parse import urlsplit

from aiohttp import web
from aiohttp.test_utils import TestServer
import numpy as np
from PIL import Image
import pytest_asyncio

BODY = "*** START OF BOOK ***\nSynthetic states and time.\n*** END OF BOOK ***"


@dataclass
class AdapterPages:
    base: str
    calls: Counter
    hosts: list
    connects: list
    denied: list


@pytest_asyncio.fixture
async def adapter_pages():
    calls, hosts, connects, denied = Counter(), [], [], []
    buffer = io.BytesIO()
    Image.fromarray(np.arange(16 * 12 * 3, dtype=np.uint8).reshape((12, 16, 3))).save(
        buffer, "PNG"
    )

    async def respond(request):
        path = request.path
        calls[path] += 1
        hosts.append(request.host)
        if path.startswith("/files/slow/"):
            await asyncio.sleep(0.15)
        if path == "/bad":
            return web.Response(status=503)
        if path in ("/archive-search", "/works", "/works/poems", "/works/prophecies"):
            return web.Response(
                text='<a href="/works/archive">Synthetic song</a><a href="/works/archive">Duplicate</a><a href="/object/object">Object title</a><a href="/item/item">Item title</a><a href="/works/short">X</a>',
                content_type="text/html",
            )
        if path == "/browse":
            return web.Response(status=404)
        if path == "/pg-search":
            return web.Response(
                text='<a href="/ebooks/701">Blake synthetic poems</a><a href="/ebooks/1">Other author</a><a href="/contact">Blake contact</a>',
                content_type="text/html",
            )
        if path == "/ia-search":
            return web.Response(
                text='<a href="/details/test">Blake synthetic record</a><a href="/details/other">Other author</a>',
                content_type="text/html",
            )
        if path == "/works/archive":
            return web.Response(
                text='<h1>Synthetic song</h1><div class="text-content"><p>First</p><p>Second</p></div><a href="/image.png">plate</a>',
                content_type="text/html",
            )
        if path == "/ebooks/701":
            return web.Response(
                text='<h1>Synthetic poems</h1><a href="/book.txt">Plain text</a>',
                content_type="text/html",
            )
        if path == "/ebooks/702":
            return web.Response(
                text='<h1>Synthetic manuscript</h1><a href="/book.htm">HTML text</a>',
                content_type="text/html",
            )
        if path == "/ebooks/706":
            return web.Response(
                text='<h1>Wrapper only</h1><a href="/wrapper-only.txt">Text</a>',
                content_type="text/html",
            )
        if path == "/wrapper-only.txt":
            return web.Response(
                text="Project Gutenberg\n*** START OF BOOK ***\n*** END OF BOOK ***\nLicense"
            )
        if path in ("/ebooks/703", "/ebooks/704", "/ebooks/705"):
            return web.Response(
                text="<h1>Synthetic text</h1>", content_type="text/html"
            )
        if path == "/book.txt":
            return web.Response(text=BODY)
        if path == "/book.htm":
            return web.Response(
                text="<p>*** START OF BOOK ***</p><p>HTML states.</p><p>*** END OF BOOK ***</p>",
                content_type="text/html",
            )
        if path in ("/files/704/704-0.txt", "/files/705/705-h/705-h.htm"):
            long = (
                "Project Gutenberg\n*** START OF BOOK ***\n"
                + "Synthetic states.\n" * 80
                + "*** END OF BOOK ***"
            )
            return web.Response(
                text="<p>" + long.replace("\n", "</p><p>") + "</p>"
                if path.endswith(".htm")
                else long
            )
        if path == "/details/test":
            return web.Response(
                text='<h1 class="item-title">Synthetic item</h1><div class="item-description">Description</div><span>1894</span><a href="/ia.txt">text.txt</a><a href="/image.png">plate.png</a><a href="/ignored.pdf">PDF</a>',
                content_type="text/html",
            )
        if path == "/ia.txt":
            return web.Response(text="Synthetic IA text.")
        if path == "/image.png":
            return web.Response(body=buffer.getvalue(), content_type="image/png")
        return web.Response(status=404)

    app = web.Application()
    app.router.add_get("/{tail:.*}", respond)
    async with TestServer(app) as server:
        base = str(server.make_url("/")).rstrip("/")
        expected = urlsplit(base)
        active = True

        def audit(event, args):
            if not active:
                return
            if event == "socket.getaddrinfo" and args[0] not in (
                expected.hostname,
                None,
            ):
                denied.append((str(args[0]), args[1]))
                raise RuntimeError("Non-owned HTTP endpoint refused")
            if event == "socket.connect":
                address = args[1]
                if not isinstance(address, tuple) or address[:2] != (
                    expected.hostname,
                    expected.port,
                ):
                    denied.append(str(address))
                    raise RuntimeError("Non-owned HTTP endpoint refused")
                connects.append(address[:2])

        sys.addaudithook(audit)
        try:
            yield AdapterPages(base, calls, hosts, connects, denied)
        finally:
            active = False
