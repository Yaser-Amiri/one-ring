.. toctree::
   :hidden:

   self
   primitives
   samples
   reference
   pitfalls

What's this?
============
The main purpose of this library is to facilitate concurrent programming with Asyncio,
to achieve this purpose it will give you basic tools of CSP (like :code:`channel` and :code:`select`),
structured concurrency and of course some sugars for Asyncio.

This is not a CSP tutorial so you need to learn it before using this library
(if you used *Golang* or *core.async* before, you should be good)


Be carefull
***********
- This is **not** a production-ready and battle-tested library.
- No thread safety or any kind of preemptive multitasking is considered in this library. Keep it in mind.
- Do **not** expect exact Go-like behavior from this library, I changed some of them on purpose.


   Indices and tables
   ==================

   * :ref:`genindex`
   * :ref:`search`
