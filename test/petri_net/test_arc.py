"""Tests for :class:`masafi_sim_petri.petri_net.arc.Arc`."""

import pytest

from masafi_sim_petri.petri_net import Arc, Place, Transition


@pytest.fixture
def place() -> Place:
    """Return a place to attach arcs to.

    Returns
    -------
    Place
        A place named ``p1``, empty.
    """
    return Place('p1')


@pytest.fixture
def transition() -> Transition:
    """Return a transition to attach arcs to.

    Returns
    -------
    Transition
        A transition named ``t1``.
    """
    return Transition('t1')


class TestConstruction:
    """Construction of an arc and the endpoints it accepts."""

    def test_from_place_to_transition(
        self, place: Place, transition: Transition
    ) -> None:
        """An arc may run from a place to a transition."""
        arc = Arc(place, transition)

        assert arc.source is place
        assert arc.target is transition

    def test_from_transition_to_place(
        self, place: Place, transition: Transition
    ) -> None:
        """An arc may run from a transition to a place."""
        arc = Arc(transition, place)

        assert arc.source is transition
        assert arc.target is place

    def test_two_places_are_rejected(self) -> None:
        """A Petri net is bipartite, so a place cannot reach a place."""
        with pytest.raises(ValueError, match='must join a place and a transition'):
            Arc(Place('p1'), Place('p2'))

    def test_two_transitions_are_rejected(self) -> None:
        """A Petri net is bipartite, so a transition cannot reach one."""
        with pytest.raises(ValueError, match='must join a place and a transition'):
            Arc(Transition('t1'), Transition('t2'))

    def test_the_rejection_names_the_offending_types(self) -> None:
        """The message says what was passed, to make the mistake obvious."""
        with pytest.raises(ValueError, match='got Place and Place'):
            Arc(Place('p1'), Place('p2'))


class TestWeight:
    """The number of tokens an arc moves."""

    def test_default_weight_is_one(
        self, place: Place, transition: Transition
    ) -> None:
        """An arc moves a single token unless told otherwise."""
        assert Arc(place, transition).weight == 1

    def test_weight_is_kept(
        self, place: Place, transition: Transition
    ) -> None:
        """A weight given at construction is the weight of the arc."""
        assert Arc(place, transition, weight=6).weight == 6

    @pytest.mark.parametrize('weight', [0, -1])
    def test_weight_below_one_is_rejected(
        self, place: Place, transition: Transition, weight: int
    ) -> None:
        """A weight of zero is not an arc, and a negative weight is nothing.

        Parameters
        ----------
        place : Place
            Endpoint of the arc under test.
        transition : Transition
            Endpoint of the arc under test.
        weight : int
            An invalid weight, at and below the boundary.
        """
        with pytest.raises(ValueError, match='at least 1'):
            Arc(place, transition, weight=weight)

    def test_weight_is_read_only(
        self, place: Place, transition: Transition
    ) -> None:
        """The weight is part of the structure of the net, fixed on creation."""
        arc = Arc(place, transition)

        with pytest.raises(AttributeError):
            arc.weight = 2  # type: ignore[misc]


class TestEndpointAccess:
    """Reaching the endpoints without caring which way the arc runs."""

    def test_place_and_transition_of_an_input_arc(
        self, place: Place, transition: Transition
    ) -> None:
        """The endpoints are reachable by kind, not only by direction."""
        arc = Arc(place, transition)

        assert arc.place is place
        assert arc.transition is transition

    def test_place_and_transition_of_an_output_arc(
        self, place: Place, transition: Transition
    ) -> None:
        """The same accessors work when the arc runs the other way."""
        arc = Arc(transition, place)

        assert arc.place is place
        assert arc.transition is transition

    @pytest.mark.parametrize('attribute', ['source', 'target', 'place', 'transition'])
    def test_endpoints_are_read_only(
        self, place: Place, transition: Transition, attribute: str
    ) -> None:
        """Endpoints are fixed: rewiring is a change of net structure.

        Parameters
        ----------
        place : Place
            Endpoint of the arc under test.
        transition : Transition
            Endpoint of the arc under test.
        attribute : str
            Name of the endpoint accessor that must not be assignable.
        """
        arc = Arc(place, transition)

        with pytest.raises(AttributeError):
            setattr(arc, attribute, place)


class TestDirection:
    """Which way the arc runs, expressed from the transition's point of view."""

    def test_place_to_transition_is_an_input_arc(
        self, place: Place, transition: Transition
    ) -> None:
        """Firing removes tokens through an arc that arrives at a transition."""
        arc = Arc(place, transition)

        assert arc.is_input is True
        assert arc.is_output is False

    def test_transition_to_place_is_an_output_arc(
        self, place: Place, transition: Transition
    ) -> None:
        """Firing adds tokens through an arc that leaves a transition."""
        arc = Arc(transition, place)

        assert arc.is_input is False
        assert arc.is_output is True

    def test_a_self_loop_is_two_distinct_arcs(
        self, place: Place, transition: Transition
    ) -> None:
        """A transition that reads and returns a token needs both directions.

        This is the mutual exclusion pattern: the same place is both input and
        output of the transition, which is two arcs and not one bidirectional
        one.
        """
        taken = Arc(place, transition)
        returned = Arc(transition, place)

        assert taken.is_input is True
        assert returned.is_output is True
        assert taken is not returned


class TestRepresentation:
    """Textual forms used in messages and in debugging output."""

    def test_str_reads_as_a_labelled_edge(
        self, place: Place, transition: Transition
    ) -> None:
        """An arc reads as an edge, so a net reads as a list of edges."""
        assert str(Arc(place, transition, weight=3)) == 'p1 --3--> t1'

    def test_str_follows_the_direction_of_the_arc(
        self, place: Place, transition: Transition
    ) -> None:
        """The arrow points the way the tokens move."""
        assert str(Arc(transition, place)) == 't1 --1--> p1'

    def test_repr_shows_the_full_state(
        self, place: Place, transition: Transition
    ) -> None:
        """The representation shows the state a failing test needs."""
        assert repr(Arc(place, transition, weight=2)) == (
            "Arc(source=Place(name='p1', initial_marking=0, marking=0), "
            "target=Transition(name='t1'), weight=2)"
        )
