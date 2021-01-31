import asyncio
from asyncio import AbstractEventLoop
from typing import Dict, Optional, Any, Awaitable
from enum import IntEnum


class ActionOnFailure(IntEnum):
    IGNORE_WITHOUT_RAISE = 0
    CANCALE_ALL_CHILDREN_WITHOUT_RAISE = 1
    IGNORE_AND_RAISE = 2
    CACALE_ALL_CHILDREN_AND_RAISE = 3


class NurseryChildFailure(Exception):
    pass


class Nursery(object):
    def __init__(
        self,
        on_failure: ActionOnFailure = ActionOnFailure.IGNORE_WITHOUT_RAISE,
        loop: Optional[AbstractEventLoop] = None,
    ):
        self.action_on_failure: ActionOnFailure = on_failure
        self.tasks: Dict[str, asyncio.Task] = {}
        self.exception: Dict[str, Any] = {}
        self._loop: AbstractEventLoop = loop or asyncio.get_event_loop()
        self.__task_number: int = 0

    def _inc_task_number(self) -> int:
        n = self.__task_number
        self.__task_number += 1
        return n

    def _generate_task_name(self) -> str:
        return "task-%s" % self._inc_task_number()

    def start(
        self, coro: Awaitable[Any], name: Optional[str] = None
    ) -> asyncio.Task:
        """Starts a tasks and binds it to the nursery"""
        if name is None:
            name = self._generate_task_name()
        if name in self.tasks:
            raise ValueError(
                "there is another task with the same name in this nursery.",
                {"name": name},
            )
        t = self._loop.create_task(coro)
        t.add_done_callback(self._task_done_hook)
        self.tasks[name] = t
        return t

    async def _wait_until_complete(self) -> None:
        await asyncio.wait(
            self.tasks.values(), return_when=asyncio.ALL_COMPLETED
        )

    def get_task_by_name(self, name: str) -> Optional[asyncio.Task]:
        return self.tasks.get(name, None)

    async def __aenter__(self) -> "Nursery":
        return self

    async def __aexit__(self, *exc_info) -> None:
        await self._wait_until_complete()
        if self.action_on_failure in (
            ActionOnFailure.IGNORE_WITHOUT_RAISE,
            ActionOnFailure.CANCALE_ALL_CHILDREN_WITHOUT_RAISE,
        ):
            return
        if not self.exception:
            return
        ex = self.exception["exception_obj"]
        for name, task in self.tasks.items():
            if task is self.exception["task"]:
                raise NurseryChildFailure(
                    "one of childrens raised an exception "
                    "in nursery, name: %s" % name
                ) from ex

    def _task_done_hook(self, task: asyncio.Task) -> None:
        try:
            if task.done() and task.exception() and not self.exception:
                # set first raised exception on nursery
                # also consumes all exceptions of children
                self.exception = {
                    "exception_obj": task.exception(),
                    "task": task,
                }
        except asyncio.CancelledError:
            pass
        if self.action_on_failure in (
            ActionOnFailure.IGNORE_WITHOUT_RAISE,
            ActionOnFailure.IGNORE_AND_RAISE,
        ):
            return
        try:
            # cancel other active children
            if task.done() and task.exception():
                for _, t in self.tasks.items():
                    if not t.done():
                        t.cancel()
        except asyncio.CancelledError:
            pass
