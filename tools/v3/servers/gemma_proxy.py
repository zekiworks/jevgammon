# /// script
# requires-python = ">=3.11"
# dependencies = ["aiohttp==3.14.4"]
# ///
"""Least-busy HTTP proxy in front of identical vLLM replicas (gemma4-31b-replicas.sh).

Every request goes to the replica with the fewest requests in flight (ties in turn), with
method, path, query, headers and body unchanged; the response (status, headers, body) is
streamed back as it arrives, so SSE streaming and logprobs pass through untouched. A replica
that refuses the connection is skipped and the next one tried; once a response has started,
nothing is retried. A client that disconnects closes its upstream request, so vLLM aborts it.

GET /proxy/status reports the requests in flight and served per replica.

    uv run --script tools/v3/servers/gemma_proxy.py --port 8894 \\
        --backend http://127.0.0.1:8900 --backend http://127.0.0.1:8901
"""
import argparse
import asyncio
import itertools

import aiohttp
from aiohttp import web

HOP_BY_HOP = {
    "connection", "keep-alive", "proxy-authenticate", "proxy-authorization", "te", "trailer",
    "trailers", "transfer-encoding", "upgrade", "host", "content-length",
}


class Backend:
    def __init__(self, url: str) -> None:
        self.url = url.rstrip("/")
        self.in_flight = 0
        self.served = 0
        self.failed = 0


class Proxy:
    def __init__(self, urls: list[str]) -> None:
        self.backends = [Backend(u) for u in urls]
        self.turn = itertools.count()
        self.session: aiohttp.ClientSession | None = None

    def order(self) -> list[Backend]:
        """Replicas by requests in flight, ties starting at a rotating position."""
        start = next(self.turn) % len(self.backends)
        rotated = self.backends[start:] + self.backends[:start]
        return sorted(rotated, key=lambda b: b.in_flight)

    async def start(self, app: web.Application) -> None:
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=None, sock_connect=10),
            connector=aiohttp.TCPConnector(limit=0),
            auto_decompress=False,
        )

    async def stop(self, app: web.Application) -> None:
        await self.session.close()

    async def status(self, request: web.Request) -> web.Response:
        return web.json_response([
            {"backend": b.url, "in_flight": b.in_flight, "served": b.served, "failed": b.failed}
            for b in self.backends
        ])

    async def handle(self, request: web.Request) -> web.StreamResponse:
        body = await request.read()
        headers = {k: v for k, v in request.headers.items() if k.lower() not in HOP_BY_HOP}
        last_error: Exception | None = None
        for backend in self.order():
            backend.in_flight += 1
            try:
                try:
                    upstream = await self.session.request(
                        request.method, backend.url + request.rel_url.path_qs,
                        headers=headers, data=body or None, allow_redirects=False,
                    )
                except (aiohttp.ClientConnectionError, asyncio.TimeoutError) as error:
                    backend.failed += 1
                    last_error = error
                    continue
                async with upstream:
                    response = web.StreamResponse(status=upstream.status, reason=upstream.reason)
                    for key, value in upstream.headers.items():
                        if key.lower() not in HOP_BY_HOP:
                            response.headers.add(key, value)
                    if upstream.content_length is not None and "chunked" not in upstream.headers.get(
                            "Transfer-Encoding", "").lower():
                        response.content_length = upstream.content_length
                    await response.prepare(request)
                    async for chunk in upstream.content.iter_any():
                        await response.write(chunk)
                    await response.write_eof()
                    backend.served += 1
                    return response
            finally:
                backend.in_flight -= 1
        return web.json_response({"error": f"no replica answered: {last_error}"}, status=502)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--backend", action="append", required=True, help="replica base URL")
    args = parser.parse_args()
    proxy = Proxy(args.backend)
    app = web.Application(client_max_size=64 * 1024 * 1024)
    app.on_startup.append(proxy.start)
    app.on_cleanup.append(proxy.stop)
    app.router.add_get("/proxy/status", proxy.status)
    app.router.add_route("*", "/{tail:.*}", proxy.handle)
    print(f"proxy on {args.host}:{args.port} -> {', '.join(args.backend)}", flush=True)
    web.run_app(app, host=args.host, port=args.port, print=None, access_log=None)


if __name__ == "__main__":
    main()
