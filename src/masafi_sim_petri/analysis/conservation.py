"""Conservation of tokens in a Petri net."""

from __future__ import annotations

from masafi_sim_petri.petri_net.petri_net import PetriNet


def is_strictly_conservative(net: PetriNet) -> bool:
    """Test whether every transition produces as many tokens as it consumes.

    Each transition is weighed on its own: the weights of the arcs into it are
    summed, the weights of the arcs out of it are summed, and the two must
    agree. A transition that balances neither creates nor destroys tokens, so
    a net whose transitions all balance keeps the total number of tokens fixed
    at whatever its initial marking held, however long it runs.

    Parameters
    ----------
    net : PetriNet
        Net to analyse. It is not fired and not modified.

    Returns
    -------
    bool
        ``True`` if every transition of the net balances. A net with no
        transitions balances vacuously.

    Notes
    -----
    This is a *structural* property: it is read off the arcs, in time linear
    in their number, and no marking is involved. Nothing has to be explored,
    which is what separates it from a behavioural property such as
    :func:`~masafi_sim_petri.analysis.boundedness.is_safe`.

    Being structural also makes the answer stronger than it looks. Token count
    is conserved for *every* initial marking, not just the one the net
    carries, and that gives boundedness for free: a strictly conservative net
    can never hold more tokens than it started with, so it is
    :math:`k`-bounded for :math:`k = \\sum M_0` without any search.

    The test is per transition, which is the classical definition, and it is
    slightly stronger than asking for the token count to be constant across
    the reachable markings. A transition that can never fire cannot disturb
    any count, yet an unbalanced one still makes this test answer ``False``.
    The structural answer is the useful one: it is the answer that holds for
    every initial marking, and it is the one the boundedness argument above
    needs.

    Strict conservation is the special case, with every place weighing one, of
    conservation with respect to a vector of place weights. A net that fails
    this test may still conserve a weighted count -- one token in a buffer
    standing for two on a pallet -- which is a place invariant and a separate
    question.

    Examples
    --------
    A token moving round a cycle is conserved: every transition takes one and
    gives one back.

    >>> from masafi_sim_petri import Arc, PetriNet, Place, Transition
    >>> from masafi_sim_petri.analysis import is_strictly_conservative
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

    A transition that forks one token into two does not conserve them:

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
    """
    for transition in net.transitions:
        consumed = sum(arc.weight for arc in net.input_arcs(transition))
        produced = sum(arc.weight for arc in net.output_arcs(transition))
        if consumed != produced:
            return False
    return True
