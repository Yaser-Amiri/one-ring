import asyncio
from random import randint
from uuid import uuid4
import pytest

from one_ring import Channel, select


async def nop(count=1):
    for _ in range(count):
        await asyncio.sleep(0.05)


async def channel_writer(channel, item, sleep_time):
    _id = str(uuid4())
    print(
        "channel writer started | id: %s | ch: %s | item: %s | sleep: %s"
        % (_id, channel, item, sleep_time)
    )
    await asyncio.sleep(sleep_time)
    print(
        "channel writer woke up | id: %s | ch: %s | item: %s | sleep: %s"
        % (_id, channel, item, sleep_time)
    )
    await channel.send(item)
    print(
        "channel writer ended | id: %s | ch: %s | item: %s | sleep: %s"
        % (_id, channel, item, sleep_time)
    )


async def channel_reader(channel, sleep_time):
    _id = str(uuid4())
    print(
        "channel reader started | id: %s | ch: %s | sleep: %s"
        % (_id, channel, sleep_time)
    )
    await asyncio.sleep(sleep_time)
    print(
        "channel reader woke up | id: %s | ch: %s | sleep: %s"
        % (_id, channel, sleep_time)
    )
    item = await channel.receive()
    print(
        "channel reader ended | id: %s | ch: %s | item: %s | sleep: %s"
        % (_id, channel, item, sleep_time)
    )


@pytest.mark.asyncio
async def test_unbuffered_channels_select_receive_before_send(event_loop):
    """
    Make some unbuffered channels,
    create an idle writer for each channel,
    select for reading on channels,
    writers try to sending data,
    test that it works fine.
    """
    select_count = 2
    channel_count = 5
    if channel_count < select_count:
        assert "This is going to hell! channel select count must be greater "
        "than channel count"

    callback_run_count = 0

    async def callback(ch, res):
        print("callback got: %s " % res)
        nonlocal callback_run_count
        callback_run_count += 1
        return ch, res

    channel_set = [Channel() for _ in range(channel_count)]
    tasks = []
    select_ran_count = 0
    try:
        for c in channel_set:
            t = event_loop.create_task(channel_writer(c, randint(1, 25), 2))
            tasks.append(t)
        for _ in range(select_count):
            ch, result = await select(*[ch.R(callback) for ch in channel_set])
            assert ch in channel_set
            assert result is not None
            select_ran_count += 1
    finally:
        for t in tasks:
            if not t.done():
                t.cancel()

    assert callback_run_count == select_ran_count == select_count

    waiting_senders = 0
    for c in channel_set:
        assert c.size() == 0  # there is nothing in channels
        for p in c._senders:
            if p.done():
                assert "There is a done sender in channel"
            waiting_senders += 1

    # counting waiting writers
    assert waiting_senders == channel_count - select_ran_count


@pytest.mark.asyncio
async def test_buffered_channels_select_receive_before_send(event_loop):
    """
    Make some buffered channels,
    create an idle writer for each channel,
    select for reading on channels,
    writers try to sending data,
    test that it works fine.
    """
    select_count = 2
    channel_count = 5
    if channel_count < select_count:
        assert "This is going to hell! channel select count must be greater "
        "than channel count"

    callback_run_count = 0

    async def callback(ch, res):
        print("callback got: %s " % res)
        nonlocal callback_run_count
        callback_run_count += 1
        return ch, res

    channel_set = [Channel(maxsize=1) for _ in range(channel_count)]
    tasks = []
    select_ran_count = 0
    try:
        for c in channel_set:
            t = event_loop.create_task(channel_writer(c, randint(1, 25), 2))
            tasks.append(t)
        for _ in range(select_count):
            ch, result = await select(*[ch.R(callback) for ch in channel_set])
            assert ch in channel_set
            assert result is not None
            select_ran_count += 1
    finally:
        for t in tasks:
            if not t.done():
                t.cancel()

    assert callback_run_count == select_ran_count == select_count

    waiting_senders = 0
    channel_queue_sizes = []
    for c in channel_set:
        channel_queue_sizes.append(c.size())
        for p in c._senders:
            if p.done():
                assert "There is a done sender in channel"
            waiting_senders += 1

    assert channel_queue_sizes.count(1) == channel_count - select_count
    assert channel_queue_sizes.count(0) == select_count
    assert waiting_senders == 0


