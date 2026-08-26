"""The reachability tree of a Petri net."""

from __future__ import annotations

import re
from collections import deque
from enum import StrEnum

from masafi_sim_petri.analysis.boundedness import _covers_strictly
from masafi_sim_petri.petri_net.petri_net import PetriNet
from masafi_sim_petri.petri_net.transition import Transition


class UnboundedNetError(ValueError):
    """Raised when a net has no finite reachability tree.

    An unbounded net reaches infinitely many markings, so its reachability
    tree is an infinite object. Building one can only ever return part of it,
    and this exception says so rather than returning that part as though it
    were the whole.
    """


class NodeLabel(StrEnum):
    """What a node of a reachability tree is, and why it stopped there.

    Attributes
    ----------
    INTERNAL
        The node was expanded: its children are every marking reachable from
        it in one firing. Only a node with this label has children.
    OLD
        The marking is already in the tree, so expanding it again would
        repeat a subtree that has been built once. This is what keeps the
        tree of a bounded net finite.
    DEADLOCK
        No transition is enabled in this marking. The net has stopped, and
        the path from the root is a firing sequence that kills it.
    TRUNCATED
        The node has enabled transitions and a new marking, but the level
        limit was reached before it could be expanded. Its presence is what
        makes :attr:`ReachabilityTree.is_complete` ``False``.
    """

    INTERNAL = 'internal'
    OLD = 'old'
    DEADLOCK = 'deadlock'
    TRUNCATED = 'truncated'


class ReachabilityTreeNode:
    """One marking in a reachability tree, and how it was reached.

    A node is created by the tree that owns it, never on its own: its label
    and its children are decided by the construction, and a node built by
    hand would have neither.

    The same marking may appear at several nodes, which is the whole
    difference between the tree and the reachability graph. In the tree a
    marking is an *occurrence*, identified by the firing sequence that
    reached it; in the graph it is a *state*, identified by its vector.

    Parameters
    ----------
    marking : tuple of int
        The marking at this node.
    level : int
        Depth in the tree, counting the root as level one.
    parent : ReachabilityTreeNode, optional
        The node this one was reached from. ``None`` at the root.
    incoming_transition : Transition, optional
        The transition whose firing reached this marking. ``None`` at the
        root.

    Attributes
    ----------
    marking : tuple of int
        The marking at this node.
    level : int
        Depth in the tree, the root being level one.
    label : NodeLabel
        What kind of node this is.
    parent : ReachabilityTreeNode or None
        The node this one was reached from.
    incoming_transition : Transition or None
        The transition that reached this marking.
    children : tuple of ReachabilityTreeNode
        The successors, ordered by transition name.
    """

    def __init__(
        self,
        marking: tuple[int, ...],
        level: int,
        parent: ReachabilityTreeNode | None = None,
        incoming_transition: Transition | None = None,
    ) -> None:
        self._marking: tuple[int, ...] = marking
        self._level: int = level
        self._parent: ReachabilityTreeNode | None = parent
        self._incoming_transition: Transition | None = incoming_transition
        self._children: list[ReachabilityTreeNode] = []
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
    def parent(self) -> ReachabilityTreeNode | None:
        """ReachabilityTreeNode or None: The node this one was reached from."""
        return self._parent

    @property
    def incoming_transition(self) -> Transition | None:
        """Transition or None: The transition that reached this marking."""
        return self._incoming_transition

    @property
    def children(self) -> tuple[ReachabilityTreeNode, ...]:
        """tuple of ReachabilityTreeNode: The successors, left to right.

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

    def path_from_root(self) -> tuple[ReachabilityTreeNode, ...]:
        """Return the nodes from the root down to this one, inclusive.

        Returns
        -------
        tuple of ReachabilityTreeNode
            The root first, this node last.
        """
        path: list[ReachabilityTreeNode] = []
        node: ReachabilityTreeNode | None = self
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

    def _add_child(self, child: ReachabilityTreeNode) -> None:
        """Append a child to this node.

        Package internal, for the same reason as :meth:`_set_label`.

        Parameters
        ----------
        child : ReachabilityTreeNode
            The node to append. Children are appended in transition order,
            so no sorting happens here.
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


