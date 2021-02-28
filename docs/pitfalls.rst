========
Pitfalls
========


Be carefull about awaiting in the body of nurseries
***************************************************
If your nursery decide to cancel everything after a child failure,
`children` will be canceled, not the the body: ::

  import logging
  from asyncio import sleep
  from one_ring import Nursery, run_main, ActionOnFailure

  logging.basicConfig(format='%(asctime)s - %(message)s"', level=logging.INFO)


  async def failure_job(sleep_time):
      logging.info("failure job started")
      await sleep(sleep_time)
      logging.info("failure job sleep ended")
      raise Exception("Boooooom!")


  async def main():
      async with Nursery(ActionOnFailure.CANCEL_ALL_CHILDREN_WITHOUT_RAISE) as n:
          n.start(failure_job(1))
          await sleep(3)
          logging.info("sleep in nursery body ended")


  if __name__ == "__main__":
      run_main(main())


Result:

.. code-block:: text

    2021-02-25 20:32:53,505 - failure job started
    2021-02-25 20:32:54,505 - failure job sleep ended
    2021-02-25 20:32:56,507 - sleep in nursery body ended

As you can see, the sleep in the nursery didn't canceled.

Transfering None in channels
****************************
You can **not** *send* :code:`None` to channels, it will raise :code:`SendNoneToChannelError`,
but if you try to *receive* from a **closed** channel, you will get :code:`None` (like *core.async*) ::

  import logging
  from asyncio import sleep
  from one_ring import Nursery, run_main, Channel

  logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)


  async def publisher(ch, sleep_time):
      logging.info("publisher: started")
      await sleep(sleep_time)
      logging.info("publisher: closing channel")
      ch.close()


  async def main():
      async with Nursery() as n:
          ch = Channel()
          n.start(publisher(ch, 3))
          result = await ch.receive()
          logging.info("result: %s / is_closed: %s" % (result, ch.is_closed()))


  if __name__ == "__main__":
      run_main(main())


Result:

.. code-block:: text

    2021-02-25 20:48:15,484 - publisher: started
    2021-02-25 20:48:18,485 - publisher: closing channel
    2021-02-25 20:48:18,485 - result: None / is_closed: True


Exception in Nursery body
*************************
If any exception arises in the body of Nursery, all children **will be** terminated regardless of :code:`action_on_failure` value. ::

  import logging
  from asyncio import sleep, CancelledError
  from one_ring import Nursery, run_main, ActionOnFailure

  logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)


  async def job(sleep_time):
      try:
          logging.info("job started")
          await sleep(sleep_time)
          logging.info("job sleep ended successfully")
      except CancelledError:
          logging.info("job canceled")


  async def main():
      async with Nursery(ActionOnFailure.IGNORE_WITHOUT_RAISE) as n:
          n.start(job(3))
          await sleep(0.5)
          raise Exception("booooo!")
          logging.info("sleep in nursery body ended")


  if __name__ == "__main__":
      run_main(main())


Result:

.. code-block:: text

  2021-02-28 23:28:31,231 - job started
  2021-02-28 23:28:31,732 - job canceled
  Traceback (most recent call last):
    File "dev_main.py", line 26, in <module>
      run_main(main())
    File "/home/yaser/workspace/one_ring/one_ring/asyncio_sugar.py", line 10, in run_main
      loop.run_until_complete(main_coro)
    File "/usr/lib64/python3.6/asyncio/base_events.py", line 488, in run_until_complete
      return future.result()
    File "dev_main.py", line 21, in main
      raise Exception("booooo!")
  Exception: booooo!
