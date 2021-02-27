import asyncio
from asyncio import AbstractEventLoop
from typing import Dict, Optional, Any, Awaitable
from enum import IntEnum

from .asyncio_sugar import get_current_task

NURSERY_MAIN_TASK_NAME = "main-task-0"


class ActionOnFailure(IntEnum):
    IGNORE_WITHOUT_RAISE = 0
    CANCEL_ALL_CHILDREN_WITHOUT_RAISE = 1
    IGNORE_AND_RAISE = 2
    CANCEL_ALL_CHILDREN_AND_RAISE = 3


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
        self.__task_number: int = 1

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
            [t for n, t in self.tasks.items() if n != NURSERY_MAIN_TASK_NAME],
            return_when=asyncio.ALL_COMPLETED,
        )

    def get_task_by_name(self, name: str) -> Optional[asyncio.Task]:
        return self.tasks.get(name, None)

    async def __aenter__(self) -> "Nursery":
        self.tasks[NURSERY_MAIN_TASK_NAME] = get_current_task(loop=self._loop)
        return self

    async def __aexit__(self, *exc_info) -> None:
        if exc_info[1]:
            current_task = get_current_task(loop=self._loop)
            self.exception = {
                "exception_obj": exc_info[1],
                "task": current_task,
            }
            self._do_action_on_failure(current_task)

        await self._wait_until_complete()

        if self.action_on_failure in (
            ActionOnFailure.IGNORE_WITHOUT_RAISE,
            ActionOnFailure.CANCEL_ALL_CHILDREN_WITHOUT_RAISE,
        ):
            return

        if not self.exception:
            return

        ex = self.exception["exception_obj"]
        if self.exception["task"] is self.tasks[NURSERY_MAIN_TASK_NAME]:
            raise ex
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
        self._do_action_on_failure(task)

    def _do_action_on_failure(self, task: asyncio.Task) -> None:
        # if main task failed
        if task is self.tasks[NURSERY_MAIN_TASK_NAME]:
            self._cancel_children()
            return

        # if one of children failed
        if self.action_on_failure in (
            ActionOnFailure.IGNORE_WITHOUT_RAISE,
            ActionOnFailure.IGNORE_AND_RAISE,
        ):
            return
        try:
            # cancel other active children
            if task.done() and task.exception():
                self._cancel_children()
        except asyncio.CancelledError:
            pass

    def _cancel_children(self) -> None:
        for n, t in self.tasks.items():
            if not t.done() and n != NURSERY_MAIN_TASK_NAME:
                t.cancel()
