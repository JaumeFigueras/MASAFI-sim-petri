"""Tests for :mod:`masafi_sim_petri.analysis.conservation`.

These cover the per-transition weighing that decides strict conservation: the
shapes that balance, the shapes that do not, the degenerate nets, and the fact
that the answer is read off the structure rather than off any marking.
"""

import pytest

from masafi_sim_petri.analysis import is_k_bounded, is_strictly_conservative
from masafi_sim_petri.petri_net import Arc, PetriNet, Place, Transition


@pytest.fixture
def cycle_net() -> PetriNet:
    """Return a net in which a single token goes round a cycle.

    The net is ``idle -> start -> busy -> stop -> idle``, with one token in
    ``idle``. Every transition takes one token and gives one back.

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


class TestConservativeNets:
    """Nets whose transitions all balance."""

    def test_a_cycle_conserves_its_token(self, cycle_net: PetriNet) -> None:
        """One in, one out, at every transition."""
        assert is_strictly_conservative(cycle_net) is True

    def test_a_self_loop_conserves(self) -> None:
        """A transition that borrows a token and returns it balances."""
        net = PetriNet()
        server = net.add_place(Place('server', initial_marking=1))
        serve = net.add_transition(Transition('serve'))
        net.add_arc(Arc(server, serve))
        net.add_arc(Arc(serve, server))
        assert is_strictly_conservative(net) is True

    def test_weights_may_differ_as_long_as_the_sums_agree(self) -> None:
        """Two tokens in from one place, one each out to two places."""
        net = PetriNet()
        pallet = net.add_place(Place('pallet', initial_marking=2))
        left = net.add_place(Place('left'))
        right = net.add_place(Place('right'))
        unpack = net.add_transition(Transition('unpack'))
        net.add_arc(Arc(pallet, unpack, weight=2))
        net.add_arc(Arc(unpack, left))
        net.add_arc(Arc(unpack, right))
        assert is_strictly_conservative(net) is True

    def test_a_join_of_two_tokens_into_two_conserves(self) -> None:
        """Several arcs on both sides, weighed as sums."""
        net = PetriNet()
        left = net.add_place(Place('left', initial_marking=1))
        right = net.add_place(Place('right', initial_marking=1))
        out_a = net.add_place(Place('out_a'))
        out_b = net.add_place(Place('out_b'))
        join = net.add_transition(Transition('join'))
        net.add_arc(Arc(left, join))
        net.add_arc(Arc(right, join))
        net.add_arc(Arc(join, out_a))
        net.add_arc(Arc(join, out_b))
        assert is_strictly_conservative(net) is True

    def test_a_net_without_transitions_conserves_vacuously(self) -> None:
        """With nothing that could move a token, nothing can lose one."""
        net = PetriNet()
        net.add_place(Place('p1', initial_marking=3))
        assert is_strictly_conservative(net) is True

    def test_an_empty_net_conserves(self) -> None:
        """A net with no transitions at all, not even places."""
        assert is_strictly_conservative(PetriNet()) is True

    def test_a_transition_without_arcs_conserves(self) -> None:
        """Nothing in and nothing out is still a balance."""
        net = PetriNet()
        net.add_transition(Transition('t1'))
        assert is_strictly_conservative(net) is True


class TestNonConservativeNets:
    """Nets with a transition that creates or destroys tokens."""

    def test_a_fork_creates_a_token(self) -> None:
        """One token in, two out."""
        net = PetriNet()
        ready = net.add_place(Place('ready', initial_marking=1))
        left = net.add_place(Place('left'))
        right = net.add_place(Place('right'))
        fork = net.add_transition(Transition('fork'))
        net.add_arc(Arc(ready, fork))
        net.add_arc(Arc(fork, left))
        net.add_arc(Arc(fork, right))
        assert is_strictly_conservative(net) is False

    def test_an_output_weight_creates_tokens(self) -> None:
        """The weight is what counts, not the number of arcs."""
        net = PetriNet()
        source = net.add_place(Place('source', initial_marking=1))
        target = net.add_place(Place('target'))
        move = net.add_transition(Transition('move'))
        net.add_arc(Arc(source, move))
        net.add_arc(Arc(move, target, weight=2))
        assert is_strictly_conservative(net) is False

    def test_a_source_transition_creates_tokens(self) -> None:
        """No input arcs at all: nothing is consumed, something is produced."""
        net = PetriNet()
        buffer = net.add_place(Place('buffer'))
        produce = net.add_transition(Transition('produce'))
        net.add_arc(Arc(produce, buffer))
        assert is_strictly_conservative(net) is False

    def test_a_sink_transition_destroys_tokens(self) -> None:
        """No output arcs at all: something is consumed, nothing is produced."""
        net = PetriNet()
        buffer = net.add_place(Place('buffer', initial_marking=1))
        consume = net.add_transition(Transition('consume'))
        net.add_arc(Arc(buffer, consume))
        assert is_strictly_conservative(net) is False

    def test_one_unbalanced_transition_is_enough(
        self, cycle_net: PetriNet
    ) -> None:
        """The rest of the net balancing does not rescue it."""
        drain = cycle_net.add_transition(Transition('drain'))
        cycle_net.add_arc(Arc(cycle_net.place('busy'), drain))
        assert is_strictly_conservative(cycle_net) is False

    def test_an_unbalanced_transition_that_can_never_fire_still_counts(
        self,
    ) -> None:
        """The test is structural: a dead transition is weighed like any other.

        ``leak`` needs two tokens from a place that can only ever hold one, so
        no reachable marking enables it and the token count is in fact
        constant. The structural answer is still ``False``, because the
        balance is what is being asked about.
        """
        net = PetriNet()
        p1 = net.add_place(Place('p1', initial_marking=1))
        p2 = net.add_place(Place('p2'))
        move = net.add_transition(Transition('move'))
        leak = net.add_transition(Transition('leak'))
        net.add_arc(Arc(p1, move))
        net.add_arc(Arc(move, p2))
        net.add_arc(Arc(p1, leak, weight=2))
        assert net.is_enabled(leak) is False
        assert is_strictly_conservative(net) is False


class TestTheNetIsLeftAlone:
    """The analysis reads the structure and nothing else."""

    def test_the_marking_is_untouched(self, cycle_net: PetriNet) -> None:
        """No transition is fired, so the current marking cannot move."""
        cycle_net.fire(cycle_net.transition('start'))
        marking = cycle_net.marking
        assert is_strictly_conservative(cycle_net) is True
        assert cycle_net.marking == marking

    def test_the_answer_does_not_depend_on_the_marking(self) -> None:
        """The same structure answers the same with no tokens in it at all."""
        empty = PetriNet()
        idle = empty.add_place(Place('idle'))
        busy = empty.add_place(Place('busy'))
        start = empty.add_transition(Transition('start'))
        empty.add_arc(Arc(idle, start))
        empty.add_arc(Arc(start, busy))
        assert is_strictly_conservative(empty) is True


class TestTheBoundednessCorollary:
    """A strictly conservative net cannot hold more tokens than it started with."""

    def test_conservation_bounds_the_net(self, cycle_net: PetriNet) -> None:
        """The total is fixed, so the sum of the initial marking is a bound."""
        assert is_strictly_conservative(cycle_net) is True
        assert is_k_bounded(cycle_net, sum(cycle_net.initial_marking)) is True

    def test_the_corollary_holds_with_several_tokens(self) -> None:
        """Three tokens circulating are bounded by three, and not by two."""
        net = PetriNet()
        idle = net.add_place(Place('idle', initial_marking=3))
        busy = net.add_place(Place('busy'))
        start = net.add_transition(Transition('start'))
        stop = net.add_transition(Transition('stop'))
        net.add_arc(Arc(idle, start))
        net.add_arc(Arc(start, busy))
        net.add_arc(Arc(busy, stop))
        net.add_arc(Arc(stop, idle))
        assert is_strictly_conservative(net) is True
        assert is_k_bounded(net, 3) is True
        assert is_k_bounded(net, 2) is False