@pytest.mark.asyncio
async def test_unbuffered_channels_select_receive_after_send(event_loop):
    """
    Make some unbuffered channels,
    create an writer for each channel,
    wait for writers to start sending data,
    select for reading on channels,
    test that it works fine.
    """
    select_count = 2
    channel_count = 5
    if channel_count < select_count:
        assert "This is going to hell! channel select count must be greater "
        "than channel count"

    callback_run_count = 0

    async def callback(ch, res):
        print("callback got: %s " % res)
        nonlocal callback_run_count
        callback_run_count += 1
        return ch, res

    channel_set = [Channel() for _ in range(channel_count)]
    tasks = []
    select_ran_count = 0
    try:
        for c in channel_set:
            t = event_loop.create_task(channel_writer(c, randint(1, 25), 0.5))
            tasks.append(t)
        await asyncio.sleep(1.5)
        await asyncio.sleep(0.01)
        for _ in range(select_count):
            ch, result = await select(*[ch.R(callback) for ch in channel_set])
            assert ch in channel_set
            assert result is not None
            select_ran_count += 1
    finally:
        for t in tasks:
            if not t.done():
                t.cancel()

    assert callback_run_count == select_ran_count == select_count

    waiting_senders = 0
    for c in channel_set:
        assert c.size() == 0  # there is nothing in channels
        for p in c._senders:
            if p.done():
                assert "There is a done sender in channel"
            waiting_senders += 1

    # counting waiting writers
    assert waiting_senders == channel_count - select_ran_count


@pytest.mark.asyncio
async def test_buffered_channels_select_receive_after_send(event_loop):
    """
    Make some buffered channels,
    create an writer for each channel,
    wait for writers to start sending data,
    select for reading on channels,
    test that it works fine.
    """
    select_count = 2
    channel_count = 5
    if channel_count < select_count:
        assert "This is going to hell! channel select count must be greater "
        "than channel count"

    callback_run_count = 0

    async def callback(ch, res):
        print("callback got: %s " % res)
        nonlocal callback_run_count
        callback_run_count += 1
        return ch, res

    channel_set = [Channel(maxsize=1) for _ in range(channel_count)]
    tasks = []
    select_ran_count = 0
    try:
        for c in channel_set:
            t = event_loop.create_task(channel_writer(c, randint(1, 25), 0.5))
            tasks.append(t)
        await asyncio.sleep(2)
        for _ in range(select_count):
            ch, result = await select(*[ch.R(callback) for ch in channel_set])
            assert ch in channel_set
            assert result is not None
            select_ran_count += 1
    finally:
        for t in tasks:
            if not t.done():
                t.cancel()

    assert callback_run_count == select_ran_count == select_count

    waiting_senders = 0
    channel_queue_sizes = []
    for c in channel_set:
        channel_queue_sizes.append(c.size())
        for p in c._senders:
            if p.done():
                assert "There is a done sender in channel"
            waiting_senders += 1

    assert channel_queue_sizes.count(1) == channel_count - select_count
    assert channel_queue_sizes.count(0) == select_count
    assert waiting_senders == 0


@pytest.mark.asyncio
async def test_unbuffered_channels_select_send_before_receive(event_loop):
    """
    Make some unbuffered channels,
    create an idle reader for each channel,
    select for writing on channels,
    readers try to receive data,
    test that it works fine.
    """
    select_count = 2
    channel_count = 5
    if channel_count < select_count:
        assert "This is going to hell! channel select count must be greater "
        "than channel count"

    callback_run_count = 0

    async def callback(ch, res):
        print("callback got: %s " % res)
        nonlocal callback_run_count
        callback_run_count += 1
        return ch, res

    channel_set = [Channel() for _ in range(channel_count)]
    tasks = []
    select_ran_count = 0
    try:
        for c in channel_set:
            t = event_loop.create_task(channel_reader(c, 2))
            tasks.append(t)
        for _ in range(select_count):
            ch, result = await select(
                *[ch.S(randint(1, 25), callback) for ch in channel_set]
            )
            assert ch in channel_set
            assert result is not None
            select_ran_count += 1
    finally:
        for t in tasks:
            if not t.done():
                t.cancel()

    assert callback_run_count == select_ran_count == select_count

    waiting_receivers = 0
    for c in channel_set:
        assert c.size() == 0  # there is nothing in channels
        for p in c._receivers:
            if p.done():
                assert "There is a done sender in channel"
            waiting_receivers += 1

    # counting waiting readers
    assert waiting_receivers == channel_count - select_ran_count


