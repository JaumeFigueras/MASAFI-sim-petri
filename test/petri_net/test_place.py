"""Tests for :class:`masafi_sim_petri.petri_net.place.Place`."""

import pytest

from masafi_sim_petri.petri_net import Place


class TestConstruction:
    """Construction and validation of the initial state of a place."""

    def test_default_initial_marking_is_zero(self) -> None:
        """A place with no initial marking starts empty."""
        place = Place('p1')

        assert place.name == 'p1'
        assert place.initial_marking == 0
        assert place.marking == 0

    def test_initial_marking_is_the_starting_marking(self) -> None:
        """The current marking starts at the initial marking."""
        place = Place('p1', initial_marking=3)

        assert place.initial_marking == 3
        assert place.marking == 3

    @pytest.mark.parametrize('name', ['', ' ', '\t\n'])
    def test_blank_name_is_rejected(self, name: str) -> None:
        """A place must be named, because the net identifies it by name.

        Parameters
        ----------
        name : str
            A name made only of whitespace, or no name at all.
        """
        with pytest.raises(ValueError, match='cannot be empty'):
            Place(name)

    def test_negative_initial_marking_is_rejected(self) -> None:
        """A marking counts tokens, so it cannot start below zero."""
        with pytest.raises(ValueError, match='cannot be negative'):
            Place('p1', initial_marking=-1)


class TestReadOnlyProperties:
    """The identity of a place does not change after construction."""

    def test_name_is_read_only(self) -> None:
        """The name is fixed, so the net index cannot go stale."""
        place = Place('p1')

        with pytest.raises(AttributeError):
            place.name = 'p2'  # type: ignore[misc]

    def test_initial_marking_is_read_only(self) -> None:
        """The initial marking is fixed, so :meth:`reset` stays meaningful."""
        place = Place('p1', initial_marking=2)

        with pytest.raises(AttributeError):
            place.initial_marking = 5  # type: ignore[misc]


class TestMarkingAssignment:
    """Direct assignment of a marking, used to restore an explored state."""

    def test_marking_can_be_assigned(self) -> None:
        """Assigning a marking replaces it without applying a firing rule."""
        place = Place('p1', initial_marking=1)

        place.marking = 7

        assert place.marking == 7

    def test_marking_can_be_assigned_zero(self) -> None:
        """Emptying a place is a legitimate state."""
        place = Place('p1', initial_marking=4)

        place.marking = 0

        assert place.marking == 0

    def test_negative_marking_is_rejected(self) -> None:
        """The non-negative invariant survives direct assignment."""
        place = Place('p1', initial_marking=4)

        with pytest.raises(ValueError, match='cannot be negative'):
            place.marking = -1

        assert place.marking == 4


class TestHasTokens:
    """The enabling test asked of an input place before it is drained."""

    @pytest.mark.parametrize(
        ('marking', 'count', 'expected'),
        [
            (0, 0, True),
            (0, 1, False),
            (2, 1, True),
            (2, 2, True),
            (2, 3, False),
        ],
    )
    def test_boundaries(
        self, marking: int, count: int, expected: bool
    ) -> None:
        """A place has `count` tokens when its marking reaches `count`.

        Parameters
        ----------
        marking : int
            Marking of the place under test.
        count : int
            Number of tokens asked for.
        expected : bool
            Expected answer, exercising both sides of the boundary.
        """
        place = Place('p1', initial_marking=marking)

        assert place.has_tokens(count) is expected

    def test_default_count_is_one(self) -> None:
        """Asking without a count asks for a single token."""
        assert Place('p1', initial_marking=1).has_tokens() is True
        assert Place('p1').has_tokens() is False

    def test_negative_count_is_rejected(self) -> None:
        """Asking for a negative number of tokens is meaningless."""
        with pytest.raises(ValueError, match='negative'):
            Place('p1').has_tokens(-1)

    def test_does_not_change_the_marking(self) -> None:
        """The enabling test is a query, not a command."""
        place = Place('p1', initial_marking=2)

        place.has_tokens(2)

        assert place.marking == 2


