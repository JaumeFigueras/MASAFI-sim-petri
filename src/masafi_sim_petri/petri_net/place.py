"""The place of a Petri net."""

from __future__ import annotations


class Place:
    """A place of a Petri net.

    A place holds a non-negative number of tokens, its *marking*. Places are
    unbounded: no capacity limits how many tokens a place may hold.

    The place does not know which arcs are attached to it. Connectivity is
    owned by the net, so a place can be created, tested and reasoned about on
    its own.

    Parameters
    ----------
    name : str
        Name of the place. It identifies the place within a net, which is
        where uniqueness is enforced; a place on its own does not know about
        other places.
    initial_marking : int, optional
        Number of tokens the place holds when the net starts, and the value
        restored by :meth:`reset`. Defaults to ``0``.

    Raises
    ------
    ValueError
        If `name` is empty or blank, or if `initial_marking` is negative.

    Examples
    --------
    >>> from masafi_sim_petri import Place
    >>> place = Place('p1', initial_marking=2)
    >>> place.marking
    2
    >>> place.add_tokens()
    >>> place.marking
    3
    >>> place.reset()
    >>> place.marking
    2
    """

    def __init__(self, name: str, initial_marking: int = 0) -> None:
        self._name: str = ''
        self._set_name(name)
        if initial_marking < 0:
            raise ValueError(
                'The initial marking of a place cannot be negative, got '
                f'{initial_marking}'
            )
        self._initial_marking: int = initial_marking
        self._marking: int = initial_marking

    @property
    def name(self) -> str:
        """str: Name of the place.

        The name identifies the place inside a net, so it cannot be assigned
        directly: the net indexes its places by name and would be left holding
        a stale entry. Use
        :meth:`~masafi_sim_petri.petri_net.petri_net.PetriNet.rename_place`,
        which renames the place and updates the index together.
        """
        return self._name

    def _set_name(self, name: str) -> None:
        """Set the name of the place, validating it.

        Internal to the package. A place that belongs to a net must be renamed
        through
        :meth:`~masafi_sim_petri.petri_net.petri_net.PetriNet.rename_place`,
        which checks the new name against the other places of the net and
        keeps its index in step.

        Parameters
        ----------
        name : str
            New name of the place.

        Raises
        ------
        ValueError
            If `name` is empty or blank.
        """
        if not name or not name.strip():
            raise ValueError('The name of a place cannot be empty')
        self._name = name

    @property
    def initial_marking(self) -> int:
        """int: Marking the place starts from, fixed at construction time."""
        return self._initial_marking

    @property
    def marking(self) -> int:
        """int: Number of tokens currently held by the place.

        Assigning to this property replaces the marking outright, without
        going through the firing rule. It is meant for restoring a state, as
        the reachability analysis does when it revisits a marking it has
        already explored.

        Raises
        ------
        ValueError
            If the assigned value is negative.
        """
        return self._marking

    @marking.setter
    def marking(self, value: int) -> None:
        if value < 0:
            raise ValueError(
                f'The marking of a place cannot be negative, got {value}'
            )
        self._marking = value

    def has_tokens(self, count: int = 1) -> bool:
        """Test whether the place holds at least `count` tokens.

        This is the enabling test used before removing tokens: a transition
        asks its input places whether they can supply the weight of the
        connecting arc.

        Parameters
        ----------
        count : int, optional
            Number of tokens to test for. Defaults to ``1``. A count of ``0``
            is always satisfied.

        Returns
        -------
        bool
            ``True`` if the place holds `count` tokens or more.

        Raises
        ------
        ValueError
            If `count` is negative.
        """
        if count < 0:
            raise ValueError(
                f'Cannot test for a negative number of tokens, got {count}'
            )
        return self._marking >= count

    def add_tokens(self, count: int = 1) -> None:
        """Add `count` tokens to the place.

        Parameters
        ----------
        count : int, optional
            Number of tokens to add. Defaults to ``1``. A count of ``0``
            leaves the marking unchanged.

        Raises
        ------
        ValueError
            If `count` is negative.
        """
        if count < 0:
            raise ValueError(
                f'Cannot add a negative number of tokens, got {count}'
            )
        self._marking += count

    def remove_tokens(self, count: int = 1) -> None:
        """Remove `count` tokens from the place.

        Callers check :meth:`has_tokens` first: an attempt to remove more
        tokens than the place holds is a bug in the firing rule, not an
        expected outcome, so it raises instead of clamping.

        Parameters
        ----------
        count : int, optional
            Number of tokens to remove. Defaults to ``1``. A count of ``0``
            leaves the marking unchanged.

        Raises
        ------
        ValueError
            If `count` is negative, or greater than the current marking.
        """
        if count < 0:
            raise ValueError(
                f'Cannot remove a negative number of tokens, got {count}'
            )
        if count > self._marking:
            raise ValueError(
                f'Cannot remove {count} tokens from place {self._name!r}, '
                f'which holds {self._marking}'
            )
        self._marking -= count

    def reset(self) -> None:
        """Restore the marking of the place to its initial marking.

        Used to return a net to its initial state, either between simulation
        runs or before an analysis that starts from the initial marking.
        """
        self._marking = self._initial_marking

    def __str__(self) -> str:
        """Return the name of the place.

        Returns
        -------
        str
            The name of the place, so that it reads naturally when
            interpolated into a message.
        """
        return self._name

    def __repr__(self) -> str:
        """Return a representation showing the full state of the place.

        Returns
        -------
        str
            The name, the initial marking and the current marking. This is a
            debugging aid, not an expression that reconstructs the place.
        """
        return (
            f'Place(name={self._name!r}, '
            f'initial_marking={self._initial_marking}, '
            f'marking={self._marking})'
        )
