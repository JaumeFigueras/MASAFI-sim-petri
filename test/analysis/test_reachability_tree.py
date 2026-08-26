"""Tests for :mod:`masafi_sim_petri.analysis.reachability_tree`.

These cover how the tree is built -- the order the branches are laid out in,
the label each leaf gets and why it stopped there -- what the level limit does,
how an unbounded net is handled, and the queries and drawing the result offers.
"""

import pytest

from masafi_sim_petri.analysis import (
    NodeLabel,
    ReachabilityTree,
    UnboundedNetError,
)
from masafi_sim_petri.petri_net import Arc, PetriNet, Place, Transition


@pytest.fixture
def choice_net() -> PetriNet:
    """Return a net with a choice, a cycle and a dead end.

    ``t1`` moves the token to ``p2`` and ``t3`` brings it back, so that branch
    closes on a marking already seen. ``t2`` moves it to ``p3``, where nothing
    is enabled.

    Returns
    -------
    PetriNet
        A net with three places, three transitions and six arcs.
    """
    net = PetriNet()
    p1 = net.add_place(Place('p1', initial_marking=1))
    p2 = net.add_place(Place('p2'))
    p3 = net.add_place(Place('p3'))
    t1 = net.add_transition(Transition('t1'))
    t2 = net.add_transition(Transition('t2'))
    t3 = net.add_transition(Transition('t3'))
    net.add_arc(Arc(p1, t1))
    net.add_arc(Arc(t1, p2))
    net.add_arc(Arc(p1, t2))
    net.add_arc(Arc(t2, p3))
    net.add_arc(Arc(p2, t3))
    net.add_arc(Arc(t3, p1))
    return net


