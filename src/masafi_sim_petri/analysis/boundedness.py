"""Boundedness of a Petri net."""

from __future__ import annotations

from collections import deque

from masafi_sim_petri.petri_net.petri_net import PetriNet
from masafi_sim_petri.petri_net.transition import Transition


def is_k_bounded(net: PetriNet, k: int) -> bool:
    """Test whether no reachable marking puts more than ``k`` tokens in a place.

    The net is explored breadth first from its initial marking, firing every
    enabled transition of every marking found. A successor holding more than
    ``k`` tokens in some place ends the search immediately with ``False``; any
    other successor not seen before is queued for expansion. When the queue
    runs dry, no reachable marking exceeds ``k`` and the net is ``k``-bounded.

    Parameters
    ----------
    net : PetriNet
        Net to analyse. Its marking is left as it was found, whatever the
        answer.
    k : int
        The bound to test for. Must not be negative.

    Returns
    -------
    bool
        ``True`` if every reachable marking holds at most ``k`` tokens in
        every place.

    Raises
    ------
    ValueError
        If ``k`` is negative.

    Notes
    -----
    The search always terminates, even on an unbounded net, and the answer is
    exact rather than an approximation. Both follow from the same observation:
    every marking that is ever stored has all of its entries in
    :math:`\\{0, \\dots, k\\}`, so there are at most :math:`(k+1)^{|P|}` of
    them, and the one kind of marking that is not stored -- the one that
    exceeds the bound -- is precisely the witness that answers the question.
    Unboundedness is what makes the search stop early, not what makes it run
    forever.

    This is boundedness for the initial marking the net carries, which is the
    usual behavioural reading. It says nothing about *structural*
    boundedness, which asks the same question of every initial marking.

    Examples
    --------
    A queue of two customers served one at a time never holds more than two
    tokens in a place:

    >>> from masafi_sim_petri import Arc, PetriNet, Place, Transition
    >>> from masafi_sim_petri.analysis import is_k_bounded
    >>> net = PetriNet()
    >>> waiting = net.add_place(Place('waiting', initial_marking=2))
    >>> served = net.add_place(Place('served'))
    >>> serve = net.add_transition(Transition('serve'))
    >>> _ = net.add_arc(Arc(waiting, serve))
    >>> _ = net.add_arc(Arc(serve, served))
    >>> is_k_bounded(net, 2)
    True
    >>> is_k_bounded(net, 1)
    False

    See Also
    --------
    is_safe : The case ``k = 1``.
    """
    if k < 0:
        raise ValueError(f'The bound cannot be negative, got {k}')
    initial_marking = net.initial_marking
    if any(tokens > k for tokens in initial_marking):
        return False
    saved_marking = net.marking
    try:
        visited: set[tuple[int, ...]] = {initial_marking}
        pending: deque[tuple[int, ...]] = deque([initial_marking])
        while pending:
            marking = pending.popleft()
            net.marking = marking
            for transition in net.enabled_transitions():
                net.marking = marking
                net.fire(transition)
                successor = net.marking
                if any(tokens > k for tokens in successor):
                    return False
                if successor not in visited:
                    visited.add(successor)
                    pending.append(successor)
    finally:
        net.marking = saved_marking
    return True


def is_safe(net: PetriNet) -> bool:
    """Test whether no reachable marking puts more than one token in a place.

    A safe net is a 1-bounded net. Safeness is what lets a place be read as a
    condition that either holds or does not, rather than as a counter, which
    is the reading most modelling patterns rely on: a resource is free or
    taken, a machine is idle or busy.

    Parameters
    ----------
    net : PetriNet
        Net to analyse. Its marking is left as it was found, whatever the
        answer.

    Returns
    -------
    bool
        ``True`` if every reachable marking holds at most one token in every
        place.

    Examples
    --------
    A single token passed around a cycle keeps the net safe:

    >>> from masafi_sim_petri import Arc, PetriNet, Place, Transition
    >>> from masafi_sim_petri.analysis import is_safe
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

    A transition with no input arcs is enabled for ever, so the place it
    feeds is not safe:

    >>> net = PetriNet()
    >>> buffer = net.add_place(Place('buffer'))
    >>> produce = net.add_transition(Transition('produce'))
    >>> _ = net.add_arc(Arc(produce, buffer))
    >>> is_safe(net)
    False

    See Also
    --------
    is_k_bounded : The general test this is the ``k = 1`` case of.
    """
    return is_k_bounded(net, 1)


