The PetriNet class
==================

:class:`~masafi_sim_petri.petri_net.petri_net.PetriNet` is the net itself. It
owns the places, the transitions and — the part that matters most — the arcs
that join them.

Building a net
--------------

Nodes are created and then added. Each ``add_`` method returns what it was
given, so a node can be bound to a name and wired in the same breath:

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
   >>> print(net)
   PetriNet with 3 places, 1 transitions and 4 arcs

This is the queue-and-server pattern: ``serve`` takes a customer from
``waiting``, borrows the single token in ``server`` and gives it back. While
that token is out, no second ``serve`` could start — which is how a net says
"one at a time" without any construct for saying it.

Why the net holds the connectivity
----------------------------------

A place does not know its arcs, and neither does a transition. The net holds
them all. This is the central structural decision of the library, and
everything else follows from it.

**One thing to keep consistent.** Connectivity recorded on the nodes *and* in
the net is connectivity recorded twice, and the two can disagree. When an
editor adds and removes arcs interactively, that divergence is not a
theoretical risk.

**An acyclic object graph.** Nodes point at nothing; arcs point at their two
nodes; the net points at everything. A place can be constructed, tested and
reasoned about entirely on its own.

**The model stays free of machinery.** Because enabling and firing are
operations of the net, neither places nor transitions need to know whether they
are being explored by a reachability analysis or driven by a discrete event
scheduler. The same net object serves both.

The cost is that a transition cannot answer questions about itself. There is no
``transition.is_enabled()``; it is ``net.is_enabled(transition)``. A transition
genuinely does not know which arcs reach it, so the shorter spelling would be a
convenience hiding a lookup that has to happen anyway.

What the net refuses
--------------------

:class:`~masafi_sim_petri.petri_net.arc.Arc` already enforces what it can see:
that an arc joins a place and a transition. The rules that need a view of the
whole net are enforced here.

**A node cannot be added twice**, and **two places cannot share a name**, nor
two transitions. Names identify a node within a net, so duplicates would make
lookup ambiguous and the marking vector wrong.

A place and a transition *may* share a name. They are separate sets, indexed
separately, and there is no lookup that would have to choose between them:

.. doctest::

   >>> ambiguous = PetriNet()
   >>> _ = ambiguous.add_place(Place('n'))
   >>> _ = ambiguous.add_transition(Transition('n'))
   >>> ambiguous.place('n').name, ambiguous.transition('n').name
   ('n', 'n')

**Both endpoints of an arc must already be in the net.** An arc reaching a node
the net does not hold would quietly join two nets into one object graph:

.. doctest::

   >>> net.add_arc(Arc(Place('elsewhere'), serve))
   Traceback (most recent call last):
       ...
   ValueError: Place 'elsewhere' is not in the net, so it cannot be used by an arc of this net

**Two arcs cannot join the same pair in the same direction.** Two input arcs
from ``p`` to ``t`` of weights 2 and 3 are indistinguishable, under the firing
rule, from one arc of weight 5 — so allowing both would give one situation two
representations, and every piece of code reading the net would have to sum them:

.. doctest::

   >>> net.add_arc(Arc(waiting, serve, weight=2))
   Traceback (most recent call last):
       ...
   ValueError: An arc already joins place 'waiting' to transition 'serve'; change its weight instead of adding a second arc

The two *directions* between the same pair remain distinct, because they do
different things — that is the self-loop above, and it is four arcs in this net
rather than three.

Reading the structure
---------------------

``places``, ``transitions`` and ``arcs`` return tuples, always in the order
things were added. That order is not cosmetic: it is what makes the marking
vector mean the same thing from one run to the next, and what makes a
reachability graph reproducible rather than merely correct.

Nodes can be found by name, and the arcs of a transition by direction:

.. doctest::

   >>> [arc.place.name for arc in net.input_arcs(net.transition('serve'))]
   ['waiting', 'server']
   >>> [arc.place.name for arc in net.output_arcs(net.transition('serve'))]
   ['served', 'server']

One more index is kept, and it exists for performance rather than for
expressiveness:

