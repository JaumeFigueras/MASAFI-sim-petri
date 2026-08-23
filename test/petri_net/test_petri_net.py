"""Tests for :class:`masafi_sim_petri.petri_net.petri_net.PetriNet`.

These cover the structure of a net -- what it accepts, what it rejects, how it
indexes the connectivity and how it reports its marking -- and the firing rule
that moves tokens through it.
"""

import pytest

from masafi_sim_petri.petri_net import Arc, PetriNet, Place, Transition


@pytest.fixture
def net() -> PetriNet:
    """Return an empty net.

    Returns
    -------
    PetriNet
        A net with no places, transitions or arcs.
    """
    return PetriNet()


@pytest.fixture
def server_net() -> PetriNet:
    """Return a small net: a queue served by a single server.

    The net is ``waiting -> serve -> served``, with a ``server`` place that
    ``serve`` takes a token from and gives back, which is the mutual exclusion
    pattern.

    Returns
    -------
    PetriNet
        A net with three places, one transition and four arcs.
    """
    net = PetriNet()
    waiting = net.add_place(Place('waiting', initial_marking=2))
    server = net.add_place(Place('server', initial_marking=1))
    served = net.add_place(Place('served'))
    serve = net.add_transition(Transition('serve'))
    net.add_arc(Arc(waiting, serve))
    net.add_arc(Arc(server, serve))
    net.add_arc(Arc(serve, served))
    net.add_arc(Arc(serve, server))
    return net


class TestEmptyNet:
    """A net that has just been created."""

    def test_has_no_nodes(self, net: PetriNet) -> None:
        """A new net is empty."""
        assert net.places == ()
        assert net.transitions == ()
        assert net.arcs == ()

    def test_has_an_empty_marking(self, net: PetriNet) -> None:
        """The marking vector of a net with no places has no entries."""
        assert net.marking == ()


class TestAddPlace:
    """Adding places, and the names they may take."""

    def test_returns_the_place(self, net: PetriNet) -> None:
        """The place is returned so it can be bound and wired in one step."""
        place = Place('p1')

        assert net.add_place(place) is place

    def test_places_keep_the_order_they_were_added(
        self, net: PetriNet
    ) -> None:
        """Order is stable, so the marking vector means the same thing twice."""
        first = net.add_place(Place('p1'))
        second = net.add_place(Place('p2'))

        assert net.places == (first, second)

    def test_the_same_place_cannot_be_added_twice(
        self, net: PetriNet
    ) -> None:
        """Adding a place twice would duplicate it in the marking vector."""
        place = net.add_place(Place('p1'))

        with pytest.raises(ValueError, match='already in the net'):
            net.add_place(place)

    def test_two_places_cannot_share_a_name(self, net: PetriNet) -> None:
        """Names identify a place within a net, so they must be unique."""
        net.add_place(Place('p1'))

        with pytest.raises(ValueError, match='already has a place named'):
            net.add_place(Place('p1'))

    def test_a_place_may_share_a_name_with_a_transition(
        self, net: PetriNet
    ) -> None:
        """Places and transitions are separate sets, indexed separately."""
        net.add_place(Place('n'))
        net.add_transition(Transition('n'))

        assert net.place('n').name == 'n'
        assert net.transition('n').name == 'n'


class TestAddTransition:
    """Adding transitions, and the names they may take."""

    def test_returns_the_transition(self, net: PetriNet) -> None:
        """The transition is returned so it can be bound and wired at once."""
        transition = Transition('t1')

        assert net.add_transition(transition) is transition

    def test_transitions_keep_the_order_they_were_added(
        self, net: PetriNet
    ) -> None:
        """Order is stable, so a run over the net is reproducible."""
        first = net.add_transition(Transition('t1'))
        second = net.add_transition(Transition('t2'))

        assert net.transitions == (first, second)

    def test_the_same_transition_cannot_be_added_twice(
        self, net: PetriNet
    ) -> None:
        """Adding a transition twice would duplicate its arc lists."""
        transition = net.add_transition(Transition('t1'))

        with pytest.raises(ValueError, match='already in the net'):
            net.add_transition(transition)

    def test_two_transitions_cannot_share_a_name(
        self, net: PetriNet
    ) -> None:
        """Names identify a transition within a net, so they must be unique."""
        net.add_transition(Transition('t1'))

        with pytest.raises(ValueError, match='already has a transition named'):
            net.add_transition(Transition('t1'))


