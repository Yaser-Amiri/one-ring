import sys
import asyncio
from asyncio import AbstractEventLoop
from typing import Optional


def run_main(main_coro):
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main_coro)
    except KeyboardInterrupt:
        pass
    finally:
        loop.close()


def get_current_task(loop: Optional[AbstractEventLoop] = None) -> asyncio.Task:
    if sys.version_info.major != 3:
        raise Exception("WTF?! this lib is designed for Python3")

    if sys.version_info.minor <= 7:
        return asyncio.Task.current_task(loop=loop)
    return asyncio.current_task(loop=loop)
