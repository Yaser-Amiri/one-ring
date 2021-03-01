import collections
from random import shuffle
from typing import (
    Tuple,
    NamedTuple,
    Optional,
    Any,
    Callable,
    Awaitable,
    Union,
    Deque,
)
import asyncio
from enum import Enum

SendNoneToChannelError = ValueError("you can not send None to a channel")


class SelectAction(str, Enum):
    SEND = "S"
    RECEIVE = "R"


class SendAction(NamedTuple):
    channel: "Channel"
    callback: Optional[Callable[["Channel", Any], Awaitable[Any]]]
    item: Any


class ReceiveAction(NamedTuple):
    channel: "Channel"
    callback: Optional[Callable[["Channel", Any], Awaitable[Any]]]


Selectable = Union[ReceiveAction, SendAction]


class Channel:
    def __init__(
        self,
        maxsize: int = 0,
        loop: Optional[asyncio.AbstractEventLoop] = None,
    ) -> None:
        if loop is None:
            self._loop = asyncio.get_event_loop()

        if maxsize < 0:
            raise ValueError("maxsize of channel can not be a negative number")
        self._maxsize = maxsize

        self._receivers: Deque[asyncio.Future] = collections.deque()
        self._senders: Deque[asyncio.Future] = collections.deque()
        self._data: Deque[Any] = collections.deque()
        self._closed_flag: bool = False

    def __repr__(self) -> str:
        return f"<{type(self).__name__} at {id(self):#x} {self._format()}>"

    def __str__(self) -> str:
        return f"<{type(self).__name__} {self._format()}>"

    def __class_getitem__(cls, type):
        return cls

    def _format(self) -> str:
        result = f"maxsize={self._maxsize!r}"
        if getattr(self, "_data", None):
            result += f" _data={list(self._data)!r}"
        if self._receivers:
            result += f" _receivers[{len(self._receivers)}]"
        if self._senders:
            result += f" _senders[{len(self._senders)}]"
        return result

    def _get(self) -> Any:
        return self._data.popleft()

    def _put(self, item: Any) -> None:
        self._data.append(item)

    def _wakeup_next(self, waiters) -> None:
        # Wake up the next waiter (if any) that isn't cancelled.
        while waiters:
            waiter = waiters.popleft()
            if not waiter.done():
                waiter.set_result(None)
                break

    def size(self) -> int:
        """Number of items in channel."""
        return len(self._data)

    @property
    def maxsize(self) -> int:
        """Number of items allowed in the channel."""
        return self._maxsize

    def empty(self) -> bool:
        """Return True if the channel is empty, False otherwise."""
        return not self._data

    def full(self) -> bool:
        """Return True if there are maxsize items in the channel."""
        if self._maxsize <= 0:
            return self.size() > 0
        return self.size() >= self._maxsize

    def close(self) -> None:
        "Closes the channel"
        if self._closed_flag is True:
            return
        self._closed_flag = True
        while self._senders:
            sender = self._senders.popleft()
            if not sender.done():
                sender.set_result((self, None))
        if self.size() == 0:
            while self._receivers:
                receiver = self._receivers.popleft()
                if not receiver.done():
                    receiver.set_result((self, None))

    def is_closed(self) -> bool:
        return self._closed_flag

    def _move_data(self) -> bool:
        if self.empty() and self.is_closed():
            while self._receivers:
                receiver = self._receivers.popleft()
                if not receiver.done():
                    receiver.set_result((self, None))
            return False
        if self.empty() or not self._receivers:
            return False
        while self._receivers:
            receiver = self._receivers.popleft()
            if not receiver.done():
                receiver.set_result((self, self._get()))
                break
        self._wakeup_next(self._senders)
        return True

    def _can_send(self) -> bool:
        if self.is_closed():
            return False
        if self.full():
            return False
        if self._maxsize == 0:
            return any((not i.done() for i in self._receivers))
        return True

    async def send(
        self, item: Any, future: Optional[asyncio.Future] = None
    ) -> bool:
        if item is None:
            raise SendNoneToChannelError
        while not self._can_send():
            sender = self._loop.create_future()
            if future is not None and future.done():
                sender.cancel()
                return False
            if self.is_closed():
                sender.cancel()
                if future is not None:
                    future.set_result((self, None))
                return False
            self._senders.append(sender)
            try:
                await sender
            except Exception:
                sender.cancel()  # Just in case sender is not done yet.
                try:
                    # Clean self._senders from canceled producers.
                    self._senders.remove(sender)
                except ValueError:
                    # TODO: check
                    # The sender could be removed from self._senders by a
                    # previous get_nowait call.
                    pass
                if not self._can_send() and not sender.cancelled():
                    # TODO: check
                    # We were woken up by get_nowait(), but can't take
                    # the call. Wake up the next in line.
                    self._wakeup_next(self._senders)
                raise

        if future is not None and future.done():
            return False
        is_done = self.send_nowait(item)
        if future is not None:
            future.set_result((self, item))
        return is_done

    def send_nowait(self, item: Any) -> bool:
        if item is None:
            raise SendNoneToChannelError
        if not self._can_send():
            return False
        self._put(item)
        self._move_data()
        return True

    def add_future_to_receivers(self, f: asyncio.Future) -> None:
        self._receivers.append(f)
        if (
            not self._move_data()
            and self.empty()
            and self._maxsize == 0
            and self._senders
        ):
            self._wakeup_next(self._senders)

    def remove_future_from_receivers(self, f: asyncio.Future) -> None:
        try:
            self._receivers.remove(f)
        except ValueError as e:
            if "deque.remove(x): x not in deque" in str(e):
                pass

    async def receive(self, future: Optional[asyncio.Future] = None) -> Any:
        receiver = self._loop.create_future()
        self.add_future_to_receivers(receiver)
        await receiver
        self.remove_future_from_receivers(receiver)
        _, result = receiver.result()
        if future is not None:
            future.set_result(result)
        return result

    def receive_nowait(self) -> Any:
        if self.empty():
            return None
        return self._get()

    def R(
        self,
        callback: Optional[Callable[["Channel", Any], Awaitable[Any]]] = None,
    ) -> ReceiveAction:
        return ReceiveAction(channel=self, callback=callback)

    def S(
        self,
        item: Any,
        callback: Optional[Callable[["Channel", Any], Awaitable[Any]]] = None,
    ) -> SendAction:
        return SendAction(channel=self, item=item, callback=callback)


