"""Tests for :class:`masafi_sim_petri.petri_net.transition.Transition`."""

import pytest

from masafi_sim_petri.petri_net import Transition


class TestConstruction:
    """Construction and validation of a transition."""

    def test_is_created_with_a_name(self) -> None:
        """A transition is identified by the name given to it."""
        transition = Transition('serve_customer')

        assert transition.name == 'serve_customer'

    @pytest.mark.parametrize('name', ['', ' ', '\t\n'])
    def test_blank_name_is_rejected(self, name: str) -> None:
        """A transition must be named, because the net identifies it by name.

        Parameters
        ----------
        name : str
            A name made only of whitespace, or no name at all.
        """
        with pytest.raises(ValueError, match='cannot be empty'):
            Transition(name)


class TestReadOnlyProperties:
    """The identity of a transition does not change after construction."""

    def test_name_is_read_only(self) -> None:
        """The name is fixed, so the net index cannot go stale."""
        transition = Transition('t1')

        with pytest.raises(AttributeError):
            transition.name = 't2'  # type: ignore[misc]


class TestNoState:
    """A P/T transition carries no state of its own."""

    def test_carries_no_marking_or_connectivity(self) -> None:
        """The marking lives in the places and the arcs live in the net.

        This test states the design decision rather than an implementation
        detail: if a transition ever grows its own token store or a list of
        arcs, that is a change of architecture and should be a deliberate one.
        """
        transition = Transition('t1')

        for attribute in ['marking', 'input_arcs', 'output_arcs', 'net']:
            assert not hasattr(transition, attribute), attribute


class TestRepresentation:
    """Textual forms used in messages and in debugging output."""

    def test_str_is_the_name(self) -> None:
        """A transition reads as its name when interpolated into a message."""
        assert str(Transition('t1')) == 't1'

    def test_repr_shows_the_state(self) -> None:
        """The representation shows the state a failing test needs."""
        assert repr(Transition('t1')) == "Transition(name='t1')"