@pytest.mark.asyncio
async def test_buffered_channels_select_send_before_receive(event_loop):
    """
    Make some buffered channels,
    select for writing on channels (they write immediately),
    test that it works fine.
    """
    channel_count = select_count = 5
    if channel_count < select_count:
        assert "This is going to hell! channel select count must be greater "
        "than channel count"

    callback_run_count = 0

    async def callback(ch, res):
        print("callback got: %s " % res)
        nonlocal callback_run_count
        callback_run_count += 1
        return ch, res

    channel_set = [Channel(maxsize=1) for _ in range(channel_count)]
    select_ran_count = 0
    for _ in range(select_count):
        ch, result = await select(
            *[ch.S(randint(1, 25), callback) for ch in channel_set]
        )
        assert ch in channel_set
        assert result is not None
        select_ran_count += 1

    assert callback_run_count == select_ran_count == select_count

    channel_queue_sizes = []
    for c in channel_set:
        channel_queue_sizes.append(c.size())

    assert channel_queue_sizes.count(1) == select_count
    assert channel_queue_sizes.count(0) == channel_count - select_count


@pytest.mark.asyncio
async def test_unbuffered_channels_select_send_after_receive(event_loop):
    """
    Make some unbuffered channels,
    create an reader for each channel,
    wait for readers to start receiveing data,
    select for writing on channels,
    test that it works fine.
    """
    select_count = 2
    channel_count = 5
    if channel_count < select_count:
        assert "This is going to hell! channel select count must be greater "
        "than channel count"

    callback_run_count = 0

    async def callback(ch, res):
        print("callback got: %s " % res)
        nonlocal callback_run_count
        callback_run_count += 1
        return ch, res

    channel_set = [Channel() for _ in range(channel_count)]
    tasks = []
    select_ran_count = 0
    try:
        for c in channel_set:
            t = event_loop.create_task(channel_reader(c, 0.5))
            tasks.append(t)
        await asyncio.sleep(1.5)
        await asyncio.sleep(0.01)
        for _ in range(select_count):
            ch, result = await select(
                *[ch.S(randint(1, 25), callback) for ch in channel_set]
            )
            assert ch in channel_set
            assert result is not None
            select_ran_count += 1
    finally:
        for t in tasks:
            if not t.done():
                t.cancel()

    assert callback_run_count == select_ran_count == select_count

    waiting_receivers = 0
    for c in channel_set:
        assert c.size() == 0  # there is nothing in channels
        for p in c._receivers:
            if p.done():
                assert "There is a done receiver in channel"
            waiting_receivers += 1

    # counting waiting writers
    assert waiting_receivers == channel_count - select_ran_count


@pytest.mark.asyncio
async def test_buffered_channels_select_send_after_receive(event_loop):
    """
    Make some buffered channels,
    create a reader for each channel,
    wait for readers to start receiving data,
    select for writing on channels,
    test that it works fine.
    """
    select_count = 2
    channel_count = 5
    if channel_count < select_count:
        assert "This is going to hell! channel select count must be greater "
        "than channel count"

    callback_run_count = 0

    async def callback(ch, res):
        print("callback got: %s " % res)
        nonlocal callback_run_count
        callback_run_count += 1
        return ch, res

    channel_set = [Channel(maxsize=1) for _ in range(channel_count)]
    tasks = []
    select_ran_count = 0
    try:
        for c in channel_set:
            t = event_loop.create_task(channel_reader(c, 0.5))
            tasks.append(t)
        await asyncio.sleep(1.5)
        await asyncio.sleep(0.01)
        for _ in range(select_count):
            ch, result = await select(
                *[ch.S(randint(1, 25), callback) for ch in channel_set]
            )
            assert ch in channel_set
            assert result is not None
            select_ran_count += 1
    finally:
        for t in tasks:
            if not t.done():
                t.cancel()

    assert callback_run_count == select_ran_count == select_count

    for c in channel_set:
        for p in c._receivers:
            if p.done():
                assert "There is a done receiver in channel"