def select_nowait(
    *select_actions: Selectable,
) -> Tuple[Optional[Channel], Any]:
    for sa in select_actions:
        if isinstance(sa, SendAction) and sa.item is None:
            raise SendNoneToChannelError

    select_actions_list = list(select_actions)
    shuffle(select_actions_list)

    for sa in select_actions_list:
        channel, callback = sa.channel, sa.callback
        if isinstance(sa, SendAction):
            is_done = True if channel.send_nowait(sa.item) else False
            item = sa.item
        else:
            item = channel.receive_nowait()
            is_done = False if item is None else True

        if is_done:
            if callback is not None:
                callback(channel, item)  # TODO
            return channel, item
    return None, None


async def select(*select_actions: Selectable) -> Tuple[Channel, Any]:
    for sa in select_actions:
        if isinstance(sa, SendAction) and sa.item is None:
            raise SendNoneToChannelError

    loop = asyncio.get_event_loop()
    future = loop.create_future()
    channel_set = []
    callback_set = []
    send_tasks = []
    for sa in select_actions:
        channel, callback = sa.channel, sa.callback
        channel_set.append(channel)
        callback_set.append(callback)
        if isinstance(sa, SendAction):
            send_tasks.append(loop.create_task(channel.send(sa.item, future)))
        else:
            channel.add_future_to_receivers(future)

    await future

    for sa in select_actions:
        channel, callback = sa.channel, sa.callback
        if isinstance(sa, ReceiveAction):
            channel.remove_future_from_receivers(future)
    for t in send_tasks:
        t.cancel()

    ch, result = future.result()
    callback = callback_set[channel_set.index(ch)]
    if callback is not None:
        await callback(channel, result)
    return ch, result


def Timeout(
    delay: float, loop: Optional[asyncio.AbstractEventLoop] = None
) -> Channel:
    if loop is None:
        loop = asyncio.get_event_loop()

    def push(channel, item):
        channel.send_nowait(item)
        channel.close()

    channel = Channel(maxsize=1)
    loop.call_later(delay, push, channel, 0)
    return channel