class TestAddArc:
    """Adding arcs, and the connectivity rules a net imposes on them."""

    def test_returns_the_arc(self, net: PetriNet) -> None:
        """The arc is returned, for symmetry with the other add methods."""
        place = net.add_place(Place('p1'))
        transition = net.add_transition(Transition('t1'))
        arc = Arc(place, transition)

        assert net.add_arc(arc) is arc

    def test_arcs_keep_the_order_they_were_added(self, net: PetriNet) -> None:
        """Order is stable, so a net reads the same way twice."""
        place = net.add_place(Place('p1'))
        transition = net.add_transition(Transition('t1'))
        first = net.add_arc(Arc(place, transition))
        second = net.add_arc(Arc(transition, place))

        assert net.arcs == (first, second)

    def test_a_foreign_place_is_rejected(self, net: PetriNet) -> None:
        """An arc to a place of another net would join two nets together."""
        transition = net.add_transition(Transition('t1'))

        with pytest.raises(ValueError, match="Place 'outsider' is not in the net"):
            net.add_arc(Arc(Place('outsider'), transition))

    def test_a_foreign_transition_is_rejected(self, net: PetriNet) -> None:
        """The same rule holds for the transition endpoint."""
        place = net.add_place(Place('p1'))

        with pytest.raises(
            ValueError, match="Transition 'outsider' is not in the net"
        ):
            net.add_arc(Arc(place, Transition('outsider')))

    def test_a_duplicate_input_arc_is_rejected(self, net: PetriNet) -> None:
        """Two arcs the same way round would be one arc of the summed weight."""
        place = net.add_place(Place('p1'))
        transition = net.add_transition(Transition('t1'))
        net.add_arc(Arc(place, transition))

        with pytest.raises(ValueError, match='already joins place'):
            net.add_arc(Arc(place, transition, weight=2))

    def test_a_duplicate_output_arc_is_rejected(self, net: PetriNet) -> None:
        """The rule applies in the other direction too."""
        place = net.add_place(Place('p1'))
        transition = net.add_transition(Transition('t1'))
        net.add_arc(Arc(transition, place))

        with pytest.raises(ValueError, match='already joins place'):
            net.add_arc(Arc(transition, place))

    def test_opposite_directions_are_not_duplicates(
        self, net: PetriNet
    ) -> None:
        """A self-loop is two arcs between the same pair, and is legitimate."""
        place = net.add_place(Place('p1'))
        transition = net.add_transition(Transition('t1'))

        net.add_arc(Arc(place, transition))
        net.add_arc(Arc(transition, place))

        assert len(net.arcs) == 2


class TestLookupByName:
    """Finding a node by the name it was given."""

    def test_finds_a_place(self, server_net: PetriNet) -> None:
        """A place is reachable by name."""
        assert server_net.place('waiting').name == 'waiting'

    def test_finds_a_transition(self, server_net: PetriNet) -> None:
        """A transition is reachable by name."""
        assert server_net.transition('serve').name == 'serve'

    def test_an_unknown_place_raises(self, server_net: PetriNet) -> None:
        """Asking for a place that is not there is a lookup failure."""
        with pytest.raises(KeyError, match='no place named'):
            server_net.place('nowhere')

    def test_an_unknown_transition_raises(self, server_net: PetriNet) -> None:
        """Asking for a transition that is not there is a lookup failure."""
        with pytest.raises(KeyError, match='no transition named'):
            server_net.transition('nowhere')


