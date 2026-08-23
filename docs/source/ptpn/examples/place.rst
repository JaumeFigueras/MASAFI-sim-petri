Working with places
===================

These examples use only :class:`~masafi_sim_petri.petri_net.place.Place`. There
is no net around them yet, so the token movements are performed by hand — which
is a good way to see what the firing rule will later automate.

A buffer being filled and drained
---------------------------------

A buffer that starts empty, receives three items and then has two taken out:

.. doctest::

   >>> from masafi_sim_petri import Place
   >>> buffer = Place('buffer')
   >>> buffer.marking
   0
   >>> buffer.add_tokens(3)
   >>> buffer.marking
   3
   >>> buffer.remove_tokens(2)
   >>> buffer.marking
   1

Firing a transition by hand
---------------------------

A transition that takes one token from ``waiting`` and puts one into
``served``, with a single ``server`` token that is taken and given back. This is
the mutual exclusion pattern: while the server token is out, no second customer
can start.

.. doctest::

   >>> from masafi_sim_petri import Place
   >>> waiting = Place('waiting', initial_marking=2)
   >>> server = Place('server', initial_marking=1)
   >>> served = Place('served')

The enabling test comes first: every input place must be able to supply the
weight of its arc.

.. doctest::

   >>> enabled = waiting.has_tokens(1) and server.has_tokens(1)
   >>> enabled
   True

Firing consumes the inputs and produces the outputs:

.. doctest::

   >>> waiting.remove_tokens(1)
   >>> server.remove_tokens(1)
   >>> served.add_tokens(1)
   >>> server.add_tokens(1)
   >>> (waiting.marking, server.marking, served.marking)
   (1, 1, 1)

Fire it once more and the queue empties:

.. doctest::

   >>> waiting.remove_tokens(1)
   >>> served.add_tokens(1)
   >>> (waiting.marking, served.marking)
   (0, 2)

Now the transition is no longer enabled, because ``waiting`` cannot supply a
token:

.. doctest::

   >>> waiting.has_tokens(1) and server.has_tokens(1)
   False

Weighted arcs
-------------

An arc weight is simply the count passed to the three methods. A transition
that packs six items into a box of six consumes six tokens and produces one:

.. doctest::

   >>> from masafi_sim_petri import Place
   >>> items = Place('items', initial_marking=13)
   >>> boxes = Place('boxes')
   >>> while items.has_tokens(6):
   ...     items.remove_tokens(6)
   ...     boxes.add_tokens(1)
   >>> (items.marking, boxes.marking)
   (1, 2)

Thirteen items make two full boxes and leave one item over — the transition is
no longer enabled, which is the enabling rule doing exactly its job.

Running a simulation twice
--------------------------

Because each place remembers its initial marking, a net can be returned to its
starting state and run again. This is what makes repeated runs, and analysis
that begins from :math:`M_0`, possible.

.. doctest::

   >>> from masafi_sim_petri import Place
   >>> stock = Place('stock', initial_marking=4)
   >>> sold = Place('sold')
   >>> def run() -> tuple[int, int]:
   ...     while stock.has_tokens():
   ...         stock.remove_tokens()
   ...         sold.add_tokens()
   ...     return stock.marking, sold.marking
   >>> run()
   (0, 4)
   >>> stock.reset()
   >>> sold.reset()
   >>> run()
   (0, 4)

Guarding against a bad firing
-----------------------------

Removing more tokens than a place holds is a bug in the firing rule, so it
raises rather than passing silently:

.. doctest::

   >>> from masafi_sim_petri import Place
   >>> stock = Place('stock', initial_marking=1)
   >>> stock.remove_tokens(3)
   Traceback (most recent call last):
       ...
   ValueError: Cannot remove 3 tokens from place 'stock', which holds 1
   >>> stock.marking
   1

The marking is untouched: a rejected removal leaves the place exactly as it
was.
