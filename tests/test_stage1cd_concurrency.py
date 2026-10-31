"""阶段 1C/1D：高成本操作的进程内并发许可。"""

import asyncio
from types import SimpleNamespace

import httpx
import pytest
from fastapi import Depends, FastAPI

from src.middleware.request_context import RequestContextMiddleware


def _limits(value=1):
    from src.services.concurrency import HighCostCapability

    return {capability: value for capability in HighCostCapability}


def test_limit_one_rejects_a_second_holder_without_unbounded_waiting():
    from src.services.concurrency import (
        ConcurrencyBusyError,
        ConcurrencyLimiter,
        HighCostCapability,
    )

    async def scenario():
        limiter = ConcurrencyLimiter(limits=_limits(), acquire_timeout_seconds=0.01)
        async with limiter.permit(HighCostCapability.SERVER_LLM):
            with pytest.raises(ConcurrencyBusyError) as raised:
                async with limiter.permit(HighCostCapability.SERVER_LLM):
                    pass
            assert raised.value.retry_after == 1
            snapshot = limiter.snapshot(HighCostCapability.SERVER_LLM)
            assert snapshot.current == 1
            assert snapshot.maximum == 1
            assert snapshot.rejected == 1

    asyncio.run(scenario())


def test_release_after_normal_and_exceptional_exit_restores_capacity():
    from src.services.concurrency import ConcurrencyLimiter, HighCostCapability

    async def scenario():
        limiter = ConcurrencyLimiter(limits=_limits(), acquire_timeout_seconds=0.01)
        async with limiter.permit(HighCostCapability.DOCUMENT_PROCESSING):
            pass
        assert limiter.snapshot(HighCostCapability.DOCUMENT_PROCESSING).current == 0

        with pytest.raises(RuntimeError, match="boom"):
            async with limiter.permit(HighCostCapability.DOCUMENT_PROCESSING):
                raise RuntimeError("boom")
        assert limiter.snapshot(HighCostCapability.DOCUMENT_PROCESSING).current == 0

        async with limiter.permit(HighCostCapability.DOCUMENT_PROCESSING):
            assert limiter.snapshot(HighCostCapability.DOCUMENT_PROCESSING).current == 1

    asyncio.run(scenario())


def test_cancelling_a_holder_releases_its_permit():
    from src.services.concurrency import ConcurrencyLimiter, HighCostCapability

    async def scenario():
        limiter = ConcurrencyLimiter(limits=_limits(), acquire_timeout_seconds=0.01)
        entered = asyncio.Event()

        async def holder():
            async with limiter.permit(HighCostCapability.AUDIO_TRANSCRIPTION):
                entered.set()
                await asyncio.Event().wait()

        task = asyncio.create_task(holder())
        await entered.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

        assert limiter.snapshot(HighCostCapability.AUDIO_TRANSCRIPTION).current == 0
        async with limiter.permit(HighCostCapability.AUDIO_TRANSCRIPTION):
            pass

    asyncio.run(scenario())


def test_capabilities_are_isolated_and_expose_current_maximum_and_rejections():
    from src.services.concurrency import ConcurrencyLimiter, HighCostCapability

    async def scenario():
        limiter = ConcurrencyLimiter(limits=_limits(), acquire_timeout_seconds=0.01)
        async with limiter.permit(HighCostCapability.SERVER_LLM):
            async with limiter.permit(HighCostCapability.RETRIEVAL):
                llm = limiter.snapshot(HighCostCapability.SERVER_LLM)
                retrieval = limiter.snapshot(HighCostCapability.RETRIEVAL)
                assert (llm.current, llm.maximum, llm.rejected) == (1, 1, 0)
                assert (retrieval.current, retrieval.maximum, retrieval.rejected) == (1, 1, 0)

    asyncio.run(scenario())