class TestConnectivity:
    """The indexes the net keeps over its arcs."""

    def test_input_arcs_are_those_reaching_the_transition(
        self, server_net: PetriNet
    ) -> None:
        """Input arcs come from the places the transition consumes from."""
        serve = server_net.transition('serve')

        sources = [arc.place.name for arc in server_net.input_arcs(serve)]

        assert sources == ['waiting', 'server']

    def test_output_arcs_are_those_leaving_the_transition(
        self, server_net: PetriNet
    ) -> None:
        """Output arcs go to the places the transition produces into."""
        serve = server_net.transition('serve')

        targets = [arc.place.name for arc in server_net.output_arcs(serve)]

        assert targets == ['served', 'server']

    def test_a_transition_with_no_arcs_has_empty_lists(
        self, net: PetriNet
    ) -> None:
        """An unconnected transition is legal, and has no arcs either way."""
        transition = net.add_transition(Transition('t1'))

        assert net.input_arcs(transition) == ()
        assert net.output_arcs(transition) == ()

    def test_input_arcs_of_a_foreign_transition_are_rejected(
        self, net: PetriNet
    ) -> None:
        """The net answers only about the transitions it holds."""
        with pytest.raises(ValueError, match='is not in the net'):
            net.input_arcs(Transition('outsider'))

    def test_output_arcs_of_a_foreign_transition_are_rejected(
        self, net: PetriNet
    ) -> None:
        """The net answers only about the transitions it holds."""
        with pytest.raises(ValueError, match='is not in the net'):
            net.output_arcs(Transition('outsider'))


class TestTransitionsAffectedBy:
    """The index that says which transitions a marking change can affect."""

    def test_lists_the_transitions_the_place_feeds(
        self, server_net: PetriNet
    ) -> None:
        """A place feeds the transitions its input arcs reach."""
        waiting = server_net.place('waiting')

        assert server_net.transitions_affected_by(waiting) == (
            server_net.transition('serve'),
        )

    def test_an_output_only_place_affects_nothing(
        self, server_net: PetriNet
    ) -> None:
        """A place that is only produced into enables no transition."""
        served = server_net.place('served')

        assert server_net.transitions_affected_by(served) == ()

    def test_a_place_of_a_self_loop_is_still_affected(
        self, server_net: PetriNet
    ) -> None:
        """A place both consumed and produced still gates its transition."""
        server = server_net.place('server')

        assert server_net.transitions_affected_by(server) == (
            server_net.transition('serve'),
        )

    def test_lists_every_transition_the_place_feeds(
        self, net: PetriNet
    ) -> None:
        """A place shared by several transitions affects all of them."""
        place = net.add_place(Place('shared'))
        first = net.add_transition(Transition('t1'))
        second = net.add_transition(Transition('t2'))
        net.add_arc(Arc(place, first))
        net.add_arc(Arc(place, second))

        assert net.transitions_affected_by(place) == (first, second)

    def test_a_foreign_place_is_rejected(self, net: PetriNet) -> None:
        """The net answers only about the places it holds."""
        with pytest.raises(ValueError, match='is not in the net'):
            net.transitions_affected_by(Place('outsider'))


