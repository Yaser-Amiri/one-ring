=========
Usecases
=========


Simple send and receive from channels
*************************************
Let's start with simplest thing: ::

    import asyncio
    from one_ring import Channel, run_main


    async def job(ch: Channel):
        print("job: go to sleep")
        await asyncio.sleep(3)
        print("job: wake up & try to send data")
        await ch.send(123)
        print("job: finished")


    async def main():
        ch = Channel()
        loop = asyncio.get_event_loop()
        loop.create_task(job(ch))
        print("main: try to receive data")
        data = await ch.receive()
        print("main: data is %s" % data)


    if __name__ == "__main__":
        run_main(main())


The result will be:

.. code-block:: text

    main: try to receive data
    job: go to sleep
    job: wake up & try to send data
    job: finished
    main: data is 123

Obviously :code:`send` and :code:`receive` methods are blocking. If you dont want to be blocked,
you can use :code:`send_nowait` and :code:`receive_nowait` but they are simple functions
so dont use :code:`await` for them.


Buffered channel
****************

You can create buffered channel by passing :code:`maxsize` to Channel class: ::

    from one_ring import Channel, run_main


    async def main():
        ch = Channel(maxsize=2)

        ch.send_nowait(1)  # >>> True
        await ch.send(2)
        # await ch.send(3)  # if I do this, it will block
        ch.send_nowait(3)  # >>> False

        ch.receive_nowait()  # >>> 1
        await ch.receive()  # >>> 2
        # await ch.receive()  # if I do this, it will block
        ch.receive_nowait()  # >>> None

        assert ch.empty()


    if __name__ == "__main__":
        run_main(main())
