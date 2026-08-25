"""The Petri net itself."""

from __future__ import annotations

from collections.abc import Iterable

from masafi_sim_petri.petri_net.arc import Arc
from masafi_sim_petri.petri_net.place import Place
from masafi_sim_petri.petri_net.transition import Transition


class PetriNet:
    """A Place/Transition Petri net.

    The net owns the places, the transitions and the arcs joining them. It is
    the only object that knows the connectivity: places and transitions hold no
    references back to their arcs, so the object graph stays acyclic and each
    node can be reasoned about on its own. Anything that depends on which arcs
    reach a node is therefore an operation of the net.

    Nothing in the net knows about time or about simulation. The same net can
    be handed to a reachability analysis or to a discrete event engine, and
    neither the places nor the transitions need to know which.

    Every collection is returned in the order its members were added, so a run
    over a net is reproducible.

    A net can be built either node by node, with :meth:`add_place`,
    :meth:`add_transition` and :meth:`add_arc`, or in one call by handing the
    nodes and the arcs to the constructor. The two are equivalent: the
    constructor adds the places, then the transitions, then the arcs, through
    those same methods, so it accepts and refuses exactly what they do.

    Parameters
    ----------
    places : iterable of Place, optional
        Places to add, in the order they are to take in the marking vector.
        Defaults to no places.
    transitions : iterable of Transition, optional
        Transitions to add, in the order :meth:`enabled_transitions` is to
        report them. Defaults to no transitions.
    arcs : iterable of Arc, optional
        Arcs to add. Both endpoints of every arc must be among `places` and
        `transitions`; the constructor does not adopt a node it was not given.
        Defaults to no arcs.

    Raises
    ------
    TypeError
        If any argument holds an object of the wrong type.
    ValueError
        For anything :meth:`add_place`, :meth:`add_transition` or
        :meth:`add_arc` refuses: a repeated node, two places or two
        transitions sharing a name, an arc reaching a node the net was not
        given, or a second arc joining the same pair in the same direction.

    Examples
    --------
    Node by node, binding each node as it is added:

    >>> from masafi_sim_petri import Arc, PetriNet, Place, Transition
    >>> net = PetriNet()
    >>> waiting = net.add_place(Place('waiting', initial_marking=2))
    >>> served = net.add_place(Place('served'))
    >>> serve = net.add_transition(Transition('serve'))
    >>> _ = net.add_arc(Arc(waiting, serve))
    >>> _ = net.add_arc(Arc(serve, served))
    >>> net.marking
    (2, 0)

    Or all at once, which reads better when the nodes already exist:

    >>> waiting = Place('waiting', initial_marking=2)
    >>> served = Place('served')
    >>> serve = Transition('serve')
    >>> net = PetriNet(
    ...     places=[waiting, served],
    ...     transitions=[serve],
    ...     arcs=[Arc(waiting, serve), Arc(serve, served)],
    ... )
    >>> net.marking
    (2, 0)
    """

    def __init__(
        self,
        places: Iterable[Place] | None = None,
        transitions: Iterable[Transition] | None = None,
        arcs: Iterable[Arc] | None = None,
    ) -> None:
        # Order and lookup are kept apart on purpose. The lists define the
        # order of the marking vector, which must not move when a node is
        # renamed; the dictionaries are only an index, and a rename edits
        # nothing else.
        self._places: list[Place] = []
        self._place_index: dict[str, Place] = {}
        self._transitions: list[Transition] = []
        self._transition_index: dict[str, Transition] = {}
        self._arcs: list[Arc] = []
        self._input_arcs: dict[Transition, list[Arc]] = {}
        self._output_arcs: dict[Transition, list[Arc]] = {}
        self._affected: dict[Place, set[Transition]] = {}
        # The nodes go in before the arcs, whatever order the caller wrote
        # the three arguments in: an arc can only be added once the net holds
        # both of its endpoints.
        for place in () if places is None else places:
            if not isinstance(place, Place):
                raise TypeError(
                    'places must contain Place objects, got '
                    f'{type(place).__name__}'
                )
            self.add_place(place)
        for transition in () if transitions is None else transitions:
            if not isinstance(transition, Transition):
                raise TypeError(
                    'transitions must contain Transition objects, got '
                    f'{type(transition).__name__}'
                )
            self.add_transition(transition)
        for arc in () if arcs is None else arcs:
            if not isinstance(arc, Arc):
                raise TypeError(
                    f'arcs must contain Arc objects, got {type(arc).__name__}'
                )
            self.add_arc(arc)

    # ------------------------------------------------------------------
    # Building the net
    # ------------------------------------------------------------------

    def add_place(self, place: Place) -> Place:
        """Add a place to the net.

        Parameters
        ----------
        place : Place
            Place to add. Its name must not already be used by another place
            of this net.

        Returns
        -------
        Place
            The place that was added, so that it can be bound to a name and
            used to build arcs in the same expression.

        Raises
        ------
        ValueError
            If the place is already in the net, or if another place of the net
            has the same name.
        """
        if place in self._affected:
            raise ValueError(f'Place {place.name!r} is already in the net')
        if place.name in self._place_index:
            raise ValueError(
                f'The net already has a place named {place.name!r}'
            )
        self._places.append(place)
        self._place_index[place.name] = place
        self._affected[place] = set()
        return place

    def add_transition(self, transition: Transition) -> Transition:
        """Add a transition to the net.

        Parameters
        ----------
        transition : Transition
            Transition to add. Its name must not already be used by another
            transition of this net.

        Returns
        -------
        Transition
            The transition that was added, so that it can be bound to a name
            and used to build arcs in the same expression.

        Raises
        ------
        ValueError
            If the transition is already in the net, or if another transition
            of the net has the same name.
        """
        if transition in self._input_arcs:
            raise ValueError(
                f'Transition {transition.name!r} is already in the net'
            )
        if transition.name in self._transition_index:
            raise ValueError(
                f'The net already has a transition named {transition.name!r}'
            )
        self._transitions.append(transition)
        self._transition_index[transition.name] = transition
        self._input_arcs[transition] = []
        self._output_arcs[transition] = []
        return transition

    def add_arc(self, arc: Arc) -> Arc:
        """Add an arc to the net.

        Both endpoints must already belong to the net. An arc that reaches a
        node the net does not hold would connect two nets together, which is
        not a Petri net.

        Parameters
        ----------
        arc : Arc
            Arc to add.

        Returns
        -------
        Arc
            The arc that was added.

        Raises
        ------
        ValueError
            If either endpoint is not in the net, or if an arc already joins
            the same place and transition in the same direction.
        """
        if arc.place not in self._affected:
            raise ValueError(
                f'Place {arc.place.name!r} is not in the net, so it cannot be '
                'used by an arc of this net'
            )
        if arc.transition not in self._input_arcs:
            raise ValueError(
                f'Transition {arc.transition.name!r} is not in the net, so it '
                'cannot be used by an arc of this net'
            )
        existing = (
            self._input_arcs[arc.transition]
            if arc.is_input
            else self._output_arcs[arc.transition]
        )
        if any(other.place is arc.place for other in existing):
            direction = 'to' if arc.is_input else 'from'
            raise ValueError(
                f'An arc already joins place {arc.place.name!r} {direction} '
                f'transition {arc.transition.name!r}; change its weight '
                'instead of adding a second arc'
            )
        self._arcs.append(arc)
        if arc.is_input:
            self._input_arcs[arc.transition].append(arc)
            self._affected[arc.place].add(arc.transition)
        else:
            self._output_arcs[arc.transition].append(arc)
        return arc

    # ------------------------------------------------------------------
    # Editing the net
    # ------------------------------------------------------------------

    def rename_place(self, place: Place, name: str) -> None:
        """Give a place of the net a new name.

        The net indexes its places by name, so a place cannot be renamed on
        its own without leaving that index pointing at the old name. This
        method renames the place and updates the index together, which is why
        it lives on the net rather than on the place.

        The order of the places is not affected, so the marking vector keeps
        meaning what it meant before the rename.

        Renaming a place to the name it already has does nothing.

        Parameters
        ----------
        place : Place
            Place to rename. It must belong to this net.
        name : str
            New name for the place.

        Raises
        ------
        ValueError
            If the place is not in the net, if `name` is empty or blank, or if
            another place of the net already has that name.
        """
        self._require_place(place)
        if name == place.name:
            return
        if name in self._place_index:
            raise ValueError(
                f'The net already has a place named {name!r}'
            )
        old_name = place.name
        place._set_name(name)
        del self._place_index[old_name]
        self._place_index[name] = place

    def rename_transition(self, transition: Transition, name: str) -> None:
        """Give a transition of the net a new name.

        The counterpart of :meth:`rename_place`, and it exists for the same
        reason: the net indexes its transitions by name and has to update that
        index as the transition is renamed.

        The order of the transitions is not affected, so the order in which
        :meth:`enabled_transitions` reports them does not change.

        Renaming a transition to the name it already has does nothing.

        Parameters
        ----------
        transition : Transition
            Transition to rename. It must belong to this net.
        name : str
            New name for the transition.

        Raises
        ------
        ValueError
            If the transition is not in the net, if `name` is empty or blank,
            or if another transition of the net already has that name.
        """
        self._require_transition(transition)
        if name == transition.name:
            return
        if name in self._transition_index:
            raise ValueError(
                f'The net already has a transition named {name!r}'
            )
        old_name = transition.name
        transition._set_name(name)
        del self._transition_index[old_name]
        self._transition_index[name] = transition

    # ------------------------------------------------------------------
    # The structure of the net
    # ------------------------------------------------------------------

    @property
    def places(self) -> tuple[Place, ...]:
        """tuple of Place: The places, in the order they were added."""
        return tuple(self._places)

    @property
    def transitions(self) -> tuple[Transition, ...]:
        """tuple of Transition: The transitions, in the order added."""
        return tuple(self._transitions)

    @property
    def arcs(self) -> tuple[Arc, ...]:
        """tuple of Arc: The arcs, in the order they were added."""
        return tuple(self._arcs)

    def place(self, name: str) -> Place:
        """Return the place of the net with the given name.

        Parameters
        ----------
        name : str
            Name of the place.

        Returns
        -------
        Place
            The place with that name.

        Raises
        ------
        KeyError
            If the net has no place with that name.
        """
        if name not in self._place_index:
            raise KeyError(f'The net has no place named {name!r}')
        return self._place_index[name]

    def transition(self, name: str) -> Transition:
        """Return the transition of the net with the given name.

        Parameters
        ----------
        name : str
            Name of the transition.

        Returns
        -------
        Transition
            The transition with that name.

        Raises
        ------
        KeyError
            If the net has no transition with that name.
        """
        if name not in self._transition_index:
            raise KeyError(f'The net has no transition named {name!r}')
        return self._transition_index[name]

    def input_arcs(self, transition: Transition) -> tuple[Arc, ...]:
        """Return the arcs that run into a transition.

        These are the arcs the firing rule consumes tokens through, and the
        ones that decide whether the transition is enabled.

        Parameters
        ----------
        transition : Transition
            Transition to look up.

        Returns
        -------
        tuple of Arc
            The input arcs, in the order they were added.

        Raises
        ------
        ValueError
            If the transition is not in the net.
        """
        self._require_transition(transition)
        return tuple(self._input_arcs[transition])

    def output_arcs(self, transition: Transition) -> tuple[Arc, ...]:
        """Return the arcs that run out of a transition.

        These are the arcs the firing rule produces tokens through.

        Parameters
        ----------
        transition : Transition
            Transition to look up.

        Returns
        -------
        tuple of Arc
            The output arcs, in the order they were added.

        Raises
        ------
        ValueError
            If the transition is not in the net.
        """
        self._require_transition(transition)
        return tuple(self._output_arcs[transition])

    def transitions_affected_by(self, place: Place) -> tuple[Transition, ...]:
        """Return the transitions whose enabling depends on a place.

        These are the transitions the place feeds, so a change to its marking
        can change only their enabling. After a firing, re-examining just these
        transitions is enough; the rest of the net cannot have changed.

        Parameters
        ----------
        place : Place
            Place to look up.

        Returns
        -------
        tuple of Transition
            The transitions reached by an input arc from this place, in the
            order they were added to the net.

        Raises
        ------
        ValueError
            If the place is not in the net.
        """
        self._require_place(place)
        affected = self._affected[place]
        return tuple(
            transition
            for transition in self._transitions
            if transition in affected
        )

    # ------------------------------------------------------------------
    # The state of the net
    # ------------------------------------------------------------------

    @property
    def marking(self) -> tuple[int, ...]:
        """tuple of int: The marking vector, in the order places were added.

        This is the state of the net. It is a tuple rather than a mapping so
        that it can be compared and hashed, which is what lets a reachability
        graph use a marking as the identity of a node.

        Assigning a marking writes it back to the places without applying the
        firing rule, so that analysis can restore a state it has already
        visited.

        Raises
        ------
        ValueError
            If the assigned vector does not have one entry per place, or if
            any entry is negative.
        """
        return tuple(place.marking for place in self._places)

    @marking.setter
    def marking(self, value: tuple[int, ...]) -> None:
        places = tuple(self._places)
        if len(value) != len(places):
            raise ValueError(
                f'The net has {len(places)} places, but the marking has '
                f'{len(value)} entries'
            )
        for place, tokens in zip(places, value, strict=True):
            if tokens < 0:
                raise ValueError(
                    f'The marking of a place cannot be negative, got {tokens} '
                    f'for place {place.name!r}'
                )
        for place, tokens in zip(places, value, strict=True):
            place.marking = tokens

    @property
    def initial_marking(self) -> tuple[int, ...]:
        """tuple of int: The marking the net starts from.

        This is :math:`M_0`, the root of the reachability graph and the state
        :meth:`reset` returns the net to.
        """
        return tuple(place.initial_marking for place in self._places)

    def reset(self) -> None:
        """Return every place of the net to its initial marking.

        Used between simulation runs, and before an analysis that starts from
        the initial marking.
        """
        for place in self._places:
            place.reset()

    # ------------------------------------------------------------------
    # The firing rule
    # ------------------------------------------------------------------

    def is_enabled(self, transition: Transition) -> bool:
        """Test whether a transition may fire in the current marking.

        A transition is enabled when every place with an arc into it holds at
        least as many tokens as that arc's weight. A transition with no input
        arcs is enabled unconditionally: it is a source, and nothing can stop
        it from firing.

        Parameters
        ----------
        transition : Transition
            Transition to test. It must belong to this net.

        Returns
        -------
        bool
            ``True`` if the transition may fire.

        Raises
        ------
        ValueError
            If the transition is not in the net.
        """
        self._require_transition(transition)
        return all(
            arc.place.has_tokens(arc.weight)
            for arc in self._input_arcs[transition]
        )

    def enabled_transitions(self) -> tuple[Transition, ...]:
        """Return every transition that may fire in the current marking.

        The result is in the order the transitions were added to the net, so
        that a run over a net is reproducible. Under the interleaved semantics
        of this library exactly one of these may fire next; each choice leads
        to a different successor marking, and it is that branching a
        reachability graph enumerates.

        Returns
        -------
        tuple of Transition
            The enabled transitions, in the order they were added.
        """
        return tuple(
            transition
            for transition in self._transitions
            if self.is_enabled(transition)
        )

    def fire(self, transition: Transition) -> None:
        """Fire a transition, moving tokens through its arcs.

        Firing removes the weight of each input arc from the place it comes
        from, then adds the weight of each output arc to the place it goes to.
        The two happen as one step: no marking in which the tokens have been
        consumed but not yet produced is ever observable.

        Consumption is performed before production, which is what makes a self
        loop work. A transition that borrows the token of a place and gives it
        back has that place as both an input and an output; taking first and
        returning after leaves the marking unchanged, whereas the reverse order
        would briefly hold two tokens in a place meant to hold one.

        Parameters
        ----------
        transition : Transition
            Transition to fire. It must belong to this net and be enabled.

        Raises
        ------
        ValueError
            If the transition is not in the net, or is not enabled in the
            current marking.

        See Also
        --------
        is_enabled : The test a transition must pass before it can be fired.
        """
        if not self.is_enabled(transition):
            raise ValueError(
                f'Transition {transition.name!r} is not enabled and cannot '
                'fire'
            )
        for arc in self._input_arcs[transition]:
            arc.place.remove_tokens(arc.weight)
        for arc in self._output_arcs[transition]:
            arc.place.add_tokens(arc.weight)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _require_place(self, place: Place) -> None:
        """Raise if a place does not belong to this net.

        Parameters
        ----------
        place : Place
            Place to check.

        Raises
        ------
        ValueError
            If the place is not in the net.
        """
        if place not in self._affected:
            raise ValueError(f'Place {place.name!r} is not in the net')

    def _require_transition(self, transition: Transition) -> None:
        """Raise if a transition does not belong to this net.

        Parameters
        ----------
        transition : Transition
            Transition to check.

        Raises
        ------
        ValueError
            If the transition is not in the net.
        """
        if transition not in self._input_arcs:
            raise ValueError(
                f'Transition {transition.name!r} is not in the net'
            )

    def __str__(self) -> str:
        """Return the size of the net.

        Returns
        -------
        str
            The number of places, transitions and arcs.
        """
        return (
            f'PetriNet with {len(self._places)} places, '
            f'{len(self._transitions)} transitions and '
            f'{len(self._arcs)} arcs'
        )

    def __repr__(self) -> str:
        """Return a representation showing the size and state of the net.

        Returns
        -------
        str
            The size of the net and its current marking. This is a debugging
            aid, not an expression that reconstructs the net.
        """
        return (
            f'PetriNet(places={len(self._places)}, '
            f'transitions={len(self._transitions)}, '
            f'arcs={len(self._arcs)}, marking={self.marking})'
        )