class TestMarking:
    """The marking vector: the state of the net."""

    def test_follows_the_order_the_places_were_added(
        self, server_net: PetriNet
    ) -> None:
        """The vector is positional, in the net's own place order."""
        assert server_net.marking == (2, 1, 0)

    def test_is_hashable(self, server_net: PetriNet) -> None:
        """A marking identifies a node of the reachability graph."""
        assert {server_net.marking: 'root'}[(2, 1, 0)] == 'root'

    def test_reflects_a_change_to_a_place(
        self, server_net: PetriNet
    ) -> None:
        """The vector is read from the places, not cached alongside them."""
        server_net.place('waiting').remove_tokens(1)

        assert server_net.marking == (1, 1, 0)

    def test_can_be_assigned(self, server_net: PetriNet) -> None:
        """Analysis restores a visited state by assigning the whole vector."""
        server_net.marking = (0, 1, 2)

        assert server_net.marking == (0, 1, 2)
        assert server_net.place('served').marking == 2

    def test_a_vector_of_the_wrong_length_is_rejected(
        self, server_net: PetriNet
    ) -> None:
        """A vector with the wrong arity is not a marking of this net."""
        with pytest.raises(ValueError, match='3 places, but the marking has 2'):
            server_net.marking = (0, 1)

    def test_a_negative_entry_is_rejected(
        self, server_net: PetriNet
    ) -> None:
        """A marking counts tokens, so no entry may be negative."""
        with pytest.raises(ValueError, match='cannot be negative'):
            server_net.marking = (0, -1, 0)

    def test_a_rejected_assignment_changes_nothing(
        self, server_net: PetriNet
    ) -> None:
        """The whole vector is validated before any place is written to."""
        with pytest.raises(ValueError):
            server_net.marking = (5, -1, 0)

        assert server_net.marking == (2, 1, 0)


class TestInitialMarking:
    """The marking the net starts from."""

    def test_is_read_from_the_places(self, server_net: PetriNet) -> None:
        """M0 is the vector of the places' initial markings."""
        assert server_net.initial_marking == (2, 1, 0)

    def test_does_not_follow_the_current_marking(
        self, server_net: PetriNet
    ) -> None:
        """M0 is fixed, whatever the net does afterwards."""
        server_net.marking = (0, 0, 3)

        assert server_net.initial_marking == (2, 1, 0)

    def test_is_read_only(self, server_net: PetriNet) -> None:
        """M0 is decided by the places, not assigned on the net."""
        with pytest.raises(AttributeError):
            server_net.initial_marking = (0, 0, 0)  # type: ignore[misc]


class TestReset:
    """Returning the net to its initial marking."""

    def test_restores_every_place(self, server_net: PetriNet) -> None:
        """A reset net is back at M0, whatever state it was in."""
        server_net.marking = (0, 0, 3)

        server_net.reset()

        assert server_net.marking == server_net.initial_marking

    def test_is_idempotent(self, server_net: PetriNet) -> None:
        """Resetting an untouched net changes nothing."""
        server_net.reset()
        server_net.reset()

        assert server_net.marking == (2, 1, 0)


class TestRepresentation:
    """Textual forms used in messages and in debugging output."""

    def test_str_reports_the_size(self, server_net: PetriNet) -> None:
        """A net reads as its size, which is what identifies it at a glance."""
        assert str(server_net) == (
            'PetriNet with 3 places, 1 transitions and 4 arcs'
        )

    def test_repr_reports_the_size_and_the_marking(
        self, server_net: PetriNet
    ) -> None:
        """The representation shows the state a failing test needs."""
        assert repr(server_net) == (
            'PetriNet(places=3, transitions=1, arcs=4, marking=(2, 1, 0))'
        )


class TestIsEnabled:
    """The condition a transition must meet before it can fire."""

    def test_a_transition_with_enough_tokens_is_enabled(
        self, server_net: PetriNet
    ) -> None:
        """Every input place can supply the weight of its arc."""
        assert server_net.is_enabled(server_net.transition('serve')) is True

    def test_a_transition_missing_one_input_is_not_enabled(
        self, server_net: PetriNet
    ) -> None:
        """One empty input place is enough to disable a transition."""
        server_net.place('waiting').marking = 0

        assert server_net.is_enabled(server_net.transition('serve')) is False

    def test_every_input_place_must_supply_its_own_arc(
        self, server_net: PetriNet
    ) -> None:
        """Tokens in one input place do not make up for another being empty."""
        server_net.marking = (5, 0, 0)

        assert server_net.is_enabled(server_net.transition('serve')) is False

    def test_the_weight_of_the_arc_is_what_is_required(
        self, net: PetriNet
    ) -> None:
        """A weighted arc needs its full weight, not merely one token."""
        items = net.add_place(Place('items', initial_marking=5))
        pack = net.add_transition(Transition('pack'))
        net.add_arc(Arc(items, pack, weight=6))

        assert net.is_enabled(pack) is False

        items.add_tokens(1)

        assert net.is_enabled(pack) is True

    def test_a_transition_with_no_input_arcs_is_always_enabled(
        self, net: PetriNet
    ) -> None:
        """A source transition has no condition to meet."""
        source = net.add_transition(Transition('source'))
        place = net.add_place(Place('p1'))
        net.add_arc(Arc(source, place))

        assert net.is_enabled(source) is True

    def test_does_not_change_the_marking(self, server_net: PetriNet) -> None:
        """The enabling test is a query, not a command."""
        server_net.is_enabled(server_net.transition('serve'))

        assert server_net.marking == (2, 1, 0)

    def test_a_foreign_transition_is_rejected(self, net: PetriNet) -> None:
        """The net answers only about the transitions it holds."""
        with pytest.raises(ValueError, match='is not in the net'):
            net.is_enabled(Transition('outsider'))


