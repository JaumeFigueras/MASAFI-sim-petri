The Arc class
=============

.. currentmodule:: masafi_sim_petri.petri_net.arc

An arc joins a place to a transition, or a transition to a place, and carries
the number of tokens that move when the transition fires.

.. doctest::

   >>> from masafi_sim_petri import Arc, Place, Transition
   >>> buffer = Place('buffer', initial_marking=6)
   >>> pack = Transition('pack')
   >>> arc = Arc(buffer, pack, weight=6)
   >>> print(arc)
   buffer --6--> pack

The bipartite rule
------------------

A Petri net is a bipartite graph: places connect only to transitions and
transitions only to places. This is not a modelling convention that can be bent
— it is what makes the formalism what it is. A place holds state; a transition
changes it. An arc between two places would mean state flowing into state with
no event in between, which has no meaning under the firing rule.

So the class enforces it, and rejects the mistake at the moment it is made
rather than letting a malformed net reach the simulator:

.. doctest::

   >>> Arc(Place('p1'), Place('p2'))
   Traceback (most recent call last):
       ...
   ValueError: An arc must join a place and a transition, got Place and Place

This is one of the few places in the library that checks types at run time. The
rule being enforced is a property of Petri nets, not a matter of Python typing,
and the net's structure is often built by an editor from user actions rather
than by code a type checker has seen.

Direction, from the transition's point of view
----------------------------------------------

Standard Petri net terminology names an arc after what it does to its
transition, and the class follows it:

**Input arc** — from a place to a transition
   Firing *removes* :attr:`Arc.weight` tokens from the place. The place must
   be able to supply them, which is what makes the transition enabled or not.

**Output arc** — from a transition to a place
   Firing *adds* :attr:`Arc.weight` tokens to the place. There is no condition
   to satisfy: places are unbounded, so a production never blocks.

.. doctest::

   >>> Arc(buffer, pack).is_input
   True
   >>> Arc(pack, buffer).is_output
   True

Because the graph is bipartite, an arc always has exactly one place and exactly
one transition, whichever way it runs. So besides ``source`` and ``target``,
which follow the direction, the endpoints can be reached by kind:

.. doctest::

   >>> outgoing = Arc(pack, buffer)
   >>> outgoing.place is buffer
   True
   >>> outgoing.transition is pack
   True

Net code usually wants the endpoints by kind — *which place does this arc
drain?* — while code that draws or serialises the net wants them by direction.
Both are available, and they are two views of the same two objects.

Self-loops are two arcs
-----------------------

A transition that takes a token and gives it back — the shape that expresses a
resource being borrowed, or a condition being read without being consumed —
needs an arc in each direction:

.. doctest::

   >>> tool = Place('tool', initial_marking=1)
   >>> work = Transition('work')
   >>> take = Arc(tool, work)
   >>> give_back = Arc(work, tool)

There is no bidirectional arc, and that is deliberate: the two directions may
carry different weights, and the reachability analysis has to treat consumption
and production separately in any case.

Weight
------

:attr:`Arc.weight` is the number of tokens moved, and it defaults to 1.

A weight of zero is rejected rather than treated as "no arc". An arc that moves
nothing is not a weaker arc; it is the absence of an arc, and expressing that
by deleting the arc keeps one representation for one situation. A net in which
some arcs are real and others are inert would have to be filtered everywhere it
is read.

.. doctest::

   >>> Arc(buffer, pack, weight=0)
   Traceback (most recent call last):
       ...
   ValueError: The weight of an arc must be at least 1, got 0

Weights are where the arithmetic of a P/T net lives. A transition packing six
items into a box has an input arc of weight 6 and an output arc of weight 1;
it is enabled only when six items are present, and it consumes all six at once.

Nothing about an arc changes
----------------------------

Both endpoints and :attr:`Arc.weight` are fixed at construction. An arc is a
piece of the *structure* of a net, not part of its state — the state is the
marking, and that lives in the places.

This matters for analysis. The reachability graph is built on the assumption
that the structure holds still while the marking moves; an arc whose weight
could change underneath it would silently invalidate the result. Editing a net
— rewiring an arc, changing a weight — is an operation on the net, which can
rebuild whatever indexes it keeps.

If the editor turns out to need in-place weight changes often enough that
replacing the arc is awkward, a validated setter can be added. Relaxing that
later is easy; taking a setter away once code depends on it is not.

An arc does not know its net
----------------------------

An arc holds its two endpoints, but neither the place nor the transition holds
the arc, and the arc does not hold the net. Connectivity is recorded once, in
:class:`~masafi_sim_petri.petri_net.petri_net.PetriNet`, which keeps the object
graph acyclic and leaves exactly one thing to update when a net is edited.

Full API
--------

Every method, with its parameters and the exceptions it raises, is in the
:doc:`API reference </api/masafi_sim_petri.petri_net.arc>`.
