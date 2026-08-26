Boundedness and safeness
========================

.. currentmodule:: masafi_sim_petri.analysis.boundedness

A place in a P/T net is unbounded by design: nothing in the model stops it
from accumulating tokens. Whether a *particular* net keeps its places bounded
is therefore not a structural property that can be read off the drawing — it
depends on the initial marking and on which firing sequences that marking
allows.

A net is **k-bounded** when no reachable marking puts more than :math:`k`
tokens in any place, and **safe** when it is 1-bounded. Safeness is the case
worth naming, because it changes how a place may be read. In a safe net a
place is a *condition* — the machine is idle, the resource is free, the buffer
slot is available — that either holds or does not. In an unsafe net the same
place is a *counter*, and every model built on the reading "this token is the
machine" is quietly wrong.

Boundedness also decides what else can be asked of the net. A bounded net has
a finite reachable state space, so questions about all of its behaviours can be
settled by enumeration. An unbounded one has an infinite state space, and the
same questions need an entirely different treatment.

The three functions
-------------------

:func:`is_k_bounded`
   Does any reachable marking exceed :math:`k` tokens in a place?

:func:`is_safe`
   The same question for :math:`k = 1`, which is the one usually asked.

:func:`is_bounded`
   Is there *any* :math:`k` that holds? Asked without one to test against,
   which changes the algorithm entirely — see
   :ref:`boundedness-without-a-bound`.

.. doctest::

   >>> from masafi_sim_petri import Arc, PetriNet, Place, Transition
   >>> from masafi_sim_petri.analysis import is_k_bounded, is_safe

A single token circulating between two places is the archetype of a safe net:
whatever fires, the token is in exactly one of them.

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
   >>> is_safe(net)
   True

Which of the two markings is asked about
----------------------------------------

A net carries two markings, and only one of them is the question.
:attr:`~masafi_sim_petri.petri_net.petri_net.PetriNet.initial_marking` is
:math:`M_0`, fixed when the places were built;
:attr:`~masafi_sim_petri.petri_net.petri_net.PetriNet.marking` is where the net
stands right now, and every firing moves it. **Both functions explore from**
:math:`M_0`.

Putting a second token into the running net therefore changes the state
without changing the question, and the two attributes say so plainly:

.. doctest::

   >>> net.marking = (2, 0)
   >>> net.marking
   (2, 0)
   >>> net.initial_marking
   (1, 0)
   >>> is_safe(net)
   True

The ``True`` is the answer for :math:`M_0 = (1, 0)`, which is still the
marking the net was built with. Give the same structure two tokens *at
construction* and :math:`M_0` itself moves, so the answer moves with it:

.. doctest::

   >>> net = PetriNet(
   ...     places=[Place('idle', initial_marking=2), Place('busy')],
   ...     transitions=[Transition('start'), Transition('stop')],
   ... )
   >>> _ = net.add_arc(Arc(net.place('idle'), net.transition('start')))
   >>> _ = net.add_arc(Arc(net.transition('start'), net.place('busy')))
   >>> _ = net.add_arc(Arc(net.place('busy'), net.transition('stop')))
   >>> _ = net.add_arc(Arc(net.transition('stop'), net.place('idle')))
   >>> net.initial_marking
   (2, 0)
   >>> is_safe(net)
   False
   >>> is_k_bounded(net, 2)
   True

Not one arc differs between the two nets. Boundedness is a property of the
structure *and* of :math:`M_0`, never of the structure alone.

Weights break safeness in the more obvious way — a transition can deliver two
tokens in a single firing:

.. doctest::

   >>> net = PetriNet()
   >>> source = net.add_place(Place('source', initial_marking=1))
   >>> target = net.add_place(Place('target'))
   >>> move = net.add_transition(Transition('move'))
   >>> _ = net.add_arc(Arc(source, move))
   >>> _ = net.add_arc(Arc(move, target, weight=2))
   >>> is_safe(net)
   False

Why a truncated search is enough
--------------------------------

The implementation of the first two is a breadth-first exploration of the
reachable markings
from :math:`M_0`: take a marking off the queue, fire each transition enabled
in it, and queue every successor not seen before. It is the reachability graph
construction, without building the graph.

On an unbounded net that exploration would never end — the reachable set is
infinite. It ends here, and the reason is worth stating precisely, because it
is what makes this analysis implementable before any coverability machinery
exists:

.. epigraph::

   Every marking the search stores has all of its entries in
   :math:`\{0, \dots, k\}`, so there are at most :math:`(k+1)^{|P|}` of them.
   The one kind of marking that is *not* stored — a successor exceeding
   :math:`k` — is exactly the witness the question asks for, and finding it
   ends the search.

So the search is self-truncating. Either it exhausts a finite set and the
answer is ``True``, or it meets a marking that exceeds the bound and the
answer is ``False``. Unboundedness is what makes it stop early, not what makes
it run forever. The answer is exact in both cases: no approximation, no bound
on the search depth, nothing to tune.

The cost is the flip side of the same argument. A safe net with :math:`|P|`
places can have up to :math:`2^{|P|}` reachable markings, and the search may
have to visit all of them before answering ``True``. Deciding safeness is
PSPACE-hard for P/T nets in general; a finite search is not a cheap one.

.. _boundedness-without-a-bound:

Boundedness without a bound
---------------------------

:func:`is_bounded` asks whether *some* :math:`k` holds. That sounds like the
same question and is not, because the whole of the argument above rests on
having a :math:`k` to exceed. With none, nothing truncates the search, and on
an unbounded net a plain exploration runs for ever.

