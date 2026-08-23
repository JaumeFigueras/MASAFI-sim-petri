"""The arc of a Petri net."""

from __future__ import annotations

from masafi_sim_petri.petri_net.place import Place
from masafi_sim_petri.petri_net.transition import Transition


class Arc:
    """A weighted, directed arc of a Petri net.

    An arc joins a place to a transition or a transition to a place. A Petri
    net is a bipartite graph, so an arc between two places or between two
    transitions is not a valid arc and is rejected.

    The direction says what the arc does when its transition fires. An arc from
    a place to a transition is an *input arc* of that transition: firing
    removes `weight` tokens from the place. An arc from a transition to a place
    is an *output arc*: firing adds `weight` tokens to the place.

    An arc holds its two endpoints, but neither endpoint holds the arc. The net
    owns the collection of arcs, so the object graph stays free of cycles.

    Parameters
    ----------
    source : Place or Transition
        Node the arc leaves.
    target : Place or Transition
        Node the arc enters. Exactly one of `source` and `target` must be a
        place and the other a transition.
    weight : int, optional
        Number of tokens the arc moves each time its transition fires.
        Defaults to ``1``.

    Raises
    ------
    ValueError
        If `source` and `target` are not one place and one transition, or if
        `weight` is smaller than ``1``.

    Examples
    --------
    >>> from masafi_sim_petri import Arc, Place, Transition
    >>> buffer = Place('buffer', initial_marking=6)
    >>> pack = Transition('pack')
    >>> arc = Arc(buffer, pack, weight=6)
    >>> arc.is_input
    True
    >>> arc.weight
    6
    >>> print(arc)
    buffer --6--> pack
    """

    def __init__(
        self,
        source: Place | Transition,
        target: Place | Transition,
        weight: int = 1,
    ) -> None:
        if isinstance(source, Place) and isinstance(target, Transition):
            self._place: Place = source
            self._transition: Transition = target
            self._is_input: bool = True
        elif isinstance(source, Transition) and isinstance(target, Place):
            self._place = target
            self._transition = source
            self._is_input = False
        else:
            raise ValueError(
                'An arc must join a place and a transition, got '
                f'{type(source).__name__} and {type(target).__name__}'
            )
        if weight < 1:
            raise ValueError(
                f'The weight of an arc must be at least 1, got {weight}'
            )
        self._source: Place | Transition = source
        self._target: Place | Transition = target
        self._weight: int = weight

    @property
    def source(self) -> Place | Transition:
        """Place or Transition: Node the arc leaves."""
        return self._source

    @property
    def target(self) -> Place | Transition:
        """Place or Transition: Node the arc enters."""
        return self._target

    @property
    def place(self) -> Place:
        """Place: The place endpoint, whichever end of the arc it is on."""
        return self._place

    @property
    def transition(self) -> Transition:
        """Transition: The transition endpoint, whichever end it is on."""
        return self._transition

    @property
    def weight(self) -> int:
        """int: Number of tokens moved each time the transition fires."""
        return self._weight

    @property
    def is_input(self) -> bool:
        """bool: Whether this is an input arc of its transition.

        ``True`` when the arc runs from the place to the transition, so that
        firing removes tokens from the place. It is the complement of
        :attr:`is_output`.
        """
        return self._is_input

    @property
    def is_output(self) -> bool:
        """bool: Whether this is an output arc of its transition.

        ``True`` when the arc runs from the transition to the place, so that
        firing adds tokens to the place. It is the complement of
        :attr:`is_input`.
        """
        return not self._is_input

    def __str__(self) -> str:
        """Return the arc as a labelled edge.

        Returns
        -------
        str
            The source, the weight and the target, so that a net can be read
            as a list of edges.
        """
        return f'{self._source} --{self._weight}--> {self._target}'

    def __repr__(self) -> str:
        """Return a representation showing the full state of the arc.

        Returns
        -------
        str
            The two endpoints and the weight. This is a debugging aid, not an
            expression that reconstructs the arc.
        """
        return (
            f'Arc(source={self._source!r}, target={self._target!r}, '
            f'weight={self._weight})'
        )