@pytest.mark.asyncio
async def test_multiple_receive_select_before_send_unbuffered(event_loop):
    """
    Make an unbuffered channels,
    create multiple coroutine and select in each (receive)
    write to the channel,
    test that it works fine.
    """
    select_count = 3
    callback_run_count = 0
    send_count = 2

    async def callback(ch, res):
        print("callback got: %s " % res)
        nonlocal callback_run_count
        callback_run_count += 1

    tasks = []
    ch = Channel()
    try:
        for c in range(select_count):
            t = event_loop.create_task(select(ch.R(callback)))
            tasks.append(t)
        await nop(10)
        for _ in range(send_count):
            await nop(3)
            await ch.send(1)
            await nop(3)
    finally:
        for t in tasks:
            if not t.done():
                t.cancel()

    assert callback_run_count == send_count

    waiting_receivers = 0
    assert ch.size() == 0  # there is nothing in channels
    for p in ch._receivers:
        if p.done():
            assert "There is a done sender in channel"
        waiting_receivers += 1

    # counting waiting writers
    assert waiting_receivers == select_count - callback_run_count


@pytest.mark.asyncio
async def test_multiple_receive_select_before_send_buffered(event_loop):
    """
    Make an buffered channels,
    create multiple coroutine and select in each (receive)
    write to the channel,
    test that it works fine.
    """
    select_count = 3
    callback_run_count = 0
    send_count = 2

    async def callback(ch, res):
        print("callback got: %s " % res)
        nonlocal callback_run_count
        callback_run_count += 1

    tasks = []
    ch = Channel(maxsize=1)
    try:
        for c in range(select_count):
            t = event_loop.create_task(select(ch.R(callback)))
            tasks.append(t)
        await nop(10)
        for _ in range(send_count):
            await nop(3)
            await ch.send(1)
            await nop(3)
    finally:
        for t in tasks:
            if not t.done():
                t.cancel()

    assert callback_run_count == send_count

    waiting_receivers = 0
    assert ch.size() == 0  # there is nothing in channels
    for p in ch._receivers:
        if p.done():
            assert "There is a done sender in channel"
        waiting_receivers += 1

    # counting waiting writers
    assert waiting_receivers == select_count - callback_run_count


@pytest.mark.asyncio
async def test_multiple_receive_select_full_channel(event_loop):
    """
    Make an unbuffered channels,
    create multiple coroutine and select in each (receive)
    write to the channel,
    test that it works fine.
    """
    select_count = 3
    callback_run_count = 0
    send_count = 1

    async def callback(ch, res):
        print("callback got: %s " % res)
        nonlocal callback_run_count
        callback_run_count += 1

    tasks = []
    ch = Channel(maxsize=1)
    ch.send_nowait(1)
    assert ch.full()
    try:
        for c in range(select_count):
            t = event_loop.create_task(select(ch.R(callback)))
            tasks.append(t)
        await nop(10)
    finally:
        for t in tasks:
            if not t.done():
                t.cancel()

    assert callback_run_count == send_count

    waiting_receivers = 0
    assert ch.size() == 0  # there is nothing in channels
    for p in ch._receivers:
        if p.done():
            assert "There is a done sender in channel"
        waiting_receivers += 1

    # counting waiting writers
    assert waiting_receivers == select_count - callback_run_count


@pytest.mark.asyncio
async def test_multiple_send_select_before_receive_unbuffered(event_loop):
    """
    Make an unbuffered channels,
    create multiple coroutine and select in each (send)
    receive from the channel,
    test that it works fine.
    """
    select_count = 3
    callback_run_count = 0
    receive_count = 2

    async def callback(ch, res):
        print("callback got: %s " % res)
        nonlocal callback_run_count
        callback_run_count += 1

    tasks = []
    ch = Channel()
    try:
        for c in range(select_count):
            t = event_loop.create_task(select(ch.S(1, callback)))
            tasks.append(t)
        await nop(10)
        for _ in range(receive_count):
            await nop(3)
            await ch.receive()
            await nop(3)
    finally:
        for t in tasks:
            if not t.done():
                t.cancel()

    assert callback_run_count == receive_count + ch.maxsize

    waiting_senders = 0
    assert ch.size() == 0  # there is nothing in channels
    for p in ch._senders:
        if p.done():
            assert "There is a done sender in channel"
        waiting_senders += 1

    # counting waiting writers
    assert waiting_senders == select_count - callback_run_count