.. doctest::

   >>> net.transitions_affected_by(waiting)
   (Transition(name='serve'),)
   >>> net.transitions_affected_by(served)
   ()

``transitions_affected_by`` answers *which transitions could have changed their
enabling because this place changed*. After a firing, only the places touched
by that firing changed, so only the transitions those places feed need
re-examining — the rest of the net provably cannot have moved. Without this,
every step of a simulation would rescan every transition, and the cost of a
step would grow with the size of the net instead of with the size of the
neighbourhood. ``served`` is only ever produced into, so it gates nothing and
the answer is empty.

The marking vector
------------------

The state of a net is the marking, and the net reports it as a tuple of counts,
positionally, in place order:

.. doctest::

   >>> net.marking
   (2, 1, 0)

A tuple rather than a mapping, for one specific reason: it is hashable. A
reachability graph identifies a node *by* its marking — two states are the same
state exactly when their markings are equal — so the marking has to work as a
dictionary key and a set member.

The vector is read from the places each time rather than cached, so it cannot
drift out of step with them:

.. doctest::

   >>> waiting.remove_tokens(1)
   >>> net.marking
   (1, 1, 0)

It can also be assigned, which writes straight through to the places without
consulting the firing rule. This is for analysis, which explores markings out
of order and must be able to put the net back into a state it has already
visited:

.. doctest::

   >>> net.marking = (0, 1, 2)
   >>> served.marking
   2

Assignment validates the whole vector — the right number of entries, none of
them negative — *before* writing any of it, so a rejected assignment leaves the
net exactly as it was rather than half-updated:

.. doctest::

   >>> net.marking = (5, -1, 0)
   Traceback (most recent call last):
       ...
   ValueError: The marking of a place cannot be negative, got -1 for place 'server'
   >>> net.marking
   (0, 1, 2)

Running the net
---------------

A transition is **enabled** when every place with an arc into it holds at least
the weight of that arc:

.. doctest::

   >>> net.reset()
   >>> net.is_enabled(serve)
   True
   >>> net.enabled_transitions()
   (Transition(name='serve'),)

Firing removes the weight of each input arc from its place, then adds the
weight of each output arc to its place:

.. doctest::

   >>> net.marking
   (2, 1, 0)
   >>> net.fire(serve)
   >>> net.marking
   (1, 1, 1)

One customer left ``waiting`` and arrived in ``served``. The token in
``server`` was taken and given back, so it reads as unchanged.

Consumption happens before production, and that order is what makes the self
loop behave. Producing first would momentarily put two tokens into a place
built to hold one; taking first and returning afterwards never does. No marking
between the two halves is observable in any case — a firing is one step.

Running a net is then a loop:

.. doctest::

   >>> while net.enabled_transitions():
   ...     net.fire(net.enabled_transitions()[0])
   >>> net.marking
   (0, 1, 2)

The queue has drained and nothing is enabled any more. A marking in which no
transition at all can fire is a **deadlock**; here it is simply the end of the
work, but in a net that is meant to keep running it is a defect, and one that
reachability analysis finds without having to be lucky.

Firing is checked, not trusted
------------------------------

Firing a transition that is not enabled raises, rather than doing nothing or
firing anyway:

.. doctest::

   >>> net.fire(serve)
   Traceback (most recent call last):
       ...
   ValueError: Transition 'serve' is not enabled and cannot fire

The caller is expected to have consulted ``is_enabled`` or
``enabled_transitions``. Reaching ``fire`` with a disabled transition means the
rule that chose it was wrong, and a marking that silently drifts is far harder
to debug than an exception at the point of the mistake. The check runs before
any token is moved, so a rejected firing leaves the net exactly as it was.

Choice, and why one transition fires at a time
-----------------------------------------------

When several transitions are enabled at once, this library fires exactly one of
them — the *interleaved* semantics. ``enabled_transitions`` returns all the
candidates and the caller picks:

