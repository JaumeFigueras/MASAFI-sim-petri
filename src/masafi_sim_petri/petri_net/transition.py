"""The transition of a Petri net."""

from __future__ import annotations


class Transition:
    """A transition of a Petri net.

    A transition is an event that may happen: an item taken from a buffer, a
    machine starting a job, a message being received. It is enabled when every
    one of its input places can supply the weight of the arc joining them, and
    firing it removes those tokens and produces tokens in its output places.

    In a Place/Transition net a transition carries no state of its own. The
    marking lives in the places, and the connectivity lives in the net, so a
    transition is identified by its name and nothing else. Enabling and firing
    are therefore operations of the net, which is the only object that knows
    which arcs reach this transition.

    Parameters
    ----------
    name : str
        Name of the transition. It identifies the transition within a net,
        which is where uniqueness is enforced; a transition on its own does
        not know about other transitions.

    Raises
    ------
    ValueError
        If `name` is empty or blank.

    See Also
    --------
    masafi_sim_petri.petri_net.place.Place : The passive node, which holds the
        tokens a transition consumes and produces.

    Examples
    --------
    >>> from masafi_sim_petri import Transition
    >>> transition = Transition('serve_customer')
    >>> transition.name
    'serve_customer'
    >>> print(transition)
    serve_customer
    """

    def __init__(self, name: str) -> None:
        if not name or not name.strip():
            raise ValueError('The name of a transition cannot be empty')
        self._name: str = name

    @property
    def name(self) -> str:
        """str: Name of the transition, fixed at construction time."""
        return self._name

    def __str__(self) -> str:
        """Return the name of the transition.

        Returns
        -------
        str
            The name of the transition, so that it reads naturally when
            interpolated into a message.
        """
        return self._name

    def __repr__(self) -> str:
        """Return a representation showing the state of the transition.

        Returns
        -------
        str
            The name of the transition. This is a debugging aid, not an
            expression that reconstructs the transition.
        """
        return f'Transition(name={self._name!r})'