@pytest.mark.asyncio
async def test_multiple_send_select_before_receive_buffered(event_loop):
    """
    Make an buffered channels,
    create multiple coroutine and select in each (send)
    receive from the channel,
    test that it works fine.
    """
    select_count = 3
    callback_run_count = 0
    receive_count = 2

    async def callback(ch, res):
        print("callback got: %s " % res)
        nonlocal callback_run_count
        callback_run_count += 1

    tasks = []
    ch = Channel(maxsize=1)
    try:
        for c in range(select_count):
            t = event_loop.create_task(select(ch.S(1, callback)))
            tasks.append(t)
        await nop(10)
        for _ in range(receive_count):
            await nop(3)
            await ch.receive()
            await nop(3)
    finally:
        for t in tasks:
            if not t.done():
                t.cancel()

    assert callback_run_count == receive_count + ch.maxsize

    waiting_senders = 0
    for p in ch._senders:
        if p.done():
            assert "There is a done sender in channel"
        waiting_senders += 1

    # counting waiting writers
    assert waiting_senders == select_count - callback_run_count


@pytest.mark.asyncio
async def test_sending_none_to_channel_on_select(event_loop):
    callback_run_count = 0

    async def callback(ch, res):
        print("callback got: %s " % res)
        nonlocal callback_run_count
        callback_run_count += 1
        return ch, res

    unbuffered_channel = Channel()
    with pytest.raises(ValueError) as excinfo:
        await select(unbuffered_channel.S(None, callback))
    assert "you can not send None to a channel" in str(excinfo)
    assert callback_run_count == 0
    assert len(unbuffered_channel._receivers) == 0
    assert len(unbuffered_channel._senders) == 0

    buffered_channel = Channel(maxsize=10)
    with pytest.raises(ValueError) as excinfo:
        await select(buffered_channel.S(None, callback))
    assert "you can not send None to a channel" in str(excinfo)
    assert callback_run_count == 0
    assert len(buffered_channel._receivers) == 0
    assert len(buffered_channel._senders) == 0


@pytest.mark.asyncio
async def test_select_combined_send_receive_on_buffered_channels(event_loop):
    """
    Make two buffered channels,
    select send and receive on each
    test that it works fine.
    """
    callback_run_count = 0

    async def callback(ch, res):
        print("callback got: %s " % res)
        nonlocal callback_run_count
        callback_run_count += 1
        return ch, res

    ch1 = Channel(maxsize=1)
    ch2 = Channel(maxsize=1)
    ch, result = await select(ch1.S(1, callback), ch2.R(callback))
    await nop(10)
    assert ch is ch1

    assert callback_run_count == 1
    assert len(tuple(filter(lambda x: not x.done(), ch1._senders))) == 0
    assert len(tuple(filter(lambda x: not x.done(), ch1._receivers))) == 0
    assert len(tuple(filter(lambda x: not x.done(), ch2._senders))) == 0
    assert len(tuple(filter(lambda x: not x.done(), ch2._receivers))) == 0


@pytest.mark.asyncio
async def test_select_combined_send_receive_on_unbuffered_channels(event_loop):
    """
    Make two unbuffered channels,
    create a receiver for one and a sender for another
    select send and receive on each
    test that it works fine.
    """
    callback_run_count = 0

    async def callback(ch, res):
        print("callback got: %s " % res)
        nonlocal callback_run_count
        callback_run_count += 1
        return ch, res

    ch1 = Channel()
    event_loop.create_task(ch1.receive())
    ch2 = Channel()
    event_loop.create_task(ch2.send(1))
    ch_r1, result = await select(ch1.S(1, callback), ch2.R(callback))
    await nop(10)
    ch_r2, result = await select(ch1.S(1, callback), ch2.R(callback))
    await nop(10)
    assert {ch_r2, ch_r1} == {ch1, ch2}

    assert callback_run_count == 2
    assert len(tuple(filter(lambda x: not x.done(), ch1._senders))) == 0
    assert len(tuple(filter(lambda x: not x.done(), ch1._receivers))) == 0
    assert len(tuple(filter(lambda x: not x.done(), ch2._senders))) == 0
    assert len(tuple(filter(lambda x: not x.done(), ch2._receivers))) == 0


