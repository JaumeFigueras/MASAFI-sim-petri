Place/Transition Petri nets
===========================

The Place/Transition net, or P/T net, is the base model of this library. Every
other class of net in the library is an extension of it, so this is the section
to read first.

.. toctree::
   :maxdepth: 2

   place
   transition
   examples/index

What is a Petri net?
--------------------

A Petri net is a directed bipartite graph with two kinds of node:

**Places**
   The passive nodes. A place holds a whole number of *tokens* and represents a
   condition: a buffer with three items in it, a machine that is idle, a
   customer waiting in a queue.

**Transitions**
   The active nodes. A transition represents an event that may happen: an item
   being taken from a buffer, a machine starting a job, a customer being
   served.

**Arcs**
   The edges. Because the graph is bipartite, an arc always joins a place to a
   transition or a transition to a place, never two nodes of the same kind. An
   arc carries a *weight*: the number of tokens it moves.

The distribution of tokens over the places is the *marking*, and the marking is
the state of the net. A net therefore separates two things that are easy to
confuse: the fixed structure of the system, which is the graph, and the
changing state of the system, which is the marking.

Formally a P/T net is a tuple :math:`N = (P, T, F, W, M_0)` where :math:`P` is
the set of places, :math:`T` the set of transitions, :math:`F \subseteq
(P \times T) \cup (T \times P)` the arcs, :math:`W : F \rightarrow
\mathbb{N}^{+}` the arc weights, and :math:`M_0 : P \rightarrow \mathbb{N}` the
initial marking.

The firing rule
---------------

The whole behaviour of a P/T net comes from one rule.

A transition is **enabled** when every place with an arc into it holds at least
as many tokens as that arc's weight. An enabled transition may **fire**, and
firing does two things atomically:

1. it removes ``weight`` tokens from each of its input places;
2. it adds ``weight`` tokens to each of its output places.

Nothing else changes. A transition that is not enabled cannot fire, and firing
is the only way a marking changes.

Two consequences are worth stating plainly, because they are what make the
model useful:

*Tokens are not conserved.* A transition with one input arc of weight 1 and two
output arcs of weight 1 turns one token into two. This is how forking, and
therefore concurrency, is expressed.

*Firing is local.* A transition only ever looks at the places directly attached
to it. There is no global scheduler deciding what happens next, which is why a
net describes a distributed system as naturally as a centralised one.

Choices made in this library
----------------------------

A P/T net admits several equally valid conventions. This library commits to
these:

**Interleaved firing**
   One enabled transition fires at a time. When several transitions are enabled
   simultaneously the net does not fire them all at once; each possible choice
   leads to a different successor marking, and it is exactly that branching
   that the reachability graph enumerates. The alternative, *maximal step*
   semantics, fires every enabled transition together and yields a different
   and coarser state space.

**Weighted arcs**
   Every arc carries a weight, defaulting to 1. Enabling and firing always
   respect it.

**Unbounded places**
   No place has a capacity. A marking may grow without limit, which means
   boundedness is a *property to be analysed* rather than a constraint imposed
   by construction. A net that grows without bound is telling you something
   about the system it models, and silently capping it would hide that.

Why Petri nets for discrete event systems?
------------------------------------------

A discrete event system is one whose state changes at distinct instants, in
response to events, rather than continuously: a production line, a
communication protocol, a traffic junction, an operating system scheduler.
Petri nets suit them for several reasons that are hard to get from other
formalisms at the same time.

**Concurrency is explicit, not encoded.** Two transitions that share no input
place are independent, and the model says so structurally — you can see it in
the graph. In a state machine the same situation has to be encoded as an
interleaving of states, and the number of states multiplies. A net stays the
size of the system; only its state space grows.

**Synchronisation is a single node.** A transition with two input places fires
only when both hold tokens. That one construct expresses a rendezvous, a join
after a fork, a resource being acquired only when every prerequisite is
available. The classic patterns of discrete event systems — mutual exclusion,
bounded buffers, producer/consumer, readers and writers — are each a few nodes.

