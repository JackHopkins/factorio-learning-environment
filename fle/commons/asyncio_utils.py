import asyncio
import concurrent.futures


def _run_async_in_new_thread(coro):
    """Run an async coroutine in a new thread with its own event loop"""

    def run_in_thread():
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)
        try:
            return new_loop.run_until_complete(coro)
        finally:
            new_loop.close()
            asyncio.set_event_loop(None)

    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(run_in_thread)
        return future.result()


def run_async_safely(coro):
    """Run an async coroutine safely, handling both cases where event loop exists or not"""
    try:
        # Check if we're already in a running event loop
        asyncio.get_running_loop()
        # If we get here, there's a running loop, so use thread approach
        return _run_async_in_new_thread(coro)
    except RuntimeError:
        # No running event loop, safe to use asyncio.run()
        return asyncio.run(coro)
