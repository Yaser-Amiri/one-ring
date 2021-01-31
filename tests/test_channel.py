import asyncio
import collections
from unittest.mock import Mock
import pytest

from one_ring import Channel


def run_concurrent(corotine, loop):
    async def m(corotine, result_q):
        result = await corotine
        await result_q.put(result)

    q = asyncio.Queue(maxsize=1)
    loop.create_task(m(corotine, q))
    return q


def test_channel_maxsize_values():
    Channel(maxsize=0)  # OK
    Channel(maxsize=1)  # OK
    with pytest.raises(ValueError):
        Channel(maxsize=-1)


@pytest.mark.asyncio
async def test_channel_empty(event_loop):
    assert Channel(maxsize=0).empty()
    assert Channel(maxsize=1).empty()

    unbuffered_channel = Channel(maxsize=0)
    task = event_loop.create_task(unbuffered_channel.send(1))
    assert unbuffered_channel.empty()
    task.cancel()

    buffered_channel = Channel(maxsize=1)
    await event_loop.create_task(buffered_channel.send(1))
    assert not buffered_channel.empty()


@pytest.mark.asyncio
async def test_channel_full(event_loop):
    assert not Channel(maxsize=0).full()
    assert not Channel(maxsize=1).full()

    unbuffered_channel = Channel(maxsize=0)
    task = event_loop.create_task(unbuffered_channel.send(1))
    assert not unbuffered_channel.full()
    task.cancel()

    # complete full
    c = 3
    buffered_channel = Channel(maxsize=3)
    for _ in range(c):
        await event_loop.create_task(buffered_channel.send(1))
    assert buffered_channel.full()

    # half full
    c = 4
    buffered_channel = Channel(maxsize=3)
    for _ in range(int(c / 2)):
        await event_loop.create_task(buffered_channel.send(1))
    assert not buffered_channel.full()


@pytest.mark.asyncio
async def test_can_send_in_channel(event_loop):
    # can not send an item on unbuffered channel with no listeners
    assert not Channel(maxsize=0)._can_send()

    # can not send an item on full channel
    channel = Channel(maxsize=1)
    channel.full = Mock()
    channel.return_value = True
    assert not channel._can_send()

    # can send an item on unbuffered channel with listeners
    unbuffered_channel = Channel(maxsize=0)
    assert not unbuffered_channel.full()
    unbuffered_channel._receivers.append(event_loop.create_future())
    assert unbuffered_channel._can_send()


@pytest.mark.asyncio
async def test_can_send_on_closed_channel(event_loop):

    # buffered channel with no receivers
    channel = Channel(maxsize=1)
    channel.close()
    assert not channel._can_send()
    assert channel.send_nowait(1) is False
    assert channel.size() == 0
    assert await channel.send(1) is False
    assert channel.size() == 0

    # unbuffered channel with no receivers
    unbuffered_channel = Channel(maxsize=0)
    unbuffered_channel.close()
    assert not unbuffered_channel._can_send()
    assert unbuffered_channel.send_nowait(1) is False
    assert unbuffered_channel.size() == 0
    assert not await unbuffered_channel.send(1)
    assert unbuffered_channel.size() == 0

    # buffered channel, with receiver, closed after attaching receiver
    channel_with_receiver = Channel(maxsize=1)
    channel_with_receiver._receivers.append(event_loop.create_future())
    channel_with_receiver.close()
    assert not channel_with_receiver._can_send()
    assert channel_with_receiver.send_nowait(1) is False
    assert channel_with_receiver.size() == 0
    assert not await channel_with_receiver.send(1)
    assert channel_with_receiver.size() == 0

    # buffered channel, with receiver, closed after attaching receiver
    unbuffered_channel_with_receiver = Channel(maxsize=0)
    unbuffered_channel_with_receiver._receivers.append(
        event_loop.create_future()
    )
    unbuffered_channel_with_receiver.close()
    assert not unbuffered_channel_with_receiver._can_send()
    assert unbuffered_channel_with_receiver.send_nowait(1) is False
    assert unbuffered_channel_with_receiver.size() == 0
    assert not await unbuffered_channel_with_receiver.send(1)
    assert unbuffered_channel_with_receiver.size() == 0

    # buffered channel, with receiver, closed before attaching receiver
    channel_with_receiver = Channel(maxsize=1)
    channel_with_receiver.close()
    channel_with_receiver._receivers.append(event_loop.create_future())
    assert not channel_with_receiver._can_send()
    assert channel_with_receiver.send_nowait(1) is False
    assert channel_with_receiver.size() == 0
    assert not await channel_with_receiver.send(1)
    assert channel_with_receiver.size() == 0

    # unbuffered channel, with receiver, closed before attaching receiver
    unbuffered_channel_with_receiver = Channel(maxsize=0)
    unbuffered_channel_with_receiver.close()
    unbuffered_channel_with_receiver._receivers.append(
        event_loop.create_future()
    )
    assert not unbuffered_channel_with_receiver._can_send()
    assert unbuffered_channel_with_receiver.size() == 0
    assert unbuffered_channel_with_receiver.send_nowait(1) is False
    assert not await unbuffered_channel_with_receiver.send(1)
    assert unbuffered_channel_with_receiver.size() == 0

    # full channel
    full_channel = Channel(maxsize=1)
    assert full_channel.send_nowait(1)
    q = run_concurrent(full_channel.send(1), event_loop)
    assert full_channel.size() == 1
    full_channel.close()
    assert await q.get() is False


