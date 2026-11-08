"""Request-scoped LLM overrides must remain isolated when synchronous work uses threads."""

import asyncio
import threading


def test_llm_request_overrides_do_not_cross_contaminate_to_thread_calls():
    from src.utils.llm import clear_request_override, set_request_override, _get_request_override

    barrier = threading.Barrier(2)

    def read_after_both_requests_arrive():
        barrier.wait(timeout=1)
        return _get_request_override()["api_key"]

    async def one_request(key: str) -> str:
        set_request_override(api_key=key)
        try:
            return await asyncio.to_thread(read_after_both_requests_arrive)
        finally:
            clear_request_override()

    async def scenario():
        first, second = await asyncio.gather(one_request("key-a"), one_request("key-b"))
        assert {first, second} == {"key-a", "key-b"}

    asyncio.run(scenario())