.. doctest::

   >>> conflict = PetriNet()
   >>> token = conflict.add_place(Place('token', initial_marking=1))
   >>> left = conflict.add_transition(Transition('left'))
   >>> right = conflict.add_transition(Transition('right'))
   >>> _ = conflict.add_arc(Arc(token, left))
   >>> _ = conflict.add_arc(Arc(token, right))
   >>> len(conflict.enabled_transitions())
   2
   >>> conflict.fire(left)
   >>> conflict.enabled_transitions()
   ()

Both were enabled; firing one took the single token and disabled the other.
This is a **conflict**, and it is not a flaw in the model — it is the model
faithfully representing a real choice, such as which of two processes acquires
a lock.

Firing them both together instead would be *maximal step* semantics, and it
would be wrong here: there is one token and two claims on it. More generally,
interleaving is what lets the reachability graph branch, and it is that
branching that exposes the orderings in which a system misbehaves. A simulator
that always resolved conflicts the same way would explore one path through the
system and report it as the system's behaviour.

Because ``enabled_transitions`` returns candidates in a stable order, the
*policy* for choosing between them sits with the caller — round robin, random
with a seed, priority, or exhaustive exploration by the reachability analysis.
The net does not decide.

Starting again
--------------

``initial_marking`` is :math:`M_0`, read from the places' own initial markings,
and ``reset()`` returns the net to it:

.. doctest::

   >>> net.initial_marking
   (2, 1, 0)
   >>> net.reset()
   >>> net.marking
   (2, 1, 0)

:math:`M_0` is needed twice over: a simulation that is run repeatedly must
start each run from the same state, and the reachability graph is rooted at it.

.. _renaming:

Renaming a node
---------------

An editor renames things. A place drawn as ``p1`` becomes ``waiting`` once the
model takes shape, and the library has to allow that without the net coming
apart.

The name cannot be assigned on the node itself, because the net indexes its
nodes by name and would be left holding the old key. Renaming goes through the
net, which changes the node and its own index together:

.. doctest::

   >>> net.rename_place(waiting, 'queue')
   >>> net.place('queue') is waiting
   True
   >>> net.place('waiting')
   Traceback (most recent call last):
       ...
   KeyError: "The net has no place named 'waiting'"

Transitions rename the same way, with
:meth:`~masafi_sim_petri.petri_net.petri_net.PetriNet.rename_transition`.

Renaming does not reorder anything
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This is the guarantee that matters, and it is the reason the net keeps its
order and its lookup in two separate structures rather than in one dictionary
keyed by name.

Place order is what gives the marking vector its meaning: the second entry is
the second place *added*, not the second alphabetically or the second by any
other measure. Had the name index also been the record of order, renaming
would have moved the renamed place to the end of it — and every marking
captured before the rename would silently start referring to different places.
A reachability graph built across such a rename would be wrong in a way nothing
would report.

So the net holds the places in a list, which a rename never touches, and
indexes them in a dictionary, which is the only thing a rename edits:

.. doctest::

   >>> [place.name for place in net.places]
   ['queue', 'server', 'served']
   >>> net.marking
   (2, 1, 0)

The renamed place is still first, and the marking vector still means what it
meant. The same holds for transitions, whose order decides the order
:meth:`~masafi_sim_petri.petri_net.petri_net.PetriNet.enabled_transitions`
reports them in.

Arcs are unaffected for a different reason: they hold references to the node
objects, not to their names, so connectivity cannot be broken by a rename at
all.

What renaming refuses
~~~~~~~~~~~~~~~~~~~~~

Names stay unique, so a name already taken by another node of the same kind is
rejected, and the net is left exactly as it was:

.. doctest::

   >>> net.rename_place(net.place('queue'), 'served')
   Traceback (most recent call last):
       ...
   ValueError: The net already has a place named 'served'
   >>> net.place('queue').name
   'queue'

Renaming a node to the name it already has is a no-op rather than a clash with
itself, and a blank name is refused just as it is at construction. The freed
name becomes available immediately, so two places can swap names in two steps
through a temporary one.

Full API
--------

Every method, with its parameters and the exceptions it raises, is in the
:doc:`API reference </api/masafi_sim_petri.petri_net.petri_net>`.
