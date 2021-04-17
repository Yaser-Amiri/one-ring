============
Primitives
============


Channel
*******
CSP is based on message passing and you can do it via channels.
You can pass everything through channels except :code:`None`.
Channels can be buffered with a static size or unbuffered.
If you try to send a value to a full channel, you will be blocked until somebody
receives a value from the channel and opens a spot, and vice versa.

Channels can be closed by calling the :code:`close` method (if you close a channel that was already closed, you won't get any error)
You can not send anything to a closed channel and if you try to receive from it, you will get :code:`None`

Sample code: ::

  async def main():
      unbuffered_channel = Channel()  # create an unbuffered channel
      buffered_channel = Channel(maxsize=8)  # create a buffered channel
      a = await unbuffered_channel.receive()  # receive from the channel
      b = unbuffered_channel.send_nowait("a not None value")  # try to receive a value from the channel and move on (without blocking)
      await unbuffered_channel.send("not None value")  # send a value to the channel
      unbuffered_channel.send_nowait("this is a no None value")  # try to send a value to the channel and move on (without blocking)
      print(buffered_channel.is_closed())  # check if the channel is closed or not
      buffered_channel.close()  # close the channel, you can close a closed channel without error
      print(buffered_channel.maxsize)  # get size of the channel (zero for unbuffered channels)
      print(buffered_channel.size())  # size shows how many spots are taken
      print(buffered_channel.empty())  # check if the channel is empty or not
      print(buffered_channel.full())  # check if the channel is full or not

- When you call :code:`receive` method, it will return a value that is fetched from the channel
  (if you try it on a closed channel you will get :code:`None`).
- :code:`receive_nowait` is the same as :code:`receive` method but it won't block and wait for a value.
  If you call it on an empty channel, it will return :code:`None`
- You can send a value to a channel by calling :code:`send` method
  (You can't send :code:`None`. If you try it, :code:`SendNoneToChannelError` exception will raise).
  This method will block and wait for an open spot (in buffered channels) or a ready listener.
  The return value of this method is a boolean that shows the operation was successful or not.
- :code:`send_nowait` is the same as :code:`send` method but it won't block and wait for a value.


Select
****************
select
select_nowait
