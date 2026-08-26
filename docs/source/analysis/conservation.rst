Conservation of tokens
======================

.. currentmodule:: masafi_sim_petri.analysis.conservation

Firing moves tokens, and it is free to change how many there are. A transition
with one input arc and two output arcs turns one token into two; a transition
with no output arcs makes one disappear. Whether that is a modelling error or
the whole point depends on what the tokens stand for.

When a token stands for a **resource** — a pallet, a machine, a licence, a
customer — the count must not drift. A net that models five machines and can
reach a marking holding six is wrong, and wrong in a way no simulation run is
guaranteed to reveal. Conservation is the property that rules it out.

A net is **strictly conservative** when every transition produces exactly as
many tokens as it consumes:

.. math::

   \forall t \in T: \quad \sum_{p \in {}^{\bullet}t} W(p, t)
                       = \sum_{p \in t^{\bullet}} W(t, p)

Weighing one transition at a time
---------------------------------

:func:`is_strictly_conservative` is the whole of it. The sums are taken over
arc *weights*, not over arcs, so a transition may have any number of arcs on
either side as long as the two totals agree.

.. doctest::

   >>> from masafi_sim_petri import Arc, PetriNet, Place, Transition
   >>> from masafi_sim_petri.analysis import is_k_bounded, is_strictly_conservative

A machine cycling between idle and busy conserves its token: each transition
takes one and gives one back.

.. doctest::

   >>> net = PetriNet()
   >>> idle = net.add_place(Place('idle', initial_marking=1))
   >>> busy = net.add_place(Place('busy'))
   >>> start = net.add_transition(Transition('start'))
   >>> stop = net.add_transition(Transition('stop'))
   >>> _ = net.add_arc(Arc(idle, start))
   >>> _ = net.add_arc(Arc(start, busy))
   >>> _ = net.add_arc(Arc(busy, stop))
   >>> _ = net.add_arc(Arc(stop, idle))
   >>> is_strictly_conservative(net)
   True

Unpacking two tokens into two conserves them just as well, even though the
arcs are not symmetric — one input arc of weight two against two output arcs
of weight one:

.. doctest::

   >>> net = PetriNet()
   >>> pallet = net.add_place(Place('pallet', initial_marking=2))
   >>> left = net.add_place(Place('left'))
   >>> right = net.add_place(Place('right'))
   >>> unpack = net.add_transition(Transition('unpack'))
   >>> _ = net.add_arc(Arc(pallet, unpack, weight=2))
   >>> _ = net.add_arc(Arc(unpack, left))
   >>> _ = net.add_arc(Arc(unpack, right))
   >>> is_strictly_conservative(net)
   True

Forking one token into two does not:

.. doctest::

   >>> net = PetriNet()
   >>> ready = net.add_place(Place('ready', initial_marking=1))
   >>> left = net.add_place(Place('left'))
   >>> right = net.add_place(Place('right'))
   >>> fork = net.add_transition(Transition('fork'))
   >>> _ = net.add_arc(Arc(ready, fork))
   >>> _ = net.add_arc(Arc(fork, left))
   >>> _ = net.add_arc(Arc(fork, right))
   >>> is_strictly_conservative(net)
   False

A source transition — one with no input arcs — never conserves, since it
consumes nothing and produces something. The same holds in reverse for a sink.

Structural, not behavioural
---------------------------

:doc:`Boundedness <boundedness>` had to be searched for: the answer lived in
the reachable markings, and the only way to it was to enumerate them. Strict
conservation is read straight off the arcs, in time linear in their number.
No marking is consulted, nothing is fired, and the size of the state space is
irrelevant. It is the first analysis in this library that costs nothing.

Being structural also makes the answer say more than it appears to. The
balance holds for *every* initial marking, not only the one the net carries,
which gives boundedness for free:

.. epigraph::

   A strictly conservative net keeps :math:`\sum M = \sum M_0` for ever, so no
   place can hold more than :math:`\sum M_0` tokens. The net is
   :math:`k`-bounded for :math:`k = \sum M_0`, and that is a *structural*
   bound: it holds for every initial marking, which no amount of searching can
   establish.

.. doctest::

   >>> net = PetriNet()
   >>> idle = net.add_place(Place('idle', initial_marking=3))
   >>> busy = net.add_place(Place('busy'))
   >>> start = net.add_transition(Transition('start'))
   >>> stop = net.add_transition(Transition('stop'))
   >>> _ = net.add_arc(Arc(idle, start))
   >>> _ = net.add_arc(Arc(start, busy))
   >>> _ = net.add_arc(Arc(busy, stop))
   >>> _ = net.add_arc(Arc(stop, idle))
   >>> is_strictly_conservative(net)
   True
   >>> is_k_bounded(net, sum(net.initial_marking))
   True

The implication runs one way only. A bounded net need not be conservative:
:func:`~masafi_sim_petri.analysis.boundedness.is_k_bounded` answering ``True``
says nothing about the balance of any transition.

Dead transitions are weighed too
--------------------------------

The test asks whether every transition balances, which is slightly stronger
than asking whether the token count stays constant as the net runs. A
transition that can never fire cannot disturb any count, yet an unbalanced one
still makes the answer ``False``.

.. doctest::

   >>> net = PetriNet()
   >>> p1 = net.add_place(Place('p1', initial_marking=1))
   >>> p2 = net.add_place(Place('p2'))
   >>> move = net.add_transition(Transition('move'))
   >>> leak = net.add_transition(Transition('leak'))
   >>> _ = net.add_arc(Arc(p1, move))
   >>> _ = net.add_arc(Arc(move, p2))
   >>> _ = net.add_arc(Arc(p1, leak, weight=2))
   >>> net.is_enabled(leak)
   False
   >>> is_strictly_conservative(net)
   False

``leak`` needs two tokens from a place that will never hold two, so the total
in this net really is constant. The structural answer is still ``False``, and
deliberately so: it is the answer that holds for every initial marking — give
``p1`` two tokens and the leak is real — and it is the answer the boundedness
corollary above depends on. Reporting the behavioural variant instead would
mean exploring the reachable markings, which is exactly the cost this analysis
avoids.

What it does not answer
-----------------------

**Conservation with weighted places is a different question.** A net that
fails this test may still conserve a *weighted* count — one token in a
``pallet`` place standing for two in ``box`` — so that
:math:`y^{T} M = y^{T} M_0` for some vector of positive place weights
:math:`y`. Strict conservation is the case where every place weighs one.
Finding whether such a :math:`y` exists at all is the place-invariant
computation, and a separate increment.

**A ``False`` is not a diagnosis.** The function returns a bare :class:`bool`.
It knows which transition failed to balance and by how much, but does not
report it yet.

Full API
--------

Every function, with its parameters and the exceptions it raises, is in the
:doc:`API reference </api/masafi_sim_petri.analysis.conservation>`.