class ReachabilityTree:
    """The reachability tree of a net, built from its initial marking.

    The root is :math:`M_0`. Every node is expanded by firing each of its
    enabled transitions in turn, one child per transition, ordered by
    transition name so that the tree drawn from this object is the tree drawn
    by hand. Construction is breadth first: a level is finished before the
    next one is begun.

    A branch stops for one of three reasons, and the node's
    :class:`NodeLabel` says which: the marking is already in the tree
    (:attr:`~NodeLabel.OLD`), no transition is enabled
    (:attr:`~NodeLabel.DEADLOCK`), or the level limit was reached
    (:attr:`~NodeLabel.TRUNCATED`). The first two are properties of the net.
    The third is a property of the question asked, and
    :attr:`is_complete` reports whether it happened.

    Parameters
    ----------
    net : PetriNet
        Net to build the tree of. It is fired during construction and its
        marking is restored before returning.
    refuse_unbounded : bool, optional
        Whether to detect an unbounded net and raise instead of building a
        tree that could never be finished. Default ``True``.
    max_levels : int, optional
        The greatest number of levels to build, the root counting as one. A
        node that would have been expanded at that level is labelled
        :attr:`~NodeLabel.TRUNCATED` instead. Default ``None``, meaning no
        limit.

    Raises
    ------
    ValueError
        If ``max_levels`` is less than one, or if ``refuse_unbounded`` is
        ``False`` and no ``max_levels`` is given: with neither a refusal nor
        a limit, an unbounded net would be built for ever.
    UnboundedNetError
        If ``refuse_unbounded`` is ``True`` and the net is found to be
        unbounded.

    Attributes
    ----------
    root : ReachabilityTreeNode
        The node holding :math:`M_0`.
    is_complete : bool
        Whether the tree is the whole tree.

    Notes
    -----
    **Old is decided against the whole tree, not against the path.** A
    marking is labelled :attr:`~NodeLabel.OLD` when it appears anywhere in
    the part of the tree already built, which is what makes every distinct
    reachable marking appear exactly once as an expanded node. Some
    presentations compare only against the path back to the root, which gives
    a larger tree with the same leaves; if that is the variant wanted, it is
    the one comparison in the construction that changes.

    **Old beats deadlock.** A dead marking reached twice is a deadlock the
    first time and old the second, so each dead marking is reported once.

    **Unboundedness is found by the covering rule**, the same one
    :func:`~masafi_sim_petri.analysis.boundedness.is_bounded` uses: a marking
    that strictly covers one of its own ancestors can be pumped for ever.
    With ``max_levels`` set, the limit may be reached before any such pair
    appears, in which case an unbounded net comes back truncated rather than
    raising.

    Examples
    --------
    A token going round a cycle gives a tree that closes on itself:

    >>> from masafi_sim_petri import Arc, PetriNet, Place, Transition
    >>> from masafi_sim_petri.analysis import ReachabilityTree
    >>> net = PetriNet()
    >>> idle = net.add_place(Place('idle', initial_marking=1))
    >>> busy = net.add_place(Place('busy'))
    >>> t1 = net.add_transition(Transition('t1'))
    >>> t2 = net.add_transition(Transition('t2'))
    >>> _ = net.add_arc(Arc(idle, t1))
    >>> _ = net.add_arc(Arc(t1, busy))
    >>> _ = net.add_arc(Arc(busy, t2))
    >>> _ = net.add_arc(Arc(t2, idle))
    >>> tree = ReachabilityTree(net)
    >>> print(tree)
    (1, 0)
    └── t1 -> (0, 1)
        └── t2 -> (1, 0) [old]
    >>> tree.is_complete
    True
    """

    def __init__(
        self,
        net: PetriNet,
        refuse_unbounded: bool = True,
        max_levels: int | None = None,
    ) -> None:
        if max_levels is not None and max_levels < 1:
            raise ValueError(
                f'A tree has at least one level, got max_levels={max_levels}'
            )
        if not refuse_unbounded and max_levels is None:
            raise ValueError(
                'Without max_levels, an unbounded net would be built for '
                'ever; either give a level limit or leave refuse_unbounded '
                'set'
            )
        self._is_complete: bool = True
        self._nodes: tuple[ReachabilityTreeNode, ...] = self._build(
            net, refuse_unbounded, max_levels
        )
        self._root: ReachabilityTreeNode = self._nodes[0]

    def _build(
        self,
        net: PetriNet,
        refuse_unbounded: bool,
        max_levels: int | None,
    ) -> tuple[ReachabilityTreeNode, ...]:
        """Build the tree, breadth first, from the initial marking of a net.

        Parameters
        ----------
        net : PetriNet
            Net to build the tree of.
        refuse_unbounded : bool
            Whether to raise on an unbounded net.
        max_levels : int or None
            The greatest number of levels to build.

        Returns
        -------
        tuple of ReachabilityTreeNode
            Every node, in the order it was created, so the root is first and
            the levels follow one another.

        Raises
        ------
        UnboundedNetError
            If the net is unbounded and ``refuse_unbounded`` is set.
        """
        saved_marking = net.marking
        try:
            root = ReachabilityTreeNode(net.initial_marking, 1)
            nodes = [root]
            seen = {root.marking}
            pending = deque([root])
            while pending:
                node = pending.popleft()
                net.marking = node.marking
                enabled = sorted(net.enabled_transitions(), key=_natural_key)
                if not enabled:
                    node._set_label(NodeLabel.DEADLOCK)
                    continue
                if max_levels is not None and node.level >= max_levels:
                    node._set_label(NodeLabel.TRUNCATED)
                    self._is_complete = False
                    continue
                ancestors = node.path_from_root()
                for transition in enabled:
                    net.marking = node.marking
                    net.fire(transition)
                    successor = net.marking
                    if refuse_unbounded and any(
                        _covers_strictly(successor, ancestor.marking)
                        for ancestor in ancestors
                    ):
                        raise UnboundedNetError(
                            f'Marking {successor} strictly covers an earlier '
                            f'marking on the same path, so the net is '
                            f'unbounded and its reachability tree is '
                            f'infinite'
                        )
                    child = ReachabilityTreeNode(
                        successor, node.level + 1, node, transition
                    )
                    node._add_child(child)
                    nodes.append(child)
                    if successor in seen:
                        child._set_label(NodeLabel.OLD)
                    else:
                        seen.add(successor)
                        pending.append(child)
        finally:
            net.marking = saved_marking
        return tuple(nodes)

    @property
    def root(self) -> ReachabilityTreeNode:
        """ReachabilityTreeNode: The node holding the initial marking."""
        return self._root

    @property
    def is_complete(self) -> bool:
        """bool: Whether the tree is the whole tree.

        ``False`` when some node was left unexpanded because the level limit
        was reached, which means the net has markings this tree does not
        show. The nodes in question are the ones
        :meth:`truncated_nodes` returns.
        """
        return self._is_complete

    @property
    def levels(self) -> int:
        """int: The number of levels the tree has, the root counting as one."""
        return max(node.level for node in self._nodes)

    def nodes(self) -> tuple[ReachabilityTreeNode, ...]:
        """Return every node, level by level.

        Returns
        -------
        tuple of ReachabilityTreeNode
            The root first, then each level in left-to-right order.
        """
        return self._nodes

    def leaves(self) -> tuple[ReachabilityTreeNode, ...]:
        """Return the nodes that were not expanded.

        Returns
        -------
        tuple of ReachabilityTreeNode
            Every node with no children, in the order they were created.
        """
        return tuple(node for node in self._nodes if node.is_leaf)

    def nodes_labelled(
        self, label: NodeLabel
    ) -> tuple[ReachabilityTreeNode, ...]:
        """Return every node carrying a given label.

        Parameters
        ----------
        label : NodeLabel
            The label to select.

        Returns
        -------
        tuple of ReachabilityTreeNode
            The matching nodes, in the order they were created.
        """
        return tuple(node for node in self._nodes if node.label is label)

    def deadlocks(self) -> tuple[ReachabilityTreeNode, ...]:
        """Return the nodes whose marking enables no transition.

        A dead marking reached by several firing sequences appears once,
        since every later occurrence is labelled :attr:`~NodeLabel.OLD`.
        Each node's :meth:`~ReachabilityTreeNode.firing_sequence` is a
        sequence that kills the net.

        Returns
        -------
        tuple of ReachabilityTreeNode
            The deadlock nodes, in the order they were created.

        Notes
        -----
        These are all the deadlocks of the net only when the tree is
        complete. Check :attr:`is_complete` before reading a ``()`` as
        deadlock freedom.
        """
        return self.nodes_labelled(NodeLabel.DEADLOCK)

    def truncated_nodes(self) -> tuple[ReachabilityTreeNode, ...]:
        """Return the nodes left unexpanded by the level limit.

        Returns
        -------
        tuple of ReachabilityTreeNode
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
        self, node: ReachabilityTreeNode, prefix: str, lines: list[str]
    ) -> None:
        """Append the drawing of the children of a node to ``lines``.

        Parameters
        ----------
        node : ReachabilityTreeNode
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
            assert transition is not None  # only the root has none
            lines.append(
                f'{prefix}{"└── " if is_last else "├── "}'
                f'{transition.name} -> {child}'
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