The way out is the observation the Karp-Miller construction is built on:

.. epigraph::

   If a marking :math:`M''` reachable from a marking :math:`M'` covers it
   strictly — :math:`M'' \ge M'` in every place, and :math:`M'' \ne M'` —
   then the firing sequence leading from :math:`M'` to :math:`M''` may be
   repeated for ever. It needs no more tokens the second time than it needed
   the first, and each round leaves the surplus of the previous one behind.
   The net is unbounded.

So the search no longer looks at how many tokens a marking holds. It looks at
how a marking compares with the markings on the path back to the root, which
is exactly the set of markings it is reachable *from*. A strict cover ends the
search with ``False``; anything already seen is not expanded again; and if the
work runs out, every reachable marking has been visited and they were finitely
many.

Termination is no longer a counting argument, since there is nothing to count.
It is this: a net branches finitely, so an infinite search tree would have an
infinite path (Koenig), and an infinite sequence of vectors over the naturals
always contains a pair :math:`M_i \le M_j` with :math:`i < j` (Dickson). That
pair is either a repeat, which is not expanded, or a strict cover, which stops
the search. Neither survives on a path that goes on for ever, so no such path
exists and the search always ends.

.. doctest::

   >>> from masafi_sim_petri.analysis import is_bounded

A producer that borrows a token and gives it back is never blocked, so the
buffer it feeds grows without limit — and adding a consumer does not help,
since nothing forces the producer to wait for it:

.. doctest::

   >>> net = PetriNet()
   >>> running = net.add_place(Place('running', initial_marking=1))
   >>> buffer = net.add_place(Place('buffer'))
   >>> produce = net.add_transition(Transition('produce'))
   >>> consume = net.add_transition(Transition('consume'))
   >>> _ = net.add_arc(Arc(running, produce))
   >>> _ = net.add_arc(Arc(produce, running))
   >>> _ = net.add_arc(Arc(produce, buffer))
   >>> _ = net.add_arc(Arc(buffer, consume))
   >>> is_bounded(net)
   False

Modelling the buffer as *finite* is what bounds it. A second place counts the
free slots, and the producer must take one to fire:

.. doctest::

   >>> net = PetriNet()
   >>> free = net.add_place(Place('free', initial_marking=3))
   >>> buffer = net.add_place(Place('buffer'))
   >>> produce = net.add_transition(Transition('produce'))
   >>> consume = net.add_transition(Transition('consume'))
   >>> _ = net.add_arc(Arc(free, produce))
   >>> _ = net.add_arc(Arc(produce, buffer))
   >>> _ = net.add_arc(Arc(buffer, consume))
   >>> _ = net.add_arc(Arc(consume, free))
   >>> is_bounded(net)
   True

The comparison is against ancestors, and only against ancestors. Two markings
on different branches may well be comparable without anything being pumpable:
neither is reachable from the other, so there is no sequence to repeat.
Comparing a marking with everything already visited would report unboundedness
on nets that are perfectly bounded.

What it is not
--------------

**It is not the coverability graph.** Deciding boundedness needs the covering
rule, but not the acceleration step that replaces a pumped place by
:math:`\omega`, and not the graph that step builds. That is why this analysis
can exist before ``coverability.py`` does, and why none of the decisions that
module still owes — how :math:`\omega` is represented, which acceleration
variant is the default — had to be taken to write it. What it costs is that a
bounded net is explored in full, with no :math:`\omega` to collapse a family
of markings into one node.

**A ``True`` carries no bound.** :func:`is_bounded` says that some :math:`k`
exists, not which. The smallest one can be looked for with
:func:`is_k_bounded` afterwards, once it is known that the question has an
answer.

**It is not cheap.** Boundedness is EXPSPACE-hard for P/T nets (Lipton), with
a matching upper bound (Rackoff). Termination is a guarantee that the answer
arrives, not that it arrives soon.

What none of them answer
------------------------

**Structural boundedness is a different question.** These functions answer for
the initial marking the net carries. A net can be bounded for one :math:`M_0`
and unbounded for another, and proving boundedness for *every* initial marking
is a question about the incidence matrix, not about a search. A sufficient
structural condition is already available: a
:doc:`strictly conservative <conservation>` net is bounded for every initial
marking, and no search is involved at all.

**A ``False`` is not a diagnosis.** The functions return a bare :class:`bool`.
They know which firing sequence overflowed which place, or which pair of
markings pumps, at the moment they stop, but they do not report it yet.

Leaving the net alone
---------------------

All three functions fire transitions on the net they are given — the firing rule
lives in :class:`~masafi_sim_petri.petri_net.petri_net.PetriNet` and is not
reimplemented here, so there is no second copy of the semantics to drift out of
step. They restore the marking the net had on entry before returning, on every
path out including a failed argument check, so from the caller's side the
analysis is a pure query.

.. doctest::

   >>> net = PetriNet()
   >>> p1 = net.add_place(Place('p1', initial_marking=1))
   >>> t1 = net.add_transition(Transition('t1'))
   >>> _ = net.add_arc(Arc(p1, t1))
   >>> net.marking
   (1,)
   >>> is_safe(net)
   True
   >>> net.marking
   (1,)

Full API
--------

Every function, with its parameters and the exceptions it raises, is in the
:doc:`API reference </api/masafi_sim_petri.analysis.boundedness>`.
