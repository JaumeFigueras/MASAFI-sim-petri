"""Tests for :mod:`masafi_sim_petri.analysis.boundedness`.

These cover the two boundedness tests: that they answer correctly on bounded
and on unbounded nets, that they terminate in both cases, that they start from
the initial marking, and that they leave the net exactly as they found it.
"""

import pytest

from masafi_sim_petri.analysis import is_k_bounded, is_safe
from masafi_sim_petri.petri_net import Arc, PetriNet, Place, Transition


@pytest.fixture
def cycle_net() -> PetriNet:
    """Return a net in which a single token goes round a cycle.

    The net is ``idle -> start -> busy -> stop -> idle``, with one token in
    ``idle``. It is safe: the token is in exactly one of the two places.

    Returns
    -------
    PetriNet
        A net with two places, two transitions and four arcs.
    """
    net = PetriNet()
    idle = net.add_place(Place('idle', initial_marking=1))
    busy = net.add_place(Place('busy'))
    start = net.add_transition(Transition('start'))
    stop = net.add_transition(Transition('stop'))
    net.add_arc(Arc(idle, start))
    net.add_arc(Arc(start, busy))
    net.add_arc(Arc(busy, stop))
    net.add_arc(Arc(stop, idle))
    return net


@pytest.fixture
def queue_net() -> PetriNet:
    """Return a net whose exact bound is two.

    Two customers wait, one transition serves them one at a time, and the
    served ones pile up: ``waiting`` starts at two and ``served`` ends at two,
    so no place ever holds more than two tokens.

    Returns
    -------
    PetriNet
        A net with two places, one transition and two arcs.
    """
    net = PetriNet()
    waiting = net.add_place(Place('waiting', initial_marking=2))
    served = net.add_place(Place('served'))
    serve = net.add_transition(Transition('serve'))
    net.add_arc(Arc(waiting, serve))
    net.add_arc(Arc(serve, served))
    return net


@pytest.fixture
def unbounded_net() -> PetriNet:
    """Return a net with an unbounded place.

    ``produce`` borrows the token of ``running`` and gives it back, so it is
    enabled for ever, and every firing adds one token to ``buffer``. The
    reachable set is infinite.

    Returns
    -------
    PetriNet
        A net with two places, one transition and three arcs.
    """
    net = PetriNet()
    running = net.add_place(Place('running', initial_marking=1))
    buffer = net.add_place(Place('buffer'))
    produce = net.add_transition(Transition('produce'))
    net.add_arc(Arc(running, produce))
    net.add_arc(Arc(produce, running))
    net.add_arc(Arc(produce, buffer))
    return net


class TestSafeNets:
    """Nets in which no place ever holds a second token."""

    def test_a_cycle_of_one_token_is_safe(self, cycle_net: PetriNet) -> None:
        """A token moving between two places never doubles up."""
        assert is_safe(cycle_net) is True

    def test_a_net_without_transitions_is_safe(self) -> None:
        """With nothing to fire, the initial marking is the whole state space."""
        net = PetriNet()
        net.add_place(Place('p1', initial_marking=1))
        assert is_safe(net) is True

    def test_an_empty_net_is_safe(self) -> None:
        """A net with no places has no place that could hold two tokens."""
        assert is_safe(PetriNet()) is True


class TestUnsafeNets:
    """Nets in which some reachable marking holds two tokens in a place."""

    def test_an_arc_weight_can_break_safeness(self) -> None:
        """A weighted output arc delivers more than one token at a time."""
        net = PetriNet()
        source = net.add_place(Place('source', initial_marking=1))
        target = net.add_place(Place('target'))
        move = net.add_transition(Transition('move'))
        net.add_arc(Arc(source, move))
        net.add_arc(Arc(move, target, weight=2))
        assert is_safe(net) is False

    def test_two_tokens_can_meet_in_a_place(self) -> None:
        """Two independent tokens joining in one place break safeness."""
        net = PetriNet()
        left = net.add_place(Place('left', initial_marking=1))
        right = net.add_place(Place('right', initial_marking=1))
        merged = net.add_place(Place('merged'))
        from_left = net.add_transition(Transition('from_left'))
        from_right = net.add_transition(Transition('from_right'))
        net.add_arc(Arc(left, from_left))
        net.add_arc(Arc(from_left, merged))
        net.add_arc(Arc(right, from_right))
        net.add_arc(Arc(from_right, merged))
        assert is_safe(net) is False

    def test_an_initial_marking_can_already_be_unsafe(self) -> None:
        """A place starting with two tokens is enough, with nothing to fire."""
        net = PetriNet()
        net.add_place(Place('p1', initial_marking=2))
        assert is_safe(net) is False

    def test_an_unbounded_net_is_not_safe(
        self, unbounded_net: PetriNet
    ) -> None:
        """The search stops at the first marking that exceeds the bound."""
        assert is_safe(unbounded_net) is False


class TestTheBound:
    """``k`` as a parameter, on a net whose exact bound is two."""

    @pytest.mark.parametrize('k', [2, 3, 10])
    def test_the_exact_bound_and_above_hold(
        self, queue_net: PetriNet, k: int
    ) -> None:
        """A net bounded by two is bounded by anything at least two."""
        assert is_k_bounded(queue_net, k) is True

    @pytest.mark.parametrize('k', [0, 1])
    def test_below_the_exact_bound_fails(
        self, queue_net: PetriNet, k: int
    ) -> None:
        """A net bounded by two is not bounded by anything less."""
        assert is_k_bounded(queue_net, k) is False

    def test_zero_bounds_a_net_that_holds_no_tokens(self) -> None:
        """A net that can never hold a token is 0-bounded."""
        net = PetriNet()
        net.add_place(Place('p1'))
        net.add_transition(Transition('t1'))
        assert is_k_bounded(net, 0) is True

    def test_a_negative_bound_is_rejected(self, cycle_net: PetriNet) -> None:
        """There is no marking below zero, so the question is malformed."""
        with pytest.raises(ValueError):
            is_k_bounded(cycle_net, -1)

    def test_an_unbounded_net_terminates_for_any_bound(
        self, unbounded_net: PetriNet
    ) -> None:
        """Exceeding the bound ends the search, however high the bound is."""
        assert is_k_bounded(unbounded_net, 5) is False


class TestTheNetIsLeftAlone:
    """The analysis fires transitions, but must not be observable."""

    def test_the_marking_survives_a_true_answer(
        self, cycle_net: PetriNet
    ) -> None:
        """A search that runs to exhaustion restores the marking."""
        cycle_net.fire(cycle_net.transition('start'))
        marking = cycle_net.marking
        assert is_safe(cycle_net) is True
        assert cycle_net.marking == marking

    def test_the_marking_survives_an_early_exit(
        self, unbounded_net: PetriNet
    ) -> None:
        """A search that returns as soon as the bound is exceeded restores it too."""
        marking = unbounded_net.marking
        assert is_safe(unbounded_net) is False
        assert unbounded_net.marking == marking

    def test_the_marking_survives_a_rejected_bound(
        self, cycle_net: PetriNet
    ) -> None:
        """A bound that is rejected leaves the net untouched."""
        marking = cycle_net.marking
        with pytest.raises(ValueError):
            is_k_bounded(cycle_net, -1)
        assert cycle_net.marking == marking

    def test_the_search_starts_from_the_initial_marking(
        self, queue_net: PetriNet
    ) -> None:
        """The current marking is a starting point for nothing but restoring."""
        queue_net.marking = (0, 0)
        assert is_k_bounded(queue_net, 1) is False
        assert queue_net.marking == (0, 0)
