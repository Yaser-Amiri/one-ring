import asyncio


def run_main(main_coro):
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main_coro)
    except KeyboardInterrupt:
        pass
    finally:
        loop.close()
