"""Tests for :mod:`masafi_sim_petri.analysis.marking_tree`.

The classes here are the finished tree, not the construction of one, so the
trees in these tests are built by hand: a node knows its marking, its place in
the tree and why it stopped there, and the tree answers questions over the
nodes it was given. What fills a tree with the right nodes is tested with each
construction that does it.
"""

import pytest

from masafi_sim_petri.analysis.marking_tree import (
    MarkingTree,
    MarkingTreeNode,
    NodeLabel,
    _natural_key,
)
from masafi_sim_petri.petri_net import Transition


@pytest.fixture
def transitions() -> tuple[Transition, Transition]:
    """Return two transitions to label the edges of a hand-built tree.

    Returns
    -------
    tuple of Transition
        Transitions named ``t1`` and ``t2``.
    """
    return Transition('t1'), Transition('t2')


@pytest.fixture
def tree(transitions: tuple[Transition, Transition]) -> MarkingTree:
    """Return a small tree built by hand.

    The shape is the one a net with a choice gives: a root with two children,
    the left one expanded once more into an old marking and the right one
    dead::

        (1, 0, 0)
        |-- t1 -> (0, 1, 0)
        |   `-- t2 -> (1, 0, 0) [old]
        `-- t2 -> (0, 0, 1) [deadlock]

    Returns
    -------
    MarkingTree
        A complete tree of four nodes over three levels.
    """
    t1, t2 = transitions
    root = MarkingTreeNode((1, 0, 0), 1)
    left = MarkingTreeNode((0, 1, 0), 2, root, t1)
    right = MarkingTreeNode((0, 0, 1), 2, root, t2)
    old = MarkingTreeNode((1, 0, 0), 3, left, t2)
    old._set_label(NodeLabel.OLD)
    right._set_label(NodeLabel.DEADLOCK)
    root._add_child(left)
    root._add_child(right)
    left._add_child(old)
    return MarkingTree([root, left, right, old], True)


class TestANode:
    """What a node knows about itself."""

    def test_a_node_holds_its_marking_and_level(
        self, tree: MarkingTree
    ) -> None:
        """The two things that place it in the tree."""
        assert tree.root.marking == (1, 0, 0)
        assert tree.root.level == 1

    def test_a_new_node_is_internal(self) -> None:
        """A node is expanded until the construction says otherwise."""
        assert MarkingTreeNode((0,), 1).label is NodeLabel.INTERNAL

    def test_the_root_is_a_root_and_nothing_else_is(
        self, tree: MarkingTree
    ) -> None:
        """Being the root is having no parent."""
        assert tree.root.is_root is True
        assert all(
            node.is_root is False for node in tree.nodes() if node is not tree.root
        )

    def test_a_node_without_children_is_a_leaf(
        self, tree: MarkingTree
    ) -> None:
        """Leaves are the nodes the construction did not expand."""
        assert tree.root.is_leaf is False
        assert [node.marking for node in tree.leaves()] == [
            (0, 0, 1),
            (1, 0, 0),
        ]

    def test_children_come_back_in_the_order_they_were_added(
        self, tree: MarkingTree, transitions: tuple[Transition, Transition]
    ) -> None:
        """The construction sorts them; the node keeps that order."""
        t1, t2 = transitions
        assert [
            child.incoming_transition for child in tree.root.children
        ] == [t1, t2]

    def test_a_path_runs_from_the_root_down(self, tree: MarkingTree) -> None:
        """Inclusive at both ends, root first."""
        deepest = tree.nodes()[-1]
        assert [node.marking for node in deepest.path_from_root()] == [
            (1, 0, 0),
            (0, 1, 0),
            (1, 0, 0),
        ]

    def test_a_firing_sequence_skips_the_root(self, tree: MarkingTree) -> None:
        """Nothing was fired to reach the initial marking."""
        deepest = tree.nodes()[-1]
        assert [t.name for t in deepest.firing_sequence()] == ['t1', 't2']
        assert tree.root.firing_sequence() == ()


class TestNodeText:
    """A node reads as its marking, and says when it stopped a branch."""

    def test_an_internal_node_shows_only_its_marking(
        self, tree: MarkingTree
    ) -> None:
        """There is nothing to explain about an expanded node."""
        assert str(tree.root) == '(1, 0, 0)'

    @pytest.mark.parametrize(
        ('label', 'expected'),
        [
            (NodeLabel.OLD, '(0,) [old]'),
            (NodeLabel.DEADLOCK, '(0,) [deadlock]'),
            (NodeLabel.TRUNCATED, '(0,) [truncated]'),
        ],
    )
    def test_a_stopped_node_shows_why(
        self, label: NodeLabel, expected: str
    ) -> None:
        """Each label prints as its own name."""
        node = MarkingTreeNode((0,), 1)
        node._set_label(label)
        assert str(node) == expected

    def test_the_representation_is_unambiguous(
        self, tree: MarkingTree
    ) -> None:
        """Marking, level and label, which is all a node is."""
        assert repr(tree.root) == (
            'MarkingTreeNode(marking=(1, 0, 0), level=1, label=internal)'
        )