@pytest.mark.asyncio
async def test_select_receive_on_closed_unbuffered_channels(event_loop):
    """
    Make some channels (unbuffered),
    close them,
    select for receiving,
    test that it works fine.
    """

    callback_run_count = 0

    async def callback(ch, res):
        print("callback got: %s " % res)
        nonlocal callback_run_count
        callback_run_count += 1
        return ch, res

    ch = Channel()
    ch.close()
    ch_r, result = await select(ch.R(callback))
    await nop(5)
    assert ch_r is ch
    assert result is None
    assert ch_r.is_closed()

    assert callback_run_count == 1
    assert len(tuple(filter(lambda x: not x.done(), ch._senders))) == 0
    assert len(tuple(filter(lambda x: not x.done(), ch._receivers))) == 0


@pytest.mark.asyncio
async def test_select_receive_on_closed_buffered_channels(event_loop):
    """
    Make some channels (buffered),
    close them,
    select for receiving,
    test that it works fine.
    """
    callback_run_count = 0

    async def callback(ch, res):
        print("callback got: %s " % res)
        nonlocal callback_run_count
        callback_run_count += 1
        return ch, res

    ch = Channel(maxsize=1)
    ch.close()
    ch_r, result = await select(ch.R(callback))
    await nop(5)
    assert ch_r is ch
    assert result is None
    assert ch_r.is_closed()

    assert callback_run_count == 1
    assert len(tuple(filter(lambda x: not x.done(), ch._senders))) == 0
    assert len(tuple(filter(lambda x: not x.done(), ch._receivers))) == 0

    full_ch = Channel(maxsize=1)
    await full_ch.send(1)
    assert full_ch.full()
    full_ch.close()

    full_ch_r, full_result = await select(full_ch.R(callback))
    await nop(5)
    assert full_ch_r is full_ch
    assert full_result == 1
    assert full_ch_r.is_closed()

    assert callback_run_count == 2
    assert len(tuple(filter(lambda x: not x.done(), full_ch._senders))) == 0
    assert len(tuple(filter(lambda x: not x.done(), full_ch._receivers))) == 0


@pytest.mark.asyncio
async def test_select_send_on_closed_unbuffered_channels(event_loop):
    """
    Make some channels (unbufferred),
    close them,
    select for sending,
    test that it works fine.
    """

    callback_run_count = 0

    async def callback(ch, res):
        print("callback got: %s " % res)
        nonlocal callback_run_count
        callback_run_count += 1
        return ch, res

    ch = Channel()
    ch.close()
    ch_r, result = await select(ch.S(1, callback))
    await nop(5)
    assert ch_r is ch
    assert result is None
    assert ch_r.is_closed()

    assert callback_run_count == 1
    assert len(tuple(filter(lambda x: not x.done(), ch._senders))) == 0
    assert len(tuple(filter(lambda x: not x.done(), ch._receivers))) == 0


@pytest.mark.asyncio
async def test_select_send_on_closed_buffered_channels(event_loop):
    """
    Make some channels (bufferred),
    close them,
    select for sending,
    test that it works fine.
    """

    callback_run_count = 0

    async def callback(ch, res):
        print("callback got: %s " % res)
        nonlocal callback_run_count
        callback_run_count += 1
        return ch, res

    ch = Channel(maxsize=1)
    ch.close()
    ch_r, result = await select(ch.S(1, callback))
    await nop(5)
    assert ch_r is ch
    assert result is None
    assert ch_r.is_closed()

    assert callback_run_count == 1
    assert len(tuple(filter(lambda x: not x.done(), ch._senders))) == 0
    assert len(tuple(filter(lambda x: not x.done(), ch._receivers))) == 0


@pytest.mark.asyncio
async def test_select_send_and_receive_on_closed_channels(event_loop):
    """
    Make some channels (unbufferred),
    close them,
    select for sending and receiving,
    test that it works fine.
    """

    callback_run_count = 0

    async def callback(ch, res):
        print("callback got: %s " % res)
        nonlocal callback_run_count
        callback_run_count += 1
        return ch, res

    ch1 = Channel()
    ch1.close()
    ch2 = Channel()
    ch2.close()
    ch_r, result = await select(ch1.S(1, callback), ch2.R(callback))
    await nop(5)
    assert ch_r in (ch1, ch2)
    assert result is None
    assert ch_r.is_closed()

    assert callback_run_count == 1
    assert len(tuple(filter(lambda x: not x.done(), ch1._senders))) == 0
    assert len(tuple(filter(lambda x: not x.done(), ch1._receivers))) == 0
    assert len(tuple(filter(lambda x: not x.done(), ch2._senders))) == 0
    assert len(tuple(filter(lambda x: not x.done(), ch2._receivers))) == 0
