"""Trees whose nodes are markings.

The structure shared by the reachability tree and the coverability tree: the
nodes, the labels that say why a branch stopped, the queries over a finished
tree and the drawing of it. What differs between the two is how the tree is
*built*, and that is left to the subclasses.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from enum import StrEnum

from masafi_sim_petri.petri_net.transition import Transition


class UnboundedNetError(ValueError):
    """Raised when a net has no finite tree of the kind asked for.

    An unbounded net reaches infinitely many markings, so its reachability
    tree is an infinite object. Building one can only ever return part of it,
    and this exception says so rather than returning that part as though it
    were the whole. The coverability tree is the construction that does have
    an answer for such a net.
    """


class NodeLabel(StrEnum):
    """What a node of a marking tree is, and why it stopped there.

    ``INTERNAL`` is a node that was expanded: its children are every marking
    reachable from it in one firing, and it is the only label a node with
    children carries. The other three are the three reasons a branch ends.

    ``OLD`` is a marking already in the tree. Expanding it again would repeat
    a subtree that has been built once, and in a net with a cycle the branch
    would never end. This is what keeps the tree of a bounded net finite.

    ``DEADLOCK`` is a marking enabling no transition. The net has stopped,
    and the path from the root is a firing sequence that kills it.

    ``TRUNCATED`` is a node with enabled transitions and a new marking that
    was left unexpanded because the level limit was reached. It is the one
    label that describes the question rather than the net, and its presence
    is what makes :attr:`MarkingTree.is_complete` ``False``.
    """

    INTERNAL = 'internal'
    OLD = 'old'
    DEADLOCK = 'deadlock'
    TRUNCATED = 'truncated'


class MarkingTreeNode:
    """One marking in a marking tree, and how it was reached.

    A node is created by the construction that owns it, never on its own: its
    label and its children are decided by that construction, and a node built
    by hand would have neither.

    The same marking may appear at several nodes, which is the whole
    difference between a tree and the reachability graph. In the tree a
    marking is an *occurrence*, identified by the firing sequence that
    reached it; in the graph it is a *state*, identified by its vector.

    Parameters
    ----------
    marking : tuple of int
        The marking at this node.
    level : int
        Depth in the tree, counting the root as level one.
    parent : MarkingTreeNode, optional
        The node this one was reached from. ``None`` at the root.
    incoming_transition : Transition, optional
        The transition whose firing reached this marking. ``None`` at the
        root.
    """

    def __init__(
        self,
        marking: tuple[int, ...],
        level: int,
        parent: MarkingTreeNode | None = None,
        incoming_transition: Transition | None = None,
    ) -> None:
        self._marking: tuple[int, ...] = marking
        self._level: int = level
        self._parent: MarkingTreeNode | None = parent
        self._incoming_transition: Transition | None = incoming_transition
        self._children: list[MarkingTreeNode] = []
        self._label: NodeLabel = NodeLabel.INTERNAL

    @property
    def marking(self) -> tuple[int, ...]:
        """tuple of int: The marking at this node."""
        return self._marking

    @property
    def level(self) -> int:
        """int: Depth in the tree, the root being level one."""
        return self._level

    @property
    def label(self) -> NodeLabel:
        """NodeLabel: What kind of node this is."""
        return self._label

    @property
    def parent(self) -> MarkingTreeNode | None:
        """MarkingTreeNode or None: The node this one was reached from."""
        return self._parent

    @property
    def incoming_transition(self) -> Transition | None:
        """Transition or None: The transition that reached this marking."""
        return self._incoming_transition

    @property
    def children(self) -> tuple[MarkingTreeNode, ...]:
        """tuple of MarkingTreeNode: The successors, left to right.

        Ordered by transition name, so the leftmost child is the one reached
        by the first transition in natural order.
        """
        return tuple(self._children)

    @property
    def is_root(self) -> bool:
        """bool: Whether this node is the initial marking."""
        return self._parent is None

    @property
    def is_leaf(self) -> bool:
        """bool: Whether this node has no children."""
        return not self._children

    def path_from_root(self) -> tuple[MarkingTreeNode, ...]:
        """Return the nodes from the root down to this one, inclusive.

        Returns
        -------
        tuple of MarkingTreeNode
            The root first, this node last.
        """
        path: list[MarkingTreeNode] = []
        node: MarkingTreeNode | None = self
        while node is not None:
            path.append(node)
            node = node._parent
        return tuple(reversed(path))

    def firing_sequence(self) -> tuple[Transition, ...]:
        """Return the transitions fired to reach this node from the root.

        Returns
        -------
        tuple of Transition
            The firing sequence, in the order it was fired. Empty at the
            root.
        """
        return tuple(
            node._incoming_transition
            for node in self.path_from_root()
            if node._incoming_transition is not None
        )

    def _set_label(self, label: NodeLabel) -> None:
        """Set the label of this node.

        Package internal: the label is decided by the construction, which is
        the only thing that knows why a node was not expanded.

        Parameters
        ----------
        label : NodeLabel
            The label to give this node.
        """
        self._label = label

    def _add_child(self, child: MarkingTreeNode) -> None:
        """Append a child to this node.

        Package internal, for the same reason as :meth:`_set_label`.

        Parameters
        ----------
        child : MarkingTreeNode
            The node to append. Children are appended in transition order, so
            no sorting happens here.
        """
        self._children.append(child)

    def __str__(self) -> str:
        """Return the marking and, unless internal, the label.

        Returns
        -------
        str
            For example ``'(1, 0) [old]'``.
        """
        if self._label is NodeLabel.INTERNAL:
            return str(self._marking)
        return f'{self._marking} [{self._label}]'

    def __repr__(self) -> str:
        """Return an unambiguous representation of the node.

        Returns
        -------
        str
            The marking, the level and the label.
        """
        return (
            f'{type(self).__name__}(marking={self._marking!r}, '
            f'level={self._level!r}, label={self._label!s})'
        )


class MarkingTree:
    """A finished tree of markings: what it holds and what it can be asked.

    This class is the result, not the construction. A subclass fires the net,
    decides which node stops a branch and why, and hands the finished nodes
    over; everything here works on that outcome and is the same whether the
    markings came from the reachability tree or from the coverability tree.

    Parameters
    ----------
    nodes : iterable of MarkingTreeNode
        Every node, in the order it was created. The construction is breadth
        first, so the root comes first and the levels follow one another.
    is_complete : bool
        Whether the tree is the whole tree, or was stopped by a level limit.

    Raises
    ------
    ValueError
        If no nodes are given. A tree has a root.
    """

    def __init__(
        self, nodes: Iterable[MarkingTreeNode], is_complete: bool
    ) -> None:
        self._nodes: tuple[MarkingTreeNode, ...] = tuple(nodes)
        if not self._nodes:
            raise ValueError('A tree has a root, so it has at least one node')
        self._root: MarkingTreeNode = self._nodes[0]
        self._is_complete: bool = is_complete

    @property
    def root(self) -> MarkingTreeNode:
        """MarkingTreeNode: The node holding the initial marking."""
        return self._root

    @property
    def is_complete(self) -> bool:
        """bool: Whether the tree is the whole tree.

        ``False`` when some node was left unexpanded because the level limit
        was reached, which means the net has markings this tree does not
        show. The nodes in question are the ones :meth:`truncated_nodes`
        returns.
        """
        return self._is_complete

    @property
    def levels(self) -> int:
        """int: The number of levels the tree has, the root counting as one."""
        return max(node.level for node in self._nodes)

    def nodes(self) -> tuple[MarkingTreeNode, ...]:
        """Return every node, level by level.

        Returns
        -------
        tuple of MarkingTreeNode
            The root first, then each level in left-to-right order.
        """
        return self._nodes

    def leaves(self) -> tuple[MarkingTreeNode, ...]:
        """Return the nodes that were not expanded.

        Returns
        -------
        tuple of MarkingTreeNode
            Every node with no children, in the order they were created.
        """
        return tuple(node for node in self._nodes if node.is_leaf)

    def nodes_labelled(self, label: NodeLabel) -> tuple[MarkingTreeNode, ...]:
        """Return every node carrying a given label.

        Parameters
        ----------
        label : NodeLabel
            The label to select.

        Returns
        -------
        tuple of MarkingTreeNode
            The matching nodes, in the order they were created.
        """
        return tuple(node for node in self._nodes if node.label is label)

    def deadlocks(self) -> tuple[MarkingTreeNode, ...]:
        """Return the nodes whose marking enables no transition.

        A dead marking reached by several firing sequences appears once,
        since every later occurrence is labelled :attr:`~NodeLabel.OLD`.
        Each node's :meth:`~MarkingTreeNode.firing_sequence` is a sequence
        that kills the net.

        Returns
        -------
        tuple of MarkingTreeNode
            The deadlock nodes, in the order they were created.

        Notes
        -----
        These are all the deadlocks of the net only when the tree is
        complete. Check :attr:`is_complete` before reading a ``()`` as
        deadlock freedom.
        """
        return self.nodes_labelled(NodeLabel.DEADLOCK)

    def truncated_nodes(self) -> tuple[MarkingTreeNode, ...]:
        """Return the nodes left unexpanded by the level limit.

        Returns
        -------
        tuple of MarkingTreeNode
            The truncated nodes, in the order they were created. Empty when
            :attr:`is_complete` is ``True``.
        """
        return self.nodes_labelled(NodeLabel.TRUNCATED)

    def markings(self) -> tuple[tuple[int, ...], ...]:
        """Return the distinct markings in the tree, in order of first sight.

        Returns
        -------
        tuple of tuple of int
            Each marking once, however many nodes hold it. When the tree is
            complete this is the reachable set of the net.
        """
        seen: dict[tuple[int, ...], None] = {}
        for node in self._nodes:
            seen.setdefault(node.marking, None)
        return tuple(seen)

    def __len__(self) -> int:
        """Return the number of nodes in the tree.

        Returns
        -------
        int
            The node count, occurrences and not distinct markings.
        """
        return len(self._nodes)

    def __str__(self) -> str:
        """Return the tree drawn as indented text.

        Each line but the root carries the transition that was fired, the
        marking it reached and, unless the node was expanded, its label.

        Returns
        -------
        str
            The drawing, without a trailing newline.
        """
        lines = [str(self._root)]
        self._draw(self._root, '', lines)
        return '\n'.join(lines)

    def _draw(
        self, node: MarkingTreeNode, prefix: str, lines: list[str]
    ) -> None:
        """Append the drawing of the children of a node to ``lines``.

        Parameters
        ----------
        node : MarkingTreeNode
            The node whose children are drawn.
        prefix : str
            The indentation carried down from the ancestors.
        lines : list of str
            The drawing so far, appended to in place.
        """
        children = node.children
        for position, child in enumerate(children):
            is_last = position == len(children) - 1
            transition = child.incoming_transition
            arrow = f'{transition.name} -> ' if transition is not None else ''
            lines.append(
                f'{prefix}{"└── " if is_last else "├── "}{arrow}{child}'
            )
            self._draw(child, f'{prefix}{"    " if is_last else "│   "}', lines)

    def __repr__(self) -> str:
        """Return an unambiguous representation of the tree.

        Returns
        -------
        str
            The node count, the number of levels and whether it is complete.
        """
        return (
            f'{type(self).__name__}(nodes={len(self._nodes)}, '
            f'levels={self.levels}, is_complete={self._is_complete!r})'
        )


def _natural_key(transition: Transition) -> tuple[tuple[int, int, str], ...]:
    """Return a sort key ordering names the way they are read.

    Splitting a name into runs of digits and runs of anything else, and
    comparing the digit runs as numbers, is what puts ``t2`` before ``t10``.
    Plain alphabetical order does not: it compares ``'2'`` with ``'1'`` and
    puts ``t10`` second.

    Package internal, shared by every tree construction so that a net drawn
    twice is drawn the same way.

    Parameters
    ----------
    transition : Transition
        The transition whose name is the key.

    Returns
    -------
    tuple
        A key comparing digit runs numerically and other runs as text. Each
        run is a triple so that numbers and text never have to be compared
        with each other.
    """
    return tuple(
        (0, int(run), '') if run.isdigit() else (1, 0, run)
        for run in re.split(r'(\d+)', transition.name)
        if run
    )