@pytest.fixture
def unbounded_net() -> PetriNet:
    """Return a net whose ``buffer`` place grows without limit.

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


class TestTheRoot:
    """The node the tree starts from."""

    def test_the_root_holds_the_initial_marking(
        self, choice_net: PetriNet
    ) -> None:
        """The tree is of :math:`M_0`, not of wherever the net stands."""
        choice_net.fire(choice_net.transition('t1'))
        tree = ReachabilityTree(choice_net)
        assert tree.root.marking == (1, 0, 0)

    def test_the_root_is_level_one(self, choice_net: PetriNet) -> None:
        """Levels are counted the way a drawn tree is."""
        assert ReachabilityTree(choice_net).root.level == 1

    def test_the_root_has_no_parent_and_no_transition(
        self, choice_net: PetriNet
    ) -> None:
        """Nothing was fired to reach the initial marking."""
        root = ReachabilityTree(choice_net).root
        assert root.parent is None
        assert root.incoming_transition is None
        assert root.is_root is True
        assert root.firing_sequence() == ()

    def test_a_net_that_cannot_fire_is_a_single_dead_root(self) -> None:
        """One node, labelled for the reason it was not expanded."""
        net = PetriNet()
        net.add_place(Place('p1', initial_marking=1))
        tree = ReachabilityTree(net)
        assert len(tree) == 1
        assert tree.root.label is NodeLabel.DEADLOCK
        assert tree.levels == 1


class TestBranchOrder:
    """Children are laid out by transition name, in natural order."""

    def test_the_branches_follow_the_names_not_the_net(self) -> None:
        """The transitions are added in reverse, the branches come out sorted."""
        net = PetriNet()
        p1 = net.add_place(Place('p1', initial_marking=1))
        for name in ('t3', 't1', 't2'):
            transition = net.add_transition(Transition(name))
            net.add_arc(Arc(p1, transition))
        tree = ReachabilityTree(net)
        fired = [
            child.incoming_transition.name for child in tree.root.children
        ]
        assert fired == ['t1', 't2', 't3']

    def test_ten_comes_after_two(self) -> None:
        """Natural order, so a digit run is compared as a number."""
        net = PetriNet()
        p1 = net.add_place(Place('p1', initial_marking=1))
        for number in (11, 2, 10, 1, 3):
            transition = net.add_transition(Transition(f't{number}'))
            net.add_arc(Arc(p1, transition))
        tree = ReachabilityTree(net)
        fired = [
            child.incoming_transition.name for child in tree.root.children
        ]
        assert fired == ['t1', 't2', 't3', 't10', 't11']

    def test_names_without_digits_are_ordered_as_text(self) -> None:
        """A name that is all letters is compared as it reads."""
        net = PetriNet()
        p1 = net.add_place(Place('p1', initial_marking=1))
        for name in ('serve', 'arrive', 'leave'):
            transition = net.add_transition(Transition(name))
            net.add_arc(Arc(p1, transition))
        tree = ReachabilityTree(net)
        fired = [
            child.incoming_transition.name for child in tree.root.children
        ]
        assert fired == ['arrive', 'leave', 'serve']


class TestLabels:
    """Why each leaf stopped where it did."""

    def test_a_repeated_marking_is_old(self, choice_net: PetriNet) -> None:
        """Coming back to a marking already in the tree ends the branch."""
        tree = ReachabilityTree(choice_net)
        old = tree.nodes_labelled(NodeLabel.OLD)
        assert [node.marking for node in old] == [(1, 0, 0)]
        assert old[0].parent.marking == (0, 1, 0)

    def test_a_marking_without_enabled_transitions_is_a_deadlock(
        self, choice_net: PetriNet
    ) -> None:
        """Nothing is enabled in ``p3``, so the branch dies there."""
        tree = ReachabilityTree(choice_net)
        assert [node.marking for node in tree.deadlocks()] == [(0, 0, 1)]

    def test_a_deadlock_node_reports_how_it_was_reached(
        self, choice_net: PetriNet
    ) -> None:
        """The firing sequence of the node is the one that kills the net."""
        tree = ReachabilityTree(choice_net)
        (deadlock,) = tree.deadlocks()
        assert [t.name for t in deadlock.firing_sequence()] == ['t2']

    def test_an_expanded_node_is_internal(self, choice_net: PetriNet) -> None:
        """Only an internal node has children."""
        tree = ReachabilityTree(choice_net)
        internal = tree.nodes_labelled(NodeLabel.INTERNAL)
        assert [node.marking for node in internal] == [(1, 0, 0), (0, 1, 0)]
        assert all(not node.is_leaf for node in internal)

    def test_old_wins_over_deadlock(self) -> None:
        """A dead marking reached twice is a deadlock once and old after.

        Both ``t1`` and ``t2`` empty the only place, so the same dead marking
        is reached on two branches.
        """
        net = PetriNet()
        p1 = net.add_place(Place('p1', initial_marking=1))
        t1 = net.add_transition(Transition('t1'))
        t2 = net.add_transition(Transition('t2'))
        net.add_arc(Arc(p1, t1))
        net.add_arc(Arc(p1, t2))
        tree = ReachabilityTree(net)
        first, second = tree.root.children
        assert first.label is NodeLabel.DEADLOCK
        assert second.label is NodeLabel.OLD
        assert len(tree.deadlocks()) == 1

    def test_old_is_decided_against_the_whole_tree(self) -> None:
        """A marking seen on another branch is old, not just one on the path.

        ``t1`` and ``t2`` both reach ``(0, 1, 0)`` -- the second by way of
        ``p3`` -- and the two occurrences are on different branches.
        """
        net = PetriNet()
        p1 = net.add_place(Place('p1', initial_marking=1))
        p2 = net.add_place(Place('p2'))
        p3 = net.add_place(Place('p3'))
        t1 = net.add_transition(Transition('t1'))
        t2 = net.add_transition(Transition('t2'))
        t3 = net.add_transition(Transition('t3'))
        net.add_arc(Arc(p1, t1))
        net.add_arc(Arc(t1, p2))
        net.add_arc(Arc(p1, t2))
        net.add_arc(Arc(t2, p3))
        net.add_arc(Arc(p3, t3))
        net.add_arc(Arc(t3, p2))
        tree = ReachabilityTree(net)
        (old,) = tree.nodes_labelled(NodeLabel.OLD)
        assert old.marking == (0, 1, 0)
        assert [t.name for t in old.firing_sequence()] == ['t2', 't3']


class TestTheLevelLimit:
    """Stopping before the tree is finished, and saying so."""

    def test_a_limit_truncates_and_reports_it(
        self, choice_net: PetriNet
    ) -> None:
        """The nodes at the last level are left unexpanded."""
        tree = ReachabilityTree(
            choice_net, refuse_unbounded=False, max_levels=2
        )
        assert tree.is_complete is False
        assert [node.marking for node in tree.truncated_nodes()] == [(0, 1, 0)]
        assert tree.levels == 2

    def test_a_limit_that_is_never_reached_leaves_the_tree_complete(
        self, choice_net: PetriNet
    ) -> None:
        """A tree of three levels is unaffected by a limit of ten."""
        tree = ReachabilityTree(choice_net, max_levels=10)
        assert tree.is_complete is True
        assert tree.truncated_nodes() == ()
        assert tree.levels == 3

    def test_a_limit_of_one_leaves_only_the_root(
        self, choice_net: PetriNet
    ) -> None:
        """The root itself can be the node that is not expanded."""
        tree = ReachabilityTree(
            choice_net, refuse_unbounded=False, max_levels=1
        )
        assert len(tree) == 1
        assert tree.root.label is NodeLabel.TRUNCATED
        assert tree.is_complete is False

    def test_a_deadlock_at_the_limit_is_still_a_deadlock(self) -> None:
        """A node with nothing enabled did not stop because of the limit."""
        net = PetriNet()
        p1 = net.add_place(Place('p1', initial_marking=1))
        p2 = net.add_place(Place('p2'))
        t1 = net.add_transition(Transition('t1'))
        net.add_arc(Arc(p1, t1))
        net.add_arc(Arc(t1, p2))
        tree = ReachabilityTree(net, refuse_unbounded=False, max_levels=2)
        assert tree.leaves()[0].label is NodeLabel.DEADLOCK
        assert tree.is_complete is True

    def test_an_unbounded_net_can_be_truncated_instead_of_refused(
        self, unbounded_net: PetriNet
    ) -> None:
        """The limit is what makes an infinite tree answerable."""
        tree = ReachabilityTree(
            unbounded_net, refuse_unbounded=False, max_levels=4
        )
        assert tree.is_complete is False
        assert tree.levels == 4
        assert [node.marking for node in tree.nodes()] == [
            (1, 0),
            (1, 1),
            (1, 2),
            (1, 3),
        ]

    def test_a_limit_below_one_is_rejected(
        self, choice_net: PetriNet
    ) -> None:
        """A tree has a root, so it has at least one level."""
        with pytest.raises(ValueError):
            ReachabilityTree(choice_net, max_levels=0)


class TestUnboundedNets:
    """A net whose tree is infinite."""

    def test_it_is_refused_by_default(
        self, unbounded_net: PetriNet
    ) -> None:
        """Building for ever is not one of the outcomes."""
        with pytest.raises(UnboundedNetError):
            ReachabilityTree(unbounded_net)

    def test_the_refusal_names_the_covering_marking(
        self, unbounded_net: PetriNet
    ) -> None:
        """The message says which marking pumps."""
        with pytest.raises(UnboundedNetError, match=r'\(1, 1\)'):
            ReachabilityTree(unbounded_net)

    def test_a_bounded_net_is_never_refused(
        self, choice_net: PetriNet
    ) -> None:
        """The covering rule finds nothing to pump in a bounded net."""
        assert ReachabilityTree(choice_net).is_complete is True

    def test_dropping_the_refusal_without_a_limit_is_rejected(
        self, unbounded_net: PetriNet
    ) -> None:
        """Neither a refusal nor a limit would mean building for ever."""
        with pytest.raises(ValueError):
            ReachabilityTree(unbounded_net, refuse_unbounded=False)


class TestQueries:
    """What the finished tree can be asked."""

    def test_the_nodes_come_level_by_level(
        self, choice_net: PetriNet
    ) -> None:
        """Breadth first, so the levels are contiguous and in order."""
        tree = ReachabilityTree(choice_net)
        assert [node.level for node in tree.nodes()] == [1, 2, 2, 3]

    def test_the_leaves_are_the_unexpanded_nodes(
        self, choice_net: PetriNet
    ) -> None:
        """Three nodes stop the tree, two of them at level two."""
        tree = ReachabilityTree(choice_net)
        assert [node.marking for node in tree.leaves()] == [
            (0, 0, 1),
            (1, 0, 0),
        ]

    def test_the_markings_are_the_distinct_ones(
        self, choice_net: PetriNet
    ) -> None:
        """Four nodes, three markings: the root is also the old leaf."""
        tree = ReachabilityTree(choice_net)
        assert len(tree) == 4
        assert tree.markings() == ((1, 0, 0), (0, 1, 0), (0, 0, 1))

    def test_a_path_runs_from_the_root_down(
        self, choice_net: PetriNet
    ) -> None:
        """The path and the firing sequence agree."""
        tree = ReachabilityTree(choice_net)
        (old,) = tree.nodes_labelled(NodeLabel.OLD)
        assert [node.marking for node in old.path_from_root()] == [
            (1, 0, 0),
            (0, 1, 0),
            (1, 0, 0),
        ]
        assert [t.name for t in old.firing_sequence()] == ['t1', 't3']


class TestDrawing:
    """The tree as text, which is how it is checked by eye."""

    def test_the_drawing_shows_branches_labels_and_transitions(
        self, choice_net: PetriNet
    ) -> None:
        """Every line but the root carries the transition that made it."""
        tree = ReachabilityTree(choice_net)
        assert str(tree) == (
            '(1, 0, 0)\n'
            '├── t1 -> (0, 1, 0)\n'
            '│   └── t3 -> (1, 0, 0) [old]\n'
            '└── t2 -> (0, 0, 1) [deadlock]'
        )

    def test_a_node_prints_its_marking_and_label(
        self, choice_net: PetriNet
    ) -> None:
        """An internal node has no label worth printing."""
        tree = ReachabilityTree(choice_net)
        assert str(tree.root) == '(1, 0, 0)'
        assert str(tree.deadlocks()[0]) == '(0, 0, 1) [deadlock]'

    def test_the_representations_are_unambiguous(
        self, choice_net: PetriNet
    ) -> None:
        """The tree and its nodes say what they are."""
        tree = ReachabilityTree(choice_net)
        assert repr(tree) == (
            'ReachabilityTree(nodes=4, levels=3, is_complete=True)'
        )
        assert repr(tree.root) == (
            'MarkingTreeNode(marking=(1, 0, 0), level=1, label=internal)'
        )


class TestTheNetIsLeftAlone:
    """Building a tree fires the net, but must not be observable."""

    def test_the_marking_survives_a_finished_tree(
        self, choice_net: PetriNet
    ) -> None:
        """The marking the net stood in is restored."""
        choice_net.fire(choice_net.transition('t1'))
        marking = choice_net.marking
        ReachabilityTree(choice_net)
        assert choice_net.marking == marking

    def test_the_marking_survives_a_refusal(
        self, unbounded_net: PetriNet
    ) -> None:
        """Raising is not an excuse to leave the net mid-firing."""
        marking = unbounded_net.marking
        with pytest.raises(UnboundedNetError):
            ReachabilityTree(unbounded_net)
        assert unbounded_net.marking == marking
