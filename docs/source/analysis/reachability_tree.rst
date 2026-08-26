The reachability tree
=====================

.. currentmodule:: masafi_sim_petri.analysis.marking_tree

The analyses so far answer a question with a :class:`bool`. The tree is the
first result that is an *object*: it shows every marking the net can reach and
every firing sequence that reaches it, and the yes-or-no answers can be read
off it afterwards.

It is built the way it is drawn. The root is :math:`M_0`. A node is expanded by
firing each of its enabled transitions in turn, one child per transition, and
the construction goes level by level — a level is finished before the next is
begun. Left to right, the children follow the transition names, so the leftmost
branch of a node is ``t1`` and the rightmost is whichever name comes last.

.. doctest::

   >>> from masafi_sim_petri import Arc, PetriNet, Place, Transition
   >>> from masafi_sim_petri.analysis import NodeLabel, ReachabilityTree

Take a net with a choice: the token in ``p1`` can go to ``p2``, from where
``t3`` brings it back, or to ``p3``, where nothing is enabled.

.. doctest::

   >>> net = PetriNet()
   >>> p1 = net.add_place(Place('p1', initial_marking=1))
   >>> p2 = net.add_place(Place('p2'))
   >>> p3 = net.add_place(Place('p3'))
   >>> t1 = net.add_transition(Transition('t1'))
   >>> t2 = net.add_transition(Transition('t2'))
   >>> t3 = net.add_transition(Transition('t3'))
   >>> _ = net.add_arc(Arc(p1, t1))
   >>> _ = net.add_arc(Arc(t1, p2))
   >>> _ = net.add_arc(Arc(p1, t2))
   >>> _ = net.add_arc(Arc(t2, p3))
   >>> _ = net.add_arc(Arc(p2, t3))
   >>> _ = net.add_arc(Arc(t3, p1))
   >>> tree = ReachabilityTree(net)
   >>> print(tree)
   (1, 0, 0)
   ├── t1 -> (0, 1, 0)
   │   └── t3 -> (1, 0, 0) [old]
   └── t2 -> (0, 0, 1) [deadlock]

Why a branch stops
------------------

A branch ends for one of three reasons, and the :class:`NodeLabel` of the leaf
says which. Two of them are facts about the net:

:attr:`~NodeLabel.OLD`
   The marking is already in the tree. Expanding it again would rebuild a
   subtree that has been built once, and the branch would never end in a net
   with a cycle. This is what makes the tree of a bounded net finite.

:attr:`~NodeLabel.DEADLOCK`
   No transition is enabled. The net has stopped, and the firing sequence from
   the root is a sequence that kills it.

The third is a fact about the question asked rather than about the net —
:attr:`~NodeLabel.TRUNCATED`, below. Anything that was expanded is
:attr:`~NodeLabel.INTERNAL`.

.. doctest::

   >>> for node in tree.leaves():
   ...     print(node.label, node.marking)
   deadlock (0, 0, 1)
   old (1, 0, 0)

A deadlock node carries the way it was reached, which is the useful half of
knowing that a deadlock exists:

.. doctest::

   >>> deadlock, = tree.deadlocks()
   >>> [transition.name for transition in deadlock.firing_sequence()]
   ['t2']

Two conventions worth stating
-----------------------------

**Old is decided against the whole tree, not against the path back to the
root.** A marking counts as old when it appears anywhere in the part of the
tree already built, so every distinct reachable marking is expanded exactly
once. Some presentations compare only against the ancestors, which gives a
larger tree with the same set of markings at its leaves.

**Old beats deadlock.** A dead marking reached down two branches is a deadlock
the first time and old the second, so :meth:`~MarkingTree.deadlocks`
reports each dead marking once rather than once per sequence that reaches it.

.. doctest::

   >>> net = PetriNet()
   >>> p1 = net.add_place(Place('p1', initial_marking=1))
   >>> p2 = net.add_place(Place('p2'))
   >>> t1 = net.add_transition(Transition('t1'))
   >>> t2 = net.add_transition(Transition('t2'))
   >>> _ = net.add_arc(Arc(p1, t1))
   >>> _ = net.add_arc(Arc(t1, p2))
   >>> _ = net.add_arc(Arc(p1, t2))
   >>> _ = net.add_arc(Arc(t2, p2))
   >>> print(ReachabilityTree(net))
   (1, 0)
   ├── t1 -> (0, 1) [deadlock]
   └── t2 -> (0, 1) [old]

Occurrences, not states
-----------------------

The same marking appears at as many nodes as there are firing sequences
reaching it. That is the difference between the tree and the reachability
graph, and it is the reason the tree is worth having: in the tree a marking is
an *occurrence*, identified by the path that reached it, and the path is the
part you want when you are explaining why the net does something. In the graph
it is a *state*, identified by its vector, and the paths are gone.

