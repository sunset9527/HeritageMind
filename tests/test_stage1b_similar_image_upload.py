"""公开以图搜图只接受有界、可解码的图片。"""

import asyncio
from io import BytesIO

import pytest
from fastapi import HTTPException
from PIL import Image
from starlette.datastructures import Headers, UploadFile


def _upload(data: bytes, filename: str = "query.png", mime: str = "image/png") -> UploadFile:
    return UploadFile(BytesIO(data), filename=filename, headers=Headers({"content-type": mime}))


def _png() -> bytes:
    output = BytesIO()
    Image.new("RGB", (2, 2), "red").save(output, format="PNG")
    return output.getvalue()


def test_similar_image_rejects_decoding_failure_and_cleans_temp(tmp_path, monkeypatch):
    import api

    monkeypatch.setattr(api.settings, "media_storage_path", str(tmp_path))
    with pytest.raises(HTTPException) as error:
        asyncio.run(api.search_similar_image(_upload(b"\x89PNG\r\n\x1a\nnot-image"), 6, object()))

    assert error.value.status_code == 415
    assert list(tmp_path.rglob("*.part")) == []


def test_similar_image_uses_validated_bytes_and_always_removes_temp(tmp_path, monkeypatch):
    import api

    captured = {}
    monkeypatch.setattr(api.settings, "media_storage_path", str(tmp_path))
    monkeypatch.setattr(
        api,
        "search_similar_images",
        lambda db, content, top_k: captured.update(content=content, top_k=top_k) or [],
    )

    result = asyncio.run(api.search_similar_image(_upload(_png()), 7, object()))

    assert result == {"results": [], "total": 0}
    assert captured == {"content": _png(), "top_k": 7}
    assert list(tmp_path.rglob("*.part")) == []


def test_similar_image_top_k_openapi_boundary_is_one_to_twenty():
    from api import app

    parameter = next(
        item
        for item in app.openapi()["paths"]["/search/similar"]["post"]["parameters"]
        if item["name"] == "top_k"
    )
    assert parameter["schema"]["minimum"] == 1
    assert parameter["schema"]["maximum"] == 20