def test_busy_http_contract_contains_stable_code_retry_after_and_request_id(monkeypatch):
    from src.deps_concurrency import high_cost_limit
    from src.services.concurrency import ConcurrencyLimiter, HighCostCapability

    async def scenario():
        limiter = ConcurrencyLimiter(limits=_limits(), acquire_timeout_seconds=0.01)
        monkeypatch.setattr("src.deps_concurrency.get_concurrency_limiter", lambda: limiter)
        app = FastAPI()
        app.add_middleware(
            RequestContextMiddleware,
            settings=SimpleNamespace(trust_proxy_headers=False, trusted_proxy_ips=[]),
        )

        @app.get("/costly")
        async def costly(_: None = Depends(high_cost_limit(HighCostCapability.SERVER_LLM))):
            return {"ok": True}

        async with limiter.permit(HighCostCapability.SERVER_LLM):
            transport = httpx.ASGITransport(app=app, client=("198.51.100.7", 1))
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/costly", headers={"X-Request-ID": "concurrency-test"})

        assert response.status_code == 503
        assert response.json()["detail"]["code"] == "busy"
        assert response.headers["retry-after"] == "1"
        assert response.headers["x-request-id"] == "concurrency-test"

    asyncio.run(scenario())


def test_settings_define_positive_limits_for_each_high_cost_pool():
    from config import Settings

    settings = Settings(_env_file=None)
    assert settings.upload_concurrency_limit > 0
    assert settings.document_processing_concurrency_limit > 0
    assert settings.index_rebuild_concurrency_limit > 0
    assert settings.server_llm_concurrency_limit > 0
    assert settings.audio_transcription_concurrency_limit > 0
    assert settings.retrieval_concurrency_limit > 0
    assert settings.high_cost_acquire_timeout_seconds > 0


@pytest.mark.parametrize(
    "field",
    [
        "upload_concurrency_limit",
        "document_processing_concurrency_limit",
        "index_rebuild_concurrency_limit",
        "server_llm_concurrency_limit",
        "audio_transcription_concurrency_limit",
        "retrieval_concurrency_limit",
        "high_cost_acquire_timeout_seconds",
    ],
)
def test_high_cost_limits_reject_zero(field):
    from config import Settings
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        Settings(_env_file=None, **{field: 0})


def test_real_api_routes_declare_expensive_operation_permits():
    from api import app
    from src.services.concurrency import HighCostCapability

    expected = {
        "/query": HighCostCapability.SERVER_LLM,
        "/query/stream": HighCostCapability.SERVER_LLM,
        "/media/upload": HighCostCapability.UPLOAD,
        "/documents/upload": HighCostCapability.UPLOAD,
        "/search/image": HighCostCapability.RETRIEVAL,
        "/search/similar": HighCostCapability.RETRIEVAL,
        "/search/audio": HighCostCapability.RETRIEVAL,
        "/search/ai": HighCostCapability.RETRIEVAL,
        "/knowledge/rebuild-embeddings": HighCostCapability.INDEX_REBUILD,
        "/search/index-images": HighCostCapability.INDEX_REBUILD,
        "/search/audio/index": HighCostCapability.INDEX_REBUILD,
    }
    for path, capability in expected.items():
        route = next(route for route in app.routes if getattr(route, "path", None) == path)
        assert any(
            getattr(dependency.call, "concurrency_capability", None) == capability
            for dependency in route.dependant.dependencies
        )


def test_upload_worker_dispatches_document_audio_and_index_jobs_through_distinct_permits(monkeypatch):
    import src.workers.upload_worker as worker
    from src.services.concurrency import HighCostCapability

    class Recorder:
        def __init__(self):
            self.capabilities = []

        def permit(self, capability):
            recorder = self

            class Context:
                async def __aenter__(self):
                    recorder.capabilities.append(capability)

                async def __aexit__(self, exc_type, exc, traceback):
                    return False

            return Context()

    async def scenario():
        recorder = Recorder()
        monkeypatch.setattr(worker, "get_concurrency_limiter", lambda: recorder)

        async def document(_):
            return "document"

        async def audio(_):
            return "audio"

        async def index(_):
            return "index"

        monkeypatch.setattr("src.workers.processors.process_document_job", document)
        monkeypatch.setattr(worker, "process_audio_job", audio)
        monkeypatch.setattr("src.services.maintenance_jobs.process_maintenance_job", index)

        assert await worker._dispatch("document", 1) == "document"
        assert await worker._dispatch("audio", 2) == "audio"
        assert await worker._dispatch("knowledge_index", 3) == "index"
        assert recorder.capabilities == [
            HighCostCapability.DOCUMENT_PROCESSING,
            HighCostCapability.AUDIO_TRANSCRIPTION,
            HighCostCapability.INDEX_REBUILD,
        ]

    asyncio.run(scenario())