class TestAddTokens:
    """Production of tokens into an output place."""

    def test_adds_the_given_count(self) -> None:
        """The marking grows by the number of tokens added."""
        place = Place('p1', initial_marking=1)

        place.add_tokens(3)

        assert place.marking == 4

    def test_default_count_is_one(self) -> None:
        """Adding without a count adds a single token."""
        place = Place('p1')

        place.add_tokens()

        assert place.marking == 1

    def test_adding_zero_leaves_the_marking_unchanged(self) -> None:
        """A zero-weight production is a no-op rather than an error."""
        place = Place('p1', initial_marking=2)

        place.add_tokens(0)

        assert place.marking == 2

    def test_negative_count_is_rejected(self) -> None:
        """Adding a negative count would be a disguised removal."""
        place = Place('p1', initial_marking=2)

        with pytest.raises(ValueError, match='negative'):
            place.add_tokens(-1)

        assert place.marking == 2

    def test_is_unbounded(self) -> None:
        """No capacity limits a place, so a large marking is accepted."""
        place = Place('p1')

        place.add_tokens(1_000_000)

        assert place.marking == 1_000_000


class TestRemoveTokens:
    """Consumption of tokens from an input place."""

    def test_removes_the_given_count(self) -> None:
        """The marking shrinks by the number of tokens removed."""
        place = Place('p1', initial_marking=5)

        place.remove_tokens(2)

        assert place.marking == 3

    def test_default_count_is_one(self) -> None:
        """Removing without a count removes a single token."""
        place = Place('p1', initial_marking=2)

        place.remove_tokens()

        assert place.marking == 1

    def test_can_empty_the_place(self) -> None:
        """Removing exactly the marking is allowed and empties the place."""
        place = Place('p1', initial_marking=3)

        place.remove_tokens(3)

        assert place.marking == 0

    def test_removing_zero_leaves_the_marking_unchanged(self) -> None:
        """A zero-weight consumption is a no-op rather than an error."""
        place = Place('p1', initial_marking=2)

        place.remove_tokens(0)

        assert place.marking == 2

    def test_negative_count_is_rejected(self) -> None:
        """Removing a negative count would be a disguised production."""
        place = Place('p1', initial_marking=2)

        with pytest.raises(ValueError, match='negative'):
            place.remove_tokens(-1)

        assert place.marking == 2

    def test_removing_more_than_held_is_rejected(self) -> None:
        """Over-removal signals a firing rule that skipped its enabling test."""
        place = Place('p1', initial_marking=2)

        with pytest.raises(ValueError, match='Cannot remove 3 tokens'):
            place.remove_tokens(3)

    def test_marking_is_unchanged_after_a_rejected_removal(self) -> None:
        """A rejected removal leaves the place exactly as it was."""
        place = Place('p1', initial_marking=2)

        with pytest.raises(ValueError):
            place.remove_tokens(3)

        assert place.marking == 2


class TestReset:
    """Return to the initial marking, used between runs and before analysis."""

    def test_restores_the_initial_marking_after_removal(self) -> None:
        """A drained place is refilled to its initial marking."""
        place = Place('p1', initial_marking=2)
        place.remove_tokens(2)

        place.reset()

        assert place.marking == 2

    def test_restores_the_initial_marking_after_assignment(self) -> None:
        """A marking restored by analysis is still undone by a reset."""
        place = Place('p1', initial_marking=2)
        place.marking = 9

        place.reset()

        assert place.marking == 2

    def test_is_idempotent(self) -> None:
        """Resetting an untouched place changes nothing."""
        place = Place('p1', initial_marking=2)

        place.reset()
        place.reset()

        assert place.marking == 2


class TestRepresentation:
    """Textual forms used in messages and in debugging output."""

    def test_str_is_the_name(self) -> None:
        """A place reads as its name when interpolated into a message."""
        assert str(Place('p1', initial_marking=2)) == 'p1'

    def test_repr_shows_the_full_state(self) -> None:
        """The representation shows the state a failing test needs."""
        place = Place('p1', initial_marking=2)
        place.add_tokens()

        assert repr(place) == (
            "Place(name='p1', initial_marking=2, marking=3)"
        )