class TestTheTree:
    """What a finished tree can be asked."""

    def test_the_first_node_is_the_root(self, tree: MarkingTree) -> None:
        """Construction is breadth first, so the root comes first."""
        assert tree.root is tree.nodes()[0]

    def test_a_tree_needs_a_root(self) -> None:
        """A tree of no nodes is not a tree."""
        with pytest.raises(ValueError):
            MarkingTree([], True)

    def test_the_levels_are_counted_from_one(self, tree: MarkingTree) -> None:
        """Three levels, the root being the first."""
        assert tree.levels == 3

    def test_the_length_counts_occurrences(self, tree: MarkingTree) -> None:
        """Four nodes, although two of them hold the same marking."""
        assert len(tree) == 4

    def test_the_markings_are_the_distinct_ones(
        self, tree: MarkingTree
    ) -> None:
        """In order of first sight, each one once."""
        assert tree.markings() == ((1, 0, 0), (0, 1, 0), (0, 0, 1))

    def test_nodes_can_be_selected_by_label(self, tree: MarkingTree) -> None:
        """The generic selector behind the named ones."""
        assert [
            node.marking for node in tree.nodes_labelled(NodeLabel.OLD)
        ] == [(1, 0, 0)]

    def test_the_deadlocks_are_the_dead_nodes(
        self, tree: MarkingTree
    ) -> None:
        """A named selector, for the label that is asked about most."""
        assert [node.marking for node in tree.deadlocks()] == [(0, 0, 1)]

    def test_a_complete_tree_has_no_truncated_nodes(
        self, tree: MarkingTree
    ) -> None:
        """The two agree, since one is the reason for the other."""
        assert tree.is_complete is True
        assert tree.truncated_nodes() == ()

    def test_an_incomplete_tree_says_so(
        self, transitions: tuple[Transition, Transition]
    ) -> None:
        """A tree stopped by a level limit reports where it stopped."""
        t1, _ = transitions
        root = MarkingTreeNode((1,), 1)
        child = MarkingTreeNode((2,), 2, root, t1)
        child._set_label(NodeLabel.TRUNCATED)
        root._add_child(child)
        stopped = MarkingTree([root, child], False)
        assert stopped.is_complete is False
        assert [node.marking for node in stopped.truncated_nodes()] == [(2,)]


class TestDrawing:
    """The tree as indented text."""

    def test_the_drawing_shows_the_shape_and_the_labels(
        self, tree: MarkingTree
    ) -> None:
        """One line per node, the branches drawn down the left."""
        assert str(tree) == (
            '(1, 0, 0)\n'
            '├── t1 -> (0, 1, 0)\n'
            '│   └── t2 -> (1, 0, 0) [old]\n'
            '└── t2 -> (0, 0, 1) [deadlock]'
        )

    def test_a_single_node_draws_as_one_line(self) -> None:
        """A root that was never expanded is the whole drawing."""
        root = MarkingTreeNode((0, 1), 1)
        root._set_label(NodeLabel.DEADLOCK)
        assert str(MarkingTree([root], True)) == '(0, 1) [deadlock]'

    def test_the_representation_is_unambiguous(
        self, tree: MarkingTree
    ) -> None:
        """Size, depth and whether it is the whole tree."""
        assert repr(tree) == (
            'MarkingTree(nodes=4, levels=3, is_complete=True)'
        )


class TestNaturalOrder:
    """The ordering shared by every tree construction."""

    def test_digits_are_compared_as_numbers(self) -> None:
        """``t2`` before ``t10``, which alphabetical order gets wrong."""
        names = ['t11', 't2', 't10', 't1']
        transitions = [Transition(name) for name in names]
        assert [
            transition.name
            for transition in sorted(transitions, key=_natural_key)
        ] == ['t1', 't2', 't10', 't11']

    def test_text_is_compared_as_text(self) -> None:
        """A name with no digits in it is ordered as it reads."""
        transitions = [Transition(name) for name in ('serve', 'arrive')]
        assert [
            transition.name
            for transition in sorted(transitions, key=_natural_key)
        ] == ['arrive', 'serve']

    def test_digits_and_text_are_never_compared_with_each_other(self) -> None:
        """A name starting with a digit and one starting with a letter."""
        transitions = [Transition(name) for name in ('t1', '1t')]
        assert [
            transition.name
            for transition in sorted(transitions, key=_natural_key)
        ] == ['1t', 't1']