**The model is graphical and formal at the same time.** The picture an engineer
draws on a whiteboard *is* the mathematical object. There is no translation
step in which meaning is lost, which matters when a domain expert and an
analyst have to agree on a model.

**Properties can be proven, not merely observed.** This is the decisive
advantage over ad hoc simulation. Simulating a system shows you what happened
in the runs you tried. Analysing a net can show you what can happen in *every*
possible run:

*Reachability*
   Which markings can the net ever reach from its initial marking? Building the
   graph of all reachable markings answers most other questions.

*Boundedness*
   Does any place accumulate tokens without limit? An unbounded place usually
   means a queue that grows forever, or a buffer that was never dimensioned.

*Liveness*
   Can every transition still eventually fire, from every reachable marking? A
   transition that can never fire again is dead code in the model.

*Deadlock*
   Is there a reachable marking in which no transition at all is enabled? The
   system has stopped and cannot restart.

A simulation can miss a deadlock that occurs in one interleaving out of
thousands. Reachability analysis cannot.

**Extension without changing the base.** Timed nets attach durations to
transitions so that the model answers questions about throughput and delay;
coloured nets let tokens carry values so that one net describes many similar
processes without duplicating structure. Both keep the firing rule above.

A small example
---------------

Two machines share a single tool. Each machine must acquire the tool before
working and release it afterwards::

    (idle_1) ──► [take_1] ──► (working_1) ──► [release_1] ──┐
        ▲            ▲                                      │
        │            │                                      │
        └────────────┼──────────────────────────────────────┘
                     │
                  (tool)  ◄── one token: the single shared tool
                     │
        ┌────────────┼──────────────────────────────────────┐
        ▼            ▼                                      │
    (idle_2) ──► [take_2] ──► (working_2) ──► [release_2] ──┘

Round brackets are places, square brackets transitions. The place ``tool``
holds one token. ``take_1`` needs a token from both ``idle_1`` and ``tool``, so
it can only fire while the tool is free; the same holds for ``take_2``. Once
either has fired the token in ``tool`` is gone and the other machine must wait.

Mutual exclusion is not a rule bolted onto the model. It is a consequence of
there being one token in one place.

The classes
-----------

The model is split into one class per concept, each in its own module under
:mod:`masafi_sim_petri.petri_net`.

:class:`~masafi_sim_petri.petri_net.place.Place`
   A named holder of tokens. Knows its current marking and the initial marking
   it is reset to. **Implemented** — see :doc:`place`.

:class:`~masafi_sim_petri.petri_net.transition.Transition`
   An event. Enabled when its input places can supply the weights of the arcs
   reaching it; firing moves the tokens. Carries no state of its own in a P/T
   net. **Implemented** — see :doc:`transition`.

``Arc``
   A weighted, directed connection between a place and a transition. *Planned.*

``ArcInhibition``
   An inhibitor arc, which enables its transition only when the place is
   *empty*. A genuine extension rather than part of the base model: it makes
   the formalism strictly more expressive, and changes how the reachability
   graph must be built. *Planned.*

``Token``
   The token itself. A P/T net does not need it — a marking is just a count —
   so it becomes meaningful with coloured nets, where a token carries a value.
   *Planned.*

``PetriNet``
   The net: it owns the places, the transitions and, importantly, the
   connectivity. Places and transitions hold no references to their arcs, so
   the model is an acyclic object graph and each class can be tested on its
   own. Enabling and firing are therefore operations on the net. *Planned.*

Keeping connectivity in one place also keeps the model free of any simulation
machinery: the same net object can be handed to the reachability analysis in
:mod:`masafi_sim_petri.analysis` or to the SimPy-driven engine in
:mod:`masafi_sim_petri.simulation`, and neither the places nor the transitions
need to know which.
