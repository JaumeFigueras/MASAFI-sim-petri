The Transition class
====================

A transition is an event that may happen. Where a place represents a condition
— *there are three items in the buffer* — a transition represents a change —
*an item is taken from the buffer*.

:class:`~masafi_sim_petri.petri_net.transition.Transition` is created with a
name and nothing else:

.. doctest::

   >>> from masafi_sim_petri import Transition
   >>> take = Transition('take_item')
   >>> take.name
   'take_item'

A transition with no state
--------------------------

The class is small, and that is the point rather than an omission.

Everything a transition does involves objects other than itself. Whether it is
enabled depends on the markings of its input places and on the weights of the
arcs reaching it. Firing it moves tokens between places. None of that
information lives in the transition:

* the **marking** lives in the places;
* the **connectivity** lives in the net.

So there is nothing left for a P/T transition to hold except its name. It is a
node in a graph, and the graph is owned by
:class:`~masafi_sim_petri.petri_net.petri_net.PetriNet`.

This is why you will not find ``transition.is_enabled()`` or
``transition.fire()`` on this class. A transition genuinely cannot answer those
questions on its own; it does not know which arcs reach it. They are operations
of the net::

    net.is_enabled(take)
    net.fire(take)

The alternative design — giving each transition a list of its input and output
arcs — would let it answer for itself, at the cost of turning the model into a
cyclic object graph with connectivity recorded in two places at once. Keeping
the topology in one object means there is one thing to keep consistent when a
net is edited, which matters when the editor is a separate application adding
and removing arcs interactively.

Where the state will appear
---------------------------

A transition stays stateless only for untimed nets.

``TransitionTimed`` will add a duration and, while it is firing, the fact that
it is in the middle of firing: a timed transition consumes its input tokens at
the moment it starts, waits, and produces its output tokens when the delay has
elapsed. During that interval the tokens exist in neither the input nor the
output places, and that is state the transition itself must carry.

For coloured nets a transition will also carry the rule that decides which
tokens it may consume and what it produces from them. Both extensions inherit
from this class, so the name and its validation are written once.

Naming
------

The name is fixed at construction and cannot be reassigned. The net indexes its
transitions by name, so a transition that could rename itself would leave that
index pointing at the wrong entry. Renaming, when the editor needs it, will go
through the net, which can update both the transition and its own index
together.

Blank names are rejected for the same reason a blank place name is: the name is
what identifies the transition inside a net.

.. doctest::

   >>> Transition('   ')
   Traceback (most recent call last):
       ...
   ValueError: The name of a transition cannot be empty

Full API
--------

Every method, with its parameters and the exceptions it raises, is in the
:doc:`API reference </api/masafi_sim_petri.petri_net.transition>`.
