=========
Samples
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

select
******
Makes a single choice between one of several channel operations (blocking),
it's like Golang's :code:`select` and of course :code:`alt!` in core.async

Channels have two methods for dispatching on :code:`select`, the :code:`R` for receiving and :code:`S` for sending data.  
:code:`select` returns a tuple, the first member is the channel that selected, the second is the data that transmitted. ::

  import logging
  from asyncio import sleep
  from one_ring import Nursery, run_main, ActionOnFailure, Channel, select

  logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)


  async def job(sleep_time: int, ch: Channel):
      logging.info("job started")
      await sleep(sleep_time)
      await ch.send("this is data")
      logging.info("job sleep ended successfully")


  async def main():
      ch1 = Channel()
      ch2 = Channel()
      ch3 = Channel()
      async with Nursery(ActionOnFailure.IGNORE_WITHOUT_RAISE) as n:
          n.start(job(2, ch2))
          ch_with_result, result = await select(
              ch1.R(),
              ch2.R(),
              ch3.S("blah data")
          )
          logging.info("ch2 selected: %s" % (ch_with_result is ch2))
          logging.info("ch2 result: %s" % result)


  if __name__ == "__main__":
      run_main(main())

Result:

.. code-block:: text

  2021-03-01 22:44:45,731 - job started
  2021-03-01 22:44:47,733 - job sleep ended successfully
  2021-03-01 22:44:47,733 - ch2 selected: True
  2021-03-01 22:44:47,733 - ch2 result: this is data

If you don't want to be blocked, use :code:`selecte_nowait` instead of :code:`select`, it's just like having :code:`default` in Golang.

**Remember** it's not awaitable, it's a normal function.::

  import logging
  from one_ring import run_main, Channel, select_nowait

  logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)


  async def main():
      ch1 = Channel()
      ch2 = Channel()
      first_ch_with_result, first_result = select_nowait(
          ch1.R(),
          ch2.S("blah data"),
      )
      logging.info("first try: ch_with_result is: %s" % first_ch_with_result)
      logging.info("first try: result: %s" % first_result)

      ch3 = Channel(maxsize=1)
      second_ch_with_result, second_result = select_nowait(
          ch1.R(),
          ch3.S("blah data"),
      )
      logging.info("second try: ch_with_result is: %s" % second_ch_with_result)
      logging.info("second try: result: %s" % second_result)


  if __name__ == "__main__":
      run_main(main())

Result:

.. code-block:: text

  2021-03-01 22:41:19,915 - first try: ch_with_result is: None
  2021-03-01 22:41:19,915 - first try: result: None
  2021-03-01 22:41:19,915 - second try: ch_with_result is: <Channel maxsize=1 _data=['blah data']>
  2021-03-01 22:41:19,916 - second try: result: blah 