class TestEnabledTransitions:
    """Listing the transitions that could fire next."""

    def test_lists_only_the_enabled_ones(self, net: PetriNet) -> None:
        """A transition whose input place is empty is left out."""
        ready = net.add_place(Place('ready', initial_marking=1))
        empty = net.add_place(Place('empty'))
        can_fire = net.add_transition(Transition('can_fire'))
        cannot_fire = net.add_transition(Transition('cannot_fire'))
        net.add_arc(Arc(ready, can_fire))
        net.add_arc(Arc(empty, cannot_fire))

        assert net.enabled_transitions() == (can_fire,)

    def test_follows_the_order_transitions_were_added(
        self, net: PetriNet
    ) -> None:
        """Order is stable, so exploring a net is reproducible."""
        place = net.add_place(Place('p1', initial_marking=1))
        first = net.add_transition(Transition('t1'))
        second = net.add_transition(Transition('t2'))
        net.add_arc(Arc(place, first))
        net.add_arc(Arc(place, second))

        assert net.enabled_transitions() == (first, second)

    def test_a_conflict_lists_both_transitions(self, net: PetriNet) -> None:
        """Two transitions sharing one token are both enabled, for now.

        This is a conflict: either may fire, and firing one disables the
        other. Listing both is what lets a reachability graph branch.
        """
        token = net.add_place(Place('token', initial_marking=1))
        left = net.add_transition(Transition('left'))
        right = net.add_transition(Transition('right'))
        net.add_arc(Arc(token, left))
        net.add_arc(Arc(token, right))

        assert net.enabled_transitions() == (left, right)

    def test_is_empty_when_the_net_is_dead(self, server_net: PetriNet) -> None:
        """A marking in which nothing is enabled is a deadlock."""
        server_net.marking = (0, 0, 0)

        assert server_net.enabled_transitions() == ()

    def test_is_empty_for_a_net_with_no_transitions(
        self, net: PetriNet
    ) -> None:
        """A net with nothing to fire has nothing enabled."""
        assert net.enabled_transitions() == ()


