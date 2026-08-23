Building and running a net
==========================

These examples build complete nets and run them. Everything the previous page
did by hand — checking that a place can supply a token, moving tokens between
places — is now done by the firing rule.

A queue with one server
-----------------------

Two customers waiting, one server, and a transition that serves a customer by
borrowing the server and giving it back.

.. doctest::

   >>> from masafi_sim_petri import Arc, PetriNet, Place, Transition
   >>> net = PetriNet()
   >>> waiting = net.add_place(Place('waiting', initial_marking=2))
   >>> server = net.add_place(Place('server', initial_marking=1))
   >>> served = net.add_place(Place('served'))
   >>> serve = net.add_transition(Transition('serve'))
   >>> _ = net.add_arc(Arc(waiting, serve))
   >>> _ = net.add_arc(Arc(server, serve))
   >>> _ = net.add_arc(Arc(serve, served))
   >>> _ = net.add_arc(Arc(serve, server))

Run it until nothing is enabled, printing the marking at each step:

.. doctest::

   >>> print(net.marking)
   (2, 1, 0)
   >>> while net.enabled_transitions():
   ...     net.fire(net.enabled_transitions()[0])
   ...     print(net.marking)
   (1, 1, 1)
   (0, 1, 2)

Both customers have been served and the server is free again. Running the same
net a second time only needs a reset:

.. doctest::

   >>> net.reset()
   >>> net.marking
   (2, 1, 0)

A producer and a consumer sharing a buffer
------------------------------------------

A producer that makes items and a consumer that takes them, joined by a buffer.
The producer is a source transition: it has no input arcs, so it can always
fire.

.. doctest::

   >>> line = PetriNet()
   >>> buffer = line.add_place(Place('buffer'))
   >>> consumed = line.add_place(Place('consumed'))
   >>> produce = line.add_transition(Transition('produce'))
   >>> consume = line.add_transition(Transition('consume'))
   >>> _ = line.add_arc(Arc(produce, buffer))
   >>> _ = line.add_arc(Arc(buffer, consume))
   >>> _ = line.add_arc(Arc(consume, consumed))

With the buffer empty only the producer can fire:

.. doctest::

   >>> [t.name for t in line.enabled_transitions()]
   ['produce']

Produce twice, and now either may fire:

.. doctest::

   >>> line.fire(produce)
   >>> line.fire(produce)
   >>> line.marking
   (2, 0)
   >>> [t.name for t in line.enabled_transitions()]
   ['produce', 'consume']

This net is **unbounded**: ``produce`` is never blocked, so the buffer can grow
without limit. That is a real property of the model, and the library does not
hide it by imposing a capacity. If the buffer should be bounded, the net must
say so — which is the next example.

Bounding a buffer with tokens
-----------------------------

Capacity is not an attribute of a place. It is modelled by a second place
holding the *free slots*, so that producing consumes a slot and consuming
returns one. The two places always hold three tokens between them.

.. doctest::

   >>> bounded = PetriNet()
   >>> items = bounded.add_place(Place('items'))
   >>> free = bounded.add_place(Place('free', initial_marking=3))
   >>> produce = bounded.add_transition(Transition('produce'))
   >>> consume = bounded.add_transition(Transition('consume'))
   >>> _ = bounded.add_arc(Arc(free, produce))
   >>> _ = bounded.add_arc(Arc(produce, items))
   >>> _ = bounded.add_arc(Arc(items, consume))
   >>> _ = bounded.add_arc(Arc(consume, free))

Fill the buffer and the producer stops on its own:

.. doctest::

   >>> for _ in range(3):
   ...     bounded.fire(produce)
   >>> bounded.marking
   (3, 0)
   >>> [t.name for t in bounded.enabled_transitions()]
   ['consume']

Modelling the capacity rather than declaring it means the constraint is visible
in the net, and the analysis can reason about it like anything else.

Weighted arcs: packing items into boxes
---------------------------------------

Six items make a box. The input arc has weight 6, so the transition is enabled
only when six items are present and consumes all six at once.

.. doctest::

   >>> packing = PetriNet()
   >>> item = packing.add_place(Place('items', initial_marking=13))
   >>> box = packing.add_place(Place('boxes'))
   >>> pack = packing.add_transition(Transition('pack'))
   >>> _ = packing.add_arc(Arc(item, pack, weight=6))
   >>> _ = packing.add_arc(Arc(pack, box))
   >>> while packing.enabled_transitions():
   ...     packing.fire(pack)
   >>> packing.marking
   (1, 2)

Thirteen items give two full boxes and leave one over, with the arc weight
doing the arithmetic.

Two machines, one tool
----------------------

The mutual exclusion pattern. Each machine must take the single tool before it
can work, and release it afterwards.

.. doctest::

   >>> shop = PetriNet()
   >>> tool = shop.add_place(Place('tool', initial_marking=1))
   >>> for machine in ['1', '2']:
   ...     idle = shop.add_place(Place(f'idle_{machine}', initial_marking=1))
   ...     working = shop.add_place(Place(f'working_{machine}'))
   ...     take = shop.add_transition(Transition(f'take_{machine}'))
   ...     release = shop.add_transition(Transition(f'release_{machine}'))
   ...     _ = shop.add_arc(Arc(idle, take))
   ...     _ = shop.add_arc(Arc(tool, take))
   ...     _ = shop.add_arc(Arc(take, working))
   ...     _ = shop.add_arc(Arc(working, release))
   ...     _ = shop.add_arc(Arc(release, idle))
   ...     _ = shop.add_arc(Arc(release, tool))

Both machines are ready to start:

.. doctest::

   >>> [t.name for t in shop.enabled_transitions()]
   ['take_1', 'take_2']

As soon as one takes the tool, the other is locked out — not by a rule, but
because the token it needs is gone:

.. doctest::

   >>> shop.fire(shop.transition('take_1'))
   >>> [t.name for t in shop.enabled_transitions()]
   ['release_1']

Releasing puts the tool back and both machines contend again:

.. doctest::

   >>> shop.fire(shop.transition('release_1'))
   >>> [t.name for t in shop.enabled_transitions()]
   ['take_1', 'take_2']

Exploring every reachable marking
---------------------------------

The marking is a hashable tuple and it can be assigned back, which is all that
a search over the state space needs. Here is that search written out — the
shape the reachability analysis will take:

.. doctest::

   >>> def reachable(net: PetriNet) -> set[tuple[int, ...]]:
   ...     seen: set[tuple[int, ...]] = set()
   ...     pending = [net.initial_marking]
   ...     while pending:
   ...         marking = pending.pop()
   ...         if marking in seen:
   ...             continue
   ...         seen.add(marking)
   ...         net.marking = marking
   ...         for transition in net.enabled_transitions():
   ...             net.marking = marking
   ...             net.fire(transition)
   ...             pending.append(net.marking)
   ...     return seen

The workshop has exactly three reachable states: nobody working, machine 1
working, machine 2 working.

.. doctest::

   >>> shop.reset()
   >>> len(reachable(shop))
   3

And the property the net was built to guarantee holds in every one of them:

.. doctest::

   >>> both = (
   ...     shop.places.index(shop.place('working_1')),
   ...     shop.places.index(shop.place('working_2')),
   ... )
   >>> any(marking[both[0]] and marking[both[1]] for marking in reachable(shop))
   False

That is not a statement about the runs that happened to be tried. Every
reachable marking was visited, so no interleaving is left untested — which is
what a Petri net offers over simulation alone.