.. doctest::

   >>> len(tree)
   4
   >>> tree.markings()
   ((1, 0, 0), (0, 1, 0), (0, 0, 1))

Ordering names the way they are read
------------------------------------

Branches are ordered by transition name, in *natural* order: a run of digits
inside a name is compared as a number. Plain alphabetical order would put
``t10`` immediately after ``t1``, which is not how anyone draws the tree.

.. doctest::

   >>> net = PetriNet()
   >>> p1 = net.add_place(Place('p1', initial_marking=1))
   >>> for number in (11, 2, 10, 1):
   ...     transition = net.add_transition(Transition(f't{number}'))
   ...     _ = net.add_arc(Arc(p1, transition))
   >>> [child.incoming_transition.name for child in ReachabilityTree(net).root.children]
   ['t1', 't2', 't10', 't11']

Note this is a deliberate departure from the rest of the library, where
:meth:`~masafi_sim_petri.petri_net.petri_net.PetriNet.enabled_transitions`
returns transitions in the order they were added to the net. The tree is drawn,
so the tree sorts.

Nets whose tree does not fit
----------------------------

An unbounded net reaches infinitely many markings, so its reachability tree is
an infinite object. There is no finite tree to return, and two parameters
decide what happens instead.

``refuse_unbounded``, on by default, watches for the covering rule that
:func:`~masafi_sim_petri.analysis.boundedness.is_bounded` uses: a marking that
strictly covers one of its own ancestors can be pumped for ever. Finding one
raises :exc:`UnboundedNetError` rather than returning a fragment as though it
were the tree.

.. doctest::

   >>> from masafi_sim_petri.analysis import UnboundedNetError
   >>> net = PetriNet()
   >>> running = net.add_place(Place('running', initial_marking=1))
   >>> buffer = net.add_place(Place('buffer'))
   >>> produce = net.add_transition(Transition('produce'))
   >>> _ = net.add_arc(Arc(running, produce))
   >>> _ = net.add_arc(Arc(produce, running))
   >>> _ = net.add_arc(Arc(produce, buffer))
   >>> ReachabilityTree(net)
   Traceback (most recent call last):
       ...
   masafi_sim_petri.analysis.reachability_tree.UnboundedNetError: Marking (1, 1) strictly covers an earlier marking on the same path, so the net is unbounded and its reachability tree is infinite

``max_levels`` caps how deep the tree goes, the root counting as level one. A
node that would have been expanded at the last level is labelled
:attr:`~NodeLabel.TRUNCATED` instead, and that is the one label meaning *the
tree stops here because you said so*. It applies to a large bounded net just as
much as to an unbounded one:

.. doctest::

   >>> tree = ReachabilityTree(net, refuse_unbounded=False, max_levels=3)
   >>> print(tree)
   (1, 0)
   └── produce -> (1, 1)
       └── produce -> (1, 2) [truncated]

A truncated tree is still a tree, but it is not *the* tree, and
:attr:`~MarkingTree.is_complete` is what tells the two apart. Read it
before drawing a conclusion from anything the tree does not contain — an empty
:meth:`~MarkingTree.deadlocks` on an incomplete tree is not deadlock
freedom, only the absence of a deadlock in the part that was built.

.. doctest::

   >>> tree.is_complete
   False
   >>> [node.marking for node in tree.truncated_nodes()]
   [(1, 2)]

Dropping the refusal without giving a limit is rejected: with neither, an
unbounded net would build for ever.

.. doctest::

   >>> ReachabilityTree(net, refuse_unbounded=False)
   Traceback (most recent call last):
       ...
   ValueError: Without max_levels, an unbounded net would be built for ever; either give a level limit or leave refuse_unbounded set

Two classes, and why
--------------------

The construction above is one of two that will produce a tree of markings: the
coverability tree builds another, from the same net, by the same breadth-first
walk, and stops its branches for reasons of its own. Everything that is not the
construction — a node with its marking, level, parent and label, and a finished
tree with its nodes, its leaves, its deadlocks and its drawing — is therefore
shared, and lives in
:mod:`~masafi_sim_petri.analysis.marking_tree` as :class:`MarkingTreeNode`,
:class:`MarkingTree` and :class:`NodeLabel`.

:class:`~masafi_sim_petri.analysis.reachability_tree.ReachabilityTree` is a
:class:`MarkingTree` that knows how to fill itself from a net. It adds a
constructor and nothing else: every query on the page above is inherited, and
the coverability tree will inherit the same ones. :exc:`UnboundedNetError` is
shared too, since it is a fact about the net rather than about either tree.

Full API
--------

Every class and method, with its parameters and the exceptions it raises, is in
the API reference: the construction in
:doc:`reachability_tree </api/masafi_sim_petri.analysis.reachability_tree>`,
the nodes, labels and queries in
:doc:`marking_tree </api/masafi_sim_petri.analysis.marking_tree>`.