class TestFire:
    """Moving tokens through the arcs of a transition."""

    def test_consumes_inputs_and_produces_outputs(
        self, server_net: PetriNet
    ) -> None:
        """One customer moves from waiting to served."""
        server_net.fire(server_net.transition('serve'))

        assert server_net.marking == (1, 1, 1)

    def test_a_self_loop_leaves_its_place_unchanged(
        self, server_net: PetriNet
    ) -> None:
        """A borrowed token is taken and given back, for a net effect of zero."""
        server_net.fire(server_net.transition('serve'))

        assert server_net.place('server').marking == 1

    def test_respects_arc_weights(self, net: PetriNet) -> None:
        """Six items become one box: the weights decide how many move."""
        items = net.add_place(Place('items', initial_marking=13))
        boxes = net.add_place(Place('boxes'))
        pack = net.add_transition(Transition('pack'))
        net.add_arc(Arc(items, pack, weight=6))
        net.add_arc(Arc(pack, boxes))

        net.fire(pack)

        assert net.marking == (7, 1)

    def test_tokens_are_not_conserved(self, net: PetriNet) -> None:
        """One token in, two out: this is how a net expresses a fork."""
        before = net.add_place(Place('before', initial_marking=1))
        left = net.add_place(Place('left'))
        right = net.add_place(Place('right'))
        fork = net.add_transition(Transition('fork'))
        net.add_arc(Arc(before, fork))
        net.add_arc(Arc(fork, left))
        net.add_arc(Arc(fork, right))

        net.fire(fork)

        assert net.marking == (0, 1, 1)

    def test_a_source_transition_creates_tokens(self, net: PetriNet) -> None:
        """A transition with no inputs may always fire, and always produces."""
        place = net.add_place(Place('p1'))
        source = net.add_transition(Transition('source'))
        net.add_arc(Arc(source, place))

        net.fire(source)
        net.fire(source)

        assert net.marking == (2,)

    def test_firing_a_disabled_transition_is_rejected(
        self, server_net: PetriNet
    ) -> None:
        """Firing without checking is a bug, so it raises rather than passes."""
        server_net.marking = (0, 1, 0)

        with pytest.raises(ValueError, match="'serve' is not enabled"):
            server_net.fire(server_net.transition('serve'))

    def test_a_rejected_firing_changes_nothing(
        self, server_net: PetriNet
    ) -> None:
        """The enabling test happens before any token is moved."""
        server_net.marking = (0, 1, 0)

        with pytest.raises(ValueError):
            server_net.fire(server_net.transition('serve'))

        assert server_net.marking == (0, 1, 0)

    def test_a_foreign_transition_is_rejected(self, net: PetriNet) -> None:
        """The net fires only the transitions it holds."""
        with pytest.raises(ValueError, match='is not in the net'):
            net.fire(Transition('outsider'))

    def test_firing_disables_the_competing_transition(
        self, net: PetriNet
    ) -> None:
        """In a conflict, whichever fires first takes the token."""
        token = net.add_place(Place('token', initial_marking=1))
        left = net.add_transition(Transition('left'))
        right = net.add_transition(Transition('right'))
        net.add_arc(Arc(token, left))
        net.add_arc(Arc(token, right))

        net.fire(left)

        assert net.enabled_transitions() == ()

    def test_the_net_can_run_until_it_is_dead(
        self, server_net: PetriNet
    ) -> None:
        """Firing repeatedly drains the queue and then stops."""
        fired = 0
        while server_net.enabled_transitions():
            server_net.fire(server_net.enabled_transitions()[0])
            fired += 1

        assert fired == 2
        assert server_net.marking == (0, 1, 2)

    def test_reset_undoes_a_run(self, server_net: PetriNet) -> None:
        """A net that has run can be returned to M0 and run again."""
        server_net.fire(server_net.transition('serve'))

        server_net.reset()

        assert server_net.marking == server_net.initial_marking


