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

The two functions
-----------------

:func:`is_k_bounded`
   Does any reachable marking exceed :math:`k` tokens in a place?

:func:`is_safe`
   The same question for :math:`k = 1`, which is the one usually asked.

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

Add a second token and the same structure is no longer safe, without a single
arc changing. Boundedness is a property of the net *and* its initial marking.

.. doctest::

   >>> net.marking = (2, 0)
   >>> is_safe(net)
   True

That answer looks wrong until you remember which marking the analysis starts
from. Both functions explore from :math:`M_0`, the marking the net was built
with, not from wherever the net happens to stand now — assigning
:attr:`~masafi_sim_petri.petri_net.petri_net.PetriNet.marking` changes the
present state, not the question. Building the net with two tokens is what
makes it unsafe, and it is then 2-bounded instead:

.. doctest::

   >>> net = PetriNet(
   ...     places=[Place('idle', initial_marking=2), Place('busy')],
   ...     transitions=[Transition('start'), Transition('stop')],
   ... )
   >>> _ = net.add_arc(Arc(net.place('idle'), net.transition('start')))
   >>> _ = net.add_arc(Arc(net.transition('start'), net.place('busy')))
   >>> _ = net.add_arc(Arc(net.place('busy'), net.transition('stop')))
   >>> _ = net.add_arc(Arc(net.transition('stop'), net.place('idle')))
   >>> is_safe(net)
   False
   >>> is_k_bounded(net, 2)
   True

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

Why a search is enough
----------------------

The implementation is a breadth-first exploration of the reachable markings
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

What it does not answer
-----------------------

**Structural boundedness is a different question.** These functions answer for
the initial marking the net carries. A net can be bounded for one :math:`M_0`
and unbounded for another, and proving boundedness for *every* initial marking
is a question about the incidence matrix, not about a search.

**A ``False`` is not a diagnosis.** The functions return a bare :class:`bool`.
They know which firing sequence overflowed which place at the moment they stop,
but they do not report it yet.

Leaving the net alone
---------------------

Both functions fire transitions on the net they are given — the firing rule
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
