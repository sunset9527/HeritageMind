"""ASGI 请求体限制必须发生在 multipart 解析之前。"""

import asyncio
import json


async def _call_middleware(messages, *, headers=None, limit=10):
    from src.middleware.request_size import RequestBodyLimitMiddleware

    received = []
    sent = []

    async def app(scope, receive, send):
        while True:
            message = await receive()
            received.append(message)
            if not message.get("more_body"):
                break
        await send({"type": "http.response.start", "status": 204, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    queue = list(messages)

    async def receive():
        return queue.pop(0)

    async def send(message):
        sent.append(message)

    middleware = RequestBodyLimitMiddleware(app, max_bytes=limit)
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/media/upload",
        "headers": headers or [],
    }
    await middleware(scope, receive, send)
    return received, sent


def test_content_length_over_limit_is_rejected_before_downstream_app_reads():
    received, sent = asyncio.run(_call_middleware(
        [{"type": "http.request", "body": b"unused", "more_body": False}],
        headers=[(b"content-length", b"11")],
        limit=10,
    ))

    assert received == []
    assert sent[0]["status"] == 413
    assert json.loads(sent[1]["body"])["detail"] == "请求体超过服务器上限"


def test_chunked_body_is_stopped_when_cumulative_bytes_cross_limit():
    received, sent = asyncio.run(_call_middleware(
        [
            {"type": "http.request", "body": b"123456", "more_body": True},
            {"type": "http.request", "body": b"78901", "more_body": False},
        ],
        limit=10,
    ))

    assert len(received) == 1
    assert sent[0]["status"] == 413


def test_body_at_limit_reaches_downstream_app():
    received, sent = asyncio.run(_call_middleware(
        [
            {"type": "http.request", "body": b"12345", "more_body": True},
            {"type": "http.request", "body": b"67890", "more_body": False},
        ],
        limit=10,
    ))

    assert len(received) == 2
    assert sent[0]["status"] == 204
