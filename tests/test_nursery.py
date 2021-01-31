import asyncio
from random import randint
from unittest.mock import MagicMock

import pytest

from one_ring import Nursery, NurseryChildFailure, ActionOnFailure


async def nop(count=1):
    for _ in range(count):
        await asyncio.sleep(0.05)


async def nop_err(count=1):
    for _ in range(count):
        await asyncio.sleep(0.05)
    raise Exception("booo!")


@pytest.mark.asyncio
async def test_nursery_task_name_generation(event_loop):
    n = Nursery()
    for i in range(5):
        assert n._generate_task_name() == "task-%s" % i


@pytest.mark.asyncio
async def test_start_task_with_custom_acceptable_name(event_loop):
    name = "aaa"
    async with Nursery() as n:
        assert n.tasks == {}
        n.start(nop(), name)
        assert name in n.tasks


@pytest.mark.asyncio
async def test_get_task_by_name(event_loop):
    name = "aaa"
    async with Nursery() as n:
        n.start(nop(), name)
        assert n.get_task_by_name(name) is not None


@pytest.mark.asyncio
async def test_get_task_by_name_with_wrong_name(event_loop):
    name = "aaa"
    async with Nursery() as n:
        n.start(nop(), name)
        assert n.get_task_by_name(name + "b") is None


@pytest.mark.asyncio
async def test_start_task_with_custom_duplicate_name(event_loop):
    name = "aaa"
    async with Nursery() as n:
        assert n.tasks == {}
        n.start(nop(), name)
        assert name in n.tasks

        coro = nop()
        with pytest.raises(ValueError):
            n.start(coro, name)

        # prevent RuntimeWarning for not scheduling the corotine
        await event_loop.create_task(coro)


@pytest.mark.asyncio
async def test_all_coroutine_are_done_after_exit(event_loop):
    # no error in tasks
    async with Nursery() as n1:
        n1.start(nop(randint(10, 20)))
        n1.start(nop(randint(10, 20)))
        n1.start(nop(randint(10, 20)))

    for t in n1.tasks.values():
        assert t.done()

    # with raising exception in tasks
    # check for all types of ActionOnFailure
    for action_on_failure in ActionOnFailure._member_map_.values():
        try:
            async with Nursery(on_failure=action_on_failure) as n2:
                n2.start(nop_err(randint(10, 20)))
                n2.start(nop_err(randint(10, 20)))
                n2.start(nop_err(randint(10, 20)))
        except NurseryChildFailure as e:
            if "booo!" not in str(e.__cause__):
                raise
        finally:
            for t in n2.tasks.values():
                assert t.done()


@pytest.mark.asyncio
async def test_check_done_call_back_is_attached(event_loop):
    async with Nursery() as n:
        task = n.start(nop(1))
        assert n._task_done_hook in task._callbacks

    # start corotine that raises an exception immediately
    async def immediate_err():
        raise Exception("booo!")

    try:
        async with Nursery() as n:
            task = n.start(immediate_err())
            assert n._task_done_hook in task._callbacks
    except NurseryChildFailure as e:
        # in case of changing default action on failure
        if "booo!" not in str(e.__cause__):
            raise


@pytest.mark.asyncio
async def test_raising_exception_at_exit(event_loop):
    # IGNORE_WITHOUT_RAISE
    try:
        async with Nursery(ActionOnFailure.IGNORE_WITHOUT_RAISE) as n:
            n.start(nop_err(1))
    except NurseryChildFailure:
        raise
    else:
        assert n.exception.get("exception_obj", None) is not None
        assert n.exception.get("task", None) is not None

    # IGNORE_AND_RAISE
    try:
        async with Nursery(ActionOnFailure.IGNORE_AND_RAISE) as n:
            n.start(nop_err(1))
    except NurseryChildFailure:
        assert n.exception.get("exception_obj", None) is not None
        assert n.exception.get("task", None) is not None
    else:
        assert False, "this is wrong! it must raise for IGNORE_AND_RAISE"

    # CANCALE_ALL_CHILDREN_WITHOUT_RAISE
    try:
        async with Nursery(
            ActionOnFailure.CANCALE_ALL_CHILDREN_WITHOUT_RAISE
        ) as n:
            n.start(nop_err(1))
    except NurseryChildFailure:
        raise
    else:
        assert n.exception.get("exception_obj", None) is not None
        assert n.exception.get("task", None) is not None

    # CANCALE_ALL_CHILDREN_AND_RAISE
    try:
        async with Nursery(
            ActionOnFailure.CANCALE_ALL_CHILDREN_AND_RAISE
        ) as n:
            n.start(nop_err(1))
    except NurseryChildFailure:
        assert n.exception.get("exception_obj", None) is not None
        assert n.exception.get("task", None) is not None
    else:
        assert (
            False
        ), "this is wrong! it must raise for CANCALE_ALL_CHILDREN_AND_RAISE"


@pytest.mark.asyncio
async def test_cancellation_on_CANCALE_ALL_CHILDREN_WITHOUT_RAISE(event_loop):
    async def job(c):
        try:
            await nop(1)
            await asyncio.sleep(1)
            await nop(1)
        except asyncio.CancelledError:
            c(True)

    cancelled = MagicMock(return_value=1)
    async with Nursery(
        ActionOnFailure.CANCALE_ALL_CHILDREN_WITHOUT_RAISE
    ) as n:
        n.start(job(cancelled))
        n.start(nop_err(1))

    cancelled.assert_called_with(True)


@pytest.mark.asyncio
async def test_cancellation_on_IGNORE_WITHOUT_RAISE(event_loop):
    async def job(c):
        try:
            await nop(1)
            await asyncio.sleep(1)
            await nop(1)
        except asyncio.CancelledError:
            c(True)
        else:
            c(False)

    cancelled = MagicMock(return_value=1)
    async with Nursery(ActionOnFailure.IGNORE_WITHOUT_RAISE) as n:
        n.start(job(cancelled))
        n.start(nop_err(1))

    cancelled.assert_called_with(False)


@pytest.mark.asyncio
async def test_cancellation_on_CANCALE_ALL_CHILDREN_AND_RAISE(event_loop):
    async def job(c):
        try:
            await nop(1)
            await asyncio.sleep(1)
            await nop(1)
        except asyncio.CancelledError:
            c(True)

    cancelled = MagicMock(return_value=1)
    try:
        async with Nursery(
            ActionOnFailure.CANCALE_ALL_CHILDREN_AND_RAISE
        ) as n:
            n.start(job(cancelled))
            n.start(nop_err(1))
    except NurseryChildFailure:
        pass
    else:
        assert False, "it must raise exception"

    cancelled.assert_called_with(True)


@pytest.mark.asyncio
async def test_cancellation_on_IGNORE_AND_RAISE(event_loop):
    async def job(c):
        try:
            await nop(1)
            await asyncio.sleep(1)
            await nop(1)
        except asyncio.CancelledError:
            c(True)
        else:
            c(False)

    cancelled = MagicMock(return_value=1)

    try:
        async with Nursery(ActionOnFailure.IGNORE_AND_RAISE) as n:
            n.start(job(cancelled))
            n.start(nop_err(1))
    except NurseryChildFailure:
        pass
    else:
        assert False, "it must raise exception"

    cancelled.assert_called_with(False)
