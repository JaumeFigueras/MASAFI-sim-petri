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
        self._name: str = ''
        self._set_name(name)

    @property
    def name(self) -> str:
        """str: Name of the transition.

        The name identifies the transition inside a net, so it cannot be
        assigned directly: the net indexes its transitions by name and would be
        left holding a stale entry. Use
        :meth:`~masafi_sim_petri.petri_net.petri_net.PetriNet.rename_transition`,
        which renames the transition and updates the index together.
        """
        return self._name

    def _set_name(self, name: str) -> None:
        """Set the name of the transition, validating it.

        Internal to the package. A transition that belongs to a net must be
        renamed through
        :meth:`~masafi_sim_petri.petri_net.petri_net.PetriNet.rename_transition`,
        which checks the new name against the other transitions of the net and
        keeps its index in step.

        Parameters
        ----------
        name : str
            New name of the transition.

        Raises
        ------
        ValueError
            If `name` is empty or blank.
        """
        if not name or not name.strip():
            raise ValueError('The name of a transition cannot be empty')
        self._name = name

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
