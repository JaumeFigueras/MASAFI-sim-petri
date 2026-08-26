"""The reachability tree of a Petri net."""

from __future__ import annotations

from collections import deque

from masafi_sim_petri.analysis.boundedness import _covers_strictly
from masafi_sim_petri.analysis.marking_tree import (
    MarkingTree,
    MarkingTreeNode,
    NodeLabel,
    UnboundedNetError,
    _natural_key,
)
from masafi_sim_petri.petri_net.petri_net import PetriNet


class ReachabilityTree(MarkingTree):
    """The reachability tree of a net, built from its initial marking.

    The root is :math:`M_0`. Every node is expanded by firing each of its
    enabled transitions in turn, one child per transition, ordered by
    transition name so that the tree drawn from this object is the tree drawn
    by hand. Construction is breadth first: a level is finished before the
    next one is begun.

    A branch stops for one of three reasons, and the node's
    :class:`~masafi_sim_petri.analysis.marking_tree.NodeLabel` says which: the
    marking is already in the tree (``OLD``), no transition is enabled
    (``DEADLOCK``), or the level limit was reached (``TRUNCATED``). The first
    two are properties of the net. The third is a property of the question
    asked, and :attr:`~masafi_sim_petri.analysis.marking_tree.MarkingTree.is_complete`
    reports whether it happened.

    Everything the finished tree can be asked -- its nodes, its leaves, its
    deadlocks, its drawing -- comes from
    :class:`~masafi_sim_petri.analysis.marking_tree.MarkingTree`, which the
    coverability tree will share.

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
        ``TRUNCATED`` instead. Default ``None``, meaning no limit.

    Raises
    ------
    ValueError
        If ``max_levels`` is less than one, or if ``refuse_unbounded`` is
        ``False`` and no ``max_levels`` is given: with neither a refusal nor
        a limit, an unbounded net would be built for ever.
    UnboundedNetError
        If ``refuse_unbounded`` is ``True`` and the net is found to be
        unbounded.

    Notes
    -----
    **Old is decided against the whole tree, not against the path.** A
    marking is labelled ``OLD`` when it appears anywhere in the part of the
    tree already built, which is what makes every distinct reachable marking
    appear exactly once as an expanded node. Some presentations compare only
    against the path back to the root, which gives a larger tree with the
    same leaves; if that is the variant wanted, it is the one comparison in
    the construction that changes.

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
        nodes, is_complete = _build(net, refuse_unbounded, max_levels)
        super().__init__(nodes, is_complete)


def _build(
    net: PetriNet, refuse_unbounded: bool, max_levels: int | None
) -> tuple[tuple[MarkingTreeNode, ...], bool]:
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
    tuple of MarkingTreeNode
        Every node, in the order it was created, so the root is first and the
        levels follow one another.
    bool
        Whether the tree is complete, that is whether the level limit left
        every node expanded.

    Raises
    ------
    UnboundedNetError
        If the net is unbounded and ``refuse_unbounded`` is set.
    """
    saved_marking = net.marking
    is_complete = True
    try:
        root = MarkingTreeNode(net.initial_marking, 1)
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
                is_complete = False
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
                        f'marking on the same path, so the net is unbounded '
                        f'and its reachability tree is infinite'
                    )
                child = MarkingTreeNode(
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
    return tuple(nodes), is_complete