class TestMutualExclusion:
    """Two machines sharing one tool: the pattern the model exists for."""

    @pytest.fixture
    def shared_tool(self) -> PetriNet:
        """Return a net in which two machines contend for a single tool.

        Returns
        -------
        PetriNet
            Two independent machines, each needing the one token held by the
            ``tool`` place before it can work.
        """
        net = PetriNet()
        tool = net.add_place(Place('tool', initial_marking=1))
        for machine in ['1', '2']:
            idle = net.add_place(Place(f'idle_{machine}', initial_marking=1))
            working = net.add_place(Place(f'working_{machine}'))
            take = net.add_transition(Transition(f'take_{machine}'))
            release = net.add_transition(Transition(f'release_{machine}'))
            net.add_arc(Arc(idle, take))
            net.add_arc(Arc(tool, take))
            net.add_arc(Arc(take, working))
            net.add_arc(Arc(working, release))
            net.add_arc(Arc(release, idle))
            net.add_arc(Arc(release, tool))
        return net

    def test_both_machines_can_start(self, shared_tool: PetriNet) -> None:
        """Before either takes the tool, both are ready to."""
        enabled = [t.name for t in shared_tool.enabled_transitions()]

        assert enabled == ['take_1', 'take_2']

    def test_taking_the_tool_locks_the_other_machine_out(
        self, shared_tool: PetriNet
    ) -> None:
        """One token in one place is the whole of the mutual exclusion."""
        shared_tool.fire(shared_tool.transition('take_1'))

        enabled = [t.name for t in shared_tool.enabled_transitions()]

        assert enabled == ['release_1']

    def test_releasing_the_tool_lets_the_other_machine_in(
        self, shared_tool: PetriNet
    ) -> None:
        """The tool returns to the shared place and contention resumes."""
        shared_tool.fire(shared_tool.transition('take_1'))
        shared_tool.fire(shared_tool.transition('release_1'))

        enabled = [t.name for t in shared_tool.enabled_transitions()]

        assert enabled == ['take_1', 'take_2']

    def test_the_two_machines_are_never_working_at_once(
        self, shared_tool: PetriNet
    ) -> None:
        """The property the net is built to guarantee, checked exhaustively.

        Every reachable marking is visited by breadth-first search, and in
        none of them do both ``working`` places hold a token. This is the
        difference between simulating a system and analysing it: no
        interleaving is left untried.
        """
        working = [
            shared_tool.places.index(shared_tool.place('working_1')),
            shared_tool.places.index(shared_tool.place('working_2')),
        ]
        seen: set[tuple[int, ...]] = set()
        pending = [shared_tool.initial_marking]

        while pending:
            marking = pending.pop()
            if marking in seen:
                continue
            seen.add(marking)
            assert not all(marking[index] for index in working), marking
            shared_tool.marking = marking
            for transition in shared_tool.enabled_transitions():
                shared_tool.marking = marking
                shared_tool.fire(transition)
                pending.append(shared_tool.marking)

        assert len(seen) == 3


