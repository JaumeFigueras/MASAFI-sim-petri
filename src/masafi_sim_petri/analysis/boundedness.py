"""Boundedness of a Petri net."""

from __future__ import annotations

from collections import deque

from masafi_sim_petri.petri_net.petri_net import PetriNet


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