def is_bounded(net: PetriNet) -> bool:
    """Test whether some bound holds, without being told which one.

    :func:`is_k_bounded` is asked about a bound and can stop as soon as a
    marking exceeds it. Here there is no bound to exceed, so the search needs
    a different reason to stop, and it takes it from the covering rule that
    underlies the Karp-Miller construction:

    .. epigraph::

       If a marking :math:`M''` reachable from a marking :math:`M'` covers it
       strictly -- :math:`M'' \\ge M'` in every place and :math:`M'' \\ne M'`
       -- then the firing sequence that led from :math:`M'` to :math:`M''` can
       be repeated for ever, each round leaving behind the tokens of the
       previous one. The net is unbounded.

    The net is explored depth first, and every marking found is compared with
    the markings on the path back to the root. A marking that strictly covers
    one of its own ancestors ends the search with ``False``; a marking already
    seen anywhere is not expanded again. If the search runs out of work, every
    reachable marking has been visited and they are finitely many, so the net
    is bounded.

    Parameters
    ----------
    net : PetriNet
        Net to analyse. Its marking is left as it was found, whatever the
        answer.

    Returns
    -------
    bool
        ``True`` if some :math:`k` bounds every place over every reachable
        marking.

    Notes
    -----
    The search always terminates, and the argument is no longer the counting
    one that :func:`is_k_bounded` relies on. Suppose it did not terminate.
    A net branches finitely, so by Koenig's lemma an infinite search tree has
    an infinite path, and by Dickson's lemma any infinite sequence of vectors
    over the naturals contains a pair :math:`M_i \\le M_j` with :math:`i < j`.
    That pair is either a repeat, which is not expanded, or a strict cover,
    which ends the search. Neither can occur on a path that goes on for ever,
    so no such path exists.

    Both answers are exact. A strict cover really does pump tokens without
    bound, and an exhausted search really has enumerated the whole reachable
    set.

    What this does *not* do is build the coverability graph. Deciding
    boundedness needs the covering rule, but not the acceleration step that
    replaces a pumped place by :math:`\\omega`, and not the graph that step
    produces. The price is that a bounded net is explored in full, and that
    the answer is a bare ``True`` with no bound attached: the smallest
    :math:`k` is not reported, and can be searched for with
    :func:`is_k_bounded` once boundedness is known.

    Boundedness is EXPSPACE-hard for P/T nets (Lipton), with a matching upper
    bound (Rackoff), so terminating is a guarantee about the answer arriving,
    not about it arriving soon.

    This is boundedness for the initial marking the net carries. *Structural*
    boundedness -- bounded for every initial marking -- is a different
    question, answered from the incidence matrix rather than by a search.

    Examples
    --------
    A transition that borrows a token and gives it back is enabled for ever,
    so the place it feeds grows without limit:

    >>> from masafi_sim_petri import Arc, PetriNet, Place, Transition
    >>> from masafi_sim_petri.analysis import is_bounded
    >>> net = PetriNet()
    >>> running = net.add_place(Place('running', initial_marking=1))
    >>> buffer = net.add_place(Place('buffer'))
    >>> produce = net.add_transition(Transition('produce'))
    >>> _ = net.add_arc(Arc(running, produce))
    >>> _ = net.add_arc(Arc(produce, running))
    >>> _ = net.add_arc(Arc(produce, buffer))
    >>> is_bounded(net)
    False

    Consuming what is produced bounds the same net:

    >>> consume = net.add_transition(Transition('consume'))
    >>> _ = net.add_arc(Arc(buffer, consume))
    >>> is_bounded(net)
    False

    That is still unbounded, because ``produce`` need never wait for
    ``consume``. Making the buffer finite, with a place counting its free
    slots, is what bounds it:

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

    See Also
    --------
    is_k_bounded : The question when the bound is known in advance.
    """
    saved_marking = net.marking
    try:
        initial_marking = net.initial_marking
        net.marking = initial_marking
        visited: set[tuple[int, ...]] = {initial_marking}
        path: list[tuple[int, ...]] = [initial_marking]
        pending: list[deque[Transition]] = [deque(net.enabled_transitions())]
        while pending:
            if not pending[-1]:
                pending.pop()
                path.pop()
                continue
            transition = pending[-1].popleft()
            net.marking = path[-1]
            net.fire(transition)
            successor = net.marking
            if any(
                _covers_strictly(successor, ancestor) for ancestor in path
            ):
                return False
            if successor in visited:
                continue
            visited.add(successor)
            path.append(successor)
            pending.append(deque(net.enabled_transitions()))
    finally:
        net.marking = saved_marking
    return True


def _covers_strictly(
    marking: tuple[int, ...], other: tuple[int, ...]
) -> bool:
    """Test whether a marking covers another one and is not equal to it.

    Parameters
    ----------
    marking : tuple of int
        The marking that may cover.
    other : tuple of int
        The marking that may be covered.

    Returns
    -------
    bool
        ``True`` if ``marking`` holds at least as many tokens as ``other`` in
        every place, and more in at least one.
    """
    return marking != other and all(
        tokens >= other_tokens
        for tokens, other_tokens in zip(marking, other, strict=True)
    )