@pytest.mark.asyncio
async def test_receive_on_closed_channel(event_loop):
    # buffered channel with no senders
    channel = Channel(maxsize=1)
    channel.close()
    assert channel.receive_nowait() is None
    assert channel.size() == 0

    # unbuffered channel with no senders
    unbuffered_channel = Channel(maxsize=0)
    unbuffered_channel.close()
    assert unbuffered_channel.receive_nowait() is None
    assert unbuffered_channel.size() == 0

    # full channel, closed after sending data, receive with no wait
    channel_with_data = Channel(maxsize=1)
    assert channel_with_data.send_nowait(1)
    channel_with_data.close()
    assert channel_with_data.receive_nowait() == 1
    assert channel_with_data.receive_nowait() is None
    assert channel_with_data.receive_nowait() is None

    # full channel, closed after sending data, receive blocking
    channel_with_data = Channel(maxsize=1)
    assert channel_with_data.send_nowait(1)
    channel_with_data.close()
    assert await channel_with_data.receive() == 1
    assert await channel_with_data.receive() is None
    assert await channel_with_data.receive() is None

    # empty channel, closed attaching receiver, receive blocking
    channel_with_data = Channel(maxsize=1)
    q = run_concurrent(channel_with_data.receive(), event_loop)
    channel_with_data.close()
    assert await q.get() is None


@pytest.mark.asyncio
async def test_wakeup_next_of_channel(event_loop):
    waiters = collections.deque()
    c = Channel()
    c._wakeup_next(waiters)  # no exception


@pytest.mark.asyncio
async def test_wakeup_next_of_channel_on_all_pending_items(event_loop):
    waiters = collections.deque()
    c = Channel()
    future_count = 3
    waiters = collections.deque()
    future_set = [event_loop.create_future() for _ in range(future_count)]
    for f in future_set:
        waiters.append(f)
    c._wakeup_next(waiters)
    assert len(waiters) == future_count - 1
    assert len(tuple(filter(lambda x: x.done(), future_set))) == 1


@pytest.mark.asyncio
async def test_wakeup_next_of_channel_on_half_pending_items(event_loop):
    waiters = collections.deque()
    c = Channel()
    future_count = 6
    done_count = 2
    waiters = collections.deque()
    future_set = [event_loop.create_future() for _ in range(future_count)]
    for f in future_set[:done_count]:
        f.set_result(None)
    for f in future_set:
        waiters.append(f)

    c._wakeup_next(waiters)
    assert len(waiters) == future_count - done_count - 1
    assert len(tuple(filter(lambda x: x.done(), future_set))) == done_count + 1


@pytest.mark.asyncio
async def test_multiple_close_of_channel(event_loop):
    c = Channel()
    assert c.close() is None
    assert c.close() is None
    assert c.close() is None


@pytest.mark.asyncio
async def test_deattaching_senders_after_closing_channel(event_loop):
    c = Channel()
    sender_count = 3
    sender_tasks = [
        event_loop.create_task(c.send(1)) for _ in range(sender_count)
    ]
    # give a chance to writers to register themselves on channel senders
    await asyncio.sleep(0.01)
    assert len(c._senders) == sender_count
    assert all([not f.done() for f in c._senders])

    assert c.close() is None
    assert len(c._senders) == 0
    assert c.is_closed()

    for t in sender_tasks:
        t.cancel()


@pytest.mark.asyncio
async def test_deattaching_receivers_after_closing_channel(event_loop):
    c = Channel()
    receiver_count = 3
    receiver_tasks = [
        event_loop.create_task(c.receive()) for _ in range(receiver_count)
    ]
    # give a chance to writers to register themselves on channel receivers
    await asyncio.sleep(0.01)
    assert len(c._receivers) == receiver_count
    assert all([not f.done() for f in c._receivers])

    assert c.close() is None
    assert len(c._receivers) == 0
    assert c.is_closed()

    for t in receiver_tasks:
        t.cancel()


@pytest.mark.asyncio
async def test_sending_none_to_channel(event_loop):
    unbuffered_channel = Channel()
    with pytest.raises(ValueError) as excinfo:
        unbuffered_channel.send_nowait(None)
    assert "you can not send None to a channel" in str(excinfo)

    with pytest.raises(ValueError) as excinfo:
        await unbuffered_channel.send(None)
    assert "you can not send None to a channel" in str(excinfo)

    buffered_channel = Channel(maxsize=10)
    with pytest.raises(ValueError) as excinfo:
        buffered_channel.send_nowait(None)
    assert "you can not send None to a channel" in str(excinfo)

    with pytest.raises(ValueError) as excinfo:
        await buffered_channel.send(None)
    assert "you can not send None to a channel" in str(excinfo)