class TestRenaming:
    """Renaming a node of the net, as a graphical editor would."""

    def test_a_place_takes_the_new_name(self, server_net: PetriNet) -> None:
        """The place itself reports the new name."""
        waiting = server_net.place('waiting')

        server_net.rename_place(waiting, 'queue')

        assert waiting.name == 'queue'

    def test_a_renamed_place_is_found_under_the_new_name(
        self, server_net: PetriNet
    ) -> None:
        """The index follows the rename, so lookup keeps working."""
        waiting = server_net.place('waiting')

        server_net.rename_place(waiting, 'queue')

        assert server_net.place('queue') is waiting

    def test_the_old_name_is_released(self, server_net: PetriNet) -> None:
        """The former name no longer resolves, and can be reused."""
        server_net.rename_place(server_net.place('waiting'), 'queue')

        with pytest.raises(KeyError, match='no place named'):
            server_net.place('waiting')

        server_net.add_place(Place('waiting'))

        assert server_net.place('waiting').name == 'waiting'

    def test_renaming_does_not_reorder_the_places(
        self, server_net: PetriNet
    ) -> None:
        """The marking vector must mean the same thing after a rename.

        Place order defines what each entry of the marking vector refers to.
        If a rename moved the place, every marking recorded beforehand would
        be silently reinterpreted, and a reachability graph spanning the
        rename would be wrong.
        """
        before = [place.name for place in server_net.places]
        marking_before = server_net.marking

        server_net.rename_place(server_net.place('waiting'), 'queue')

        assert [place.name for place in server_net.places] == [
            'queue',
            *before[1:],
        ]
        assert server_net.marking == marking_before

    def test_a_transition_takes_the_new_name(
        self, server_net: PetriNet
    ) -> None:
        """Transitions rename the same way places do."""
        serve = server_net.transition('serve')

        server_net.rename_transition(serve, 'attend')

        assert serve.name == 'attend'
        assert server_net.transition('attend') is serve

    def test_renaming_does_not_reorder_the_transitions(
        self, net: PetriNet
    ) -> None:
        """Transition order decides the order enabled ones are reported in."""
        place = net.add_place(Place('p1', initial_marking=1))
        first = net.add_transition(Transition('t1'))
        second = net.add_transition(Transition('t2'))
        net.add_arc(Arc(place, first))
        net.add_arc(Arc(place, second))

        net.rename_transition(first, 'zzz')

        assert net.enabled_transitions() == (first, second)

    def test_renaming_keeps_the_arcs(self, server_net: PetriNet) -> None:
        """Arcs hold node references, so connectivity survives a rename."""
        serve = server_net.transition('serve')
        server_net.rename_place(server_net.place('waiting'), 'queue')

        sources = [arc.place.name for arc in server_net.input_arcs(serve)]

        assert sources == ['queue', 'server']

    def test_the_net_still_fires_after_a_rename(
        self, server_net: PetriNet
    ) -> None:
        """A rename is a change of label, not a change of behaviour."""
        server_net.rename_place(server_net.place('waiting'), 'queue')
        server_net.rename_transition(server_net.transition('serve'), 'attend')

        server_net.fire(server_net.transition('attend'))

        assert server_net.marking == (1, 1, 1)

    def test_renaming_to_the_same_name_does_nothing(
        self, server_net: PetriNet
    ) -> None:
        """A no-op rename is not a name clash with itself."""
        waiting = server_net.place('waiting')

        server_net.rename_place(waiting, 'waiting')

        assert server_net.place('waiting') is waiting

    def test_renaming_a_transition_to_the_same_name_does_nothing(
        self, server_net: PetriNet
    ) -> None:
        """A no-op rename is not a name clash with itself."""
        serve = server_net.transition('serve')

        server_net.rename_transition(serve, 'serve')

        assert server_net.transition('serve') is serve

    def test_a_name_taken_by_another_place_is_rejected(
        self, server_net: PetriNet
    ) -> None:
        """Names stay unique, which is what makes lookup unambiguous."""
        with pytest.raises(ValueError, match='already has a place named'):
            server_net.rename_place(server_net.place('waiting'), 'served')

    def test_a_name_taken_by_another_transition_is_rejected(
        self, net: PetriNet
    ) -> None:
        """The same rule holds for transitions."""
        first = net.add_transition(Transition('t1'))
        net.add_transition(Transition('t2'))

        with pytest.raises(ValueError, match='already has a transition named'):
            net.rename_transition(first, 't2')

    @pytest.mark.parametrize('name', ['', ' '])
    def test_a_blank_name_is_rejected(
        self, server_net: PetriNet, name: str
    ) -> None:
        """A renamed node must still be named.

        Parameters
        ----------
        server_net : PetriNet
            Net under test.
        name : str
            A name made only of whitespace, or no name at all.
        """
        with pytest.raises(ValueError, match='cannot be empty'):
            server_net.rename_place(server_net.place('waiting'), name)

    def test_a_rejected_rename_changes_nothing(
        self, server_net: PetriNet
    ) -> None:
        """Validation happens before the place or the index is touched."""
        waiting = server_net.place('waiting')

        with pytest.raises(ValueError):
            server_net.rename_place(waiting, 'served')

        assert waiting.name == 'waiting'
        assert server_net.place('waiting') is waiting
        assert server_net.place('served').name == 'served'

    def test_a_foreign_place_cannot_be_renamed(self, net: PetriNet) -> None:
        """The net renames only the places it holds."""
        with pytest.raises(ValueError, match='is not in the net'):
            net.rename_place(Place('outsider'), 'other')

    def test_a_foreign_transition_cannot_be_renamed(
        self, net: PetriNet
    ) -> None:
        """The net renames only the transitions it holds."""
        with pytest.raises(ValueError, match='is not in the net'):
            net.rename_transition(Transition('outsider'), 'other')
