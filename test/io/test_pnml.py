"""Tests for :mod:`masafi_sim_petri.io.pnml`."""

from pathlib import Path

import pytest

from masafi_sim_petri import Arc, PetriNet, Place, Transition
from masafi_sim_petri.io import (
    PNML_NAMESPACE,
    PT_NET_TYPE,
    PnmlError,
    element_for,
    element_to_pnml,
    from_element,
    from_pnml,
    graphics_of,
    nodes_by_element,
    pnml_to_element,
    qname,
    read_pnml,
    set_graphics,
    to_element,
    to_pnml,
    write_pnml,
)


@pytest.fixture
def server_net() -> PetriNet:
    """Return a queue served by a single server.

    Returns
    -------
    PetriNet
        Three places, one transition and four arcs, one of them a self loop.
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


def document(body: str, net_type: str = PT_NET_TYPE) -> str:
    """Return a PNML document wrapping the given page contents.

    Parameters
    ----------
    body : str
        The elements to place inside the ``page`` element.
    net_type : str, optional
        Value of the ``type`` attribute of the net.

    Returns
    -------
    str
        A complete PNML document.
    """
    return (
        '<pnml xmlns="http://www.pnml.org/version-2009/grammar/pnml">'
        f'<net id="n1" type="{net_type}"><page id="p1">{body}'
        '</page></net></pnml>'
    )


class TestWriting:
    """What a net looks like once written out."""

    def test_declares_the_place_transition_net_type(
        self, server_net: PetriNet
    ) -> None:
        """The type URI is what tells another tool how to read the file."""
        assert f'type="{PT_NET_TYPE}"' in to_pnml(server_net)

    def test_declares_the_pnml_namespace(
        self, server_net: PetriNet
    ) -> None:
        """A PNML document is namespaced, and tools match on it."""
        assert (
            'xmlns="http://www.pnml.org/version-2009/grammar/pnml"'
            in to_pnml(server_net)
        )

    def test_starts_with_an_xml_declaration(
        self, server_net: PetriNet
    ) -> None:
        """The encoding is stated rather than left to be guessed."""
        assert to_pnml(server_net).startswith("<?xml version='1.0'")

    def test_the_net_id_can_be_chosen(self, server_net: PetriNet) -> None:
        """A caller naming the net gets that name in the document."""
        assert 'id="queue"' in to_pnml(server_net, net_id='queue')

    def test_writes_the_initial_marking_not_the_current_one(
        self, server_net: PetriNet
    ) -> None:
        """PNML records M0, so a net that has run is written as it started."""
        server_net.fire(server_net.transition('serve'))

        assert '<text>2</text>' in to_pnml(server_net)

    def test_omits_an_empty_initial_marking(
        self, server_net: PetriNet
    ) -> None:
        """No initialMarking means no tokens, so writing zero is noise."""
        written = to_pnml(server_net)

        assert written.count('initialMarking') == 2 * 2

    def test_omits_a_weight_of_one(self, server_net: PetriNet) -> None:
        """No inscription means a weight of one, which is the default."""
        assert 'inscription' not in to_pnml(server_net)

    def test_writes_a_weight_other_than_one(self) -> None:
        """A weighted arc carries its weight as an inscription."""
        net = PetriNet()
        items = net.add_place(Place('items'))
        pack = net.add_transition(Transition('pack'))
        net.add_arc(Arc(items, pack, weight=6))

        assert '<inscription>' in to_pnml(net)
        assert '<text>6</text>' in to_pnml(net)

    def test_an_arc_points_the_way_the_tokens_move(self) -> None:
        """source and target follow the direction, not the node kinds."""
        net = PetriNet()
        place = net.add_place(Place('p1'))
        transition = net.add_transition(Transition('t1'))
        net.add_arc(Arc(transition, place))

        assert 'source="t1" target="p1"' in to_pnml(net)

    def test_an_empty_net_is_still_a_valid_document(self) -> None:
        """A net with nothing in it writes an empty page, not an error."""
        assert '<page id="page1"' in to_pnml(PetriNet())


class TestRoundTrip:
    """Writing a net and reading it back."""

    def test_keeps_the_places_in_order(self, server_net: PetriNet) -> None:
        """Place order is the meaning of the marking vector, so it must hold."""
        restored = from_pnml(to_pnml(server_net))

        assert [place.name for place in restored.places] == [
            'waiting',
            'server',
            'served',
        ]

    def test_keeps_the_marking(self, server_net: PetriNet) -> None:
        """The restored net starts where the original started."""
        restored = from_pnml(to_pnml(server_net))

        assert restored.marking == server_net.marking
        assert restored.initial_marking == server_net.initial_marking

    def test_keeps_the_transitions(self, server_net: PetriNet) -> None:
        """Transition order decides the order enabled ones are reported in."""
        restored = from_pnml(to_pnml(server_net))

        assert [t.name for t in restored.transitions] == ['serve']

    def test_keeps_the_connectivity(self, server_net: PetriNet) -> None:
        """Every arc comes back with the same endpoints and direction."""
        restored = from_pnml(to_pnml(server_net))

        assert [str(arc) for arc in restored.arcs] == [
            str(arc) for arc in server_net.arcs
        ]

    def test_keeps_arc_weights(self) -> None:
        """A weight survives the trip, including the implicit weight of one."""
        net = PetriNet()
        items = net.add_place(Place('items', initial_marking=13))
        boxes = net.add_place(Place('boxes'))
        pack = net.add_transition(Transition('pack'))
        net.add_arc(Arc(items, pack, weight=6))
        net.add_arc(Arc(pack, boxes))

        restored = from_pnml(to_pnml(net))

        assert [arc.weight for arc in restored.arcs] == [6, 1]

    def test_the_restored_net_behaves_the_same(
        self, server_net: PetriNet
    ) -> None:
        """The point of a round trip: the net still runs the same way."""
        restored = from_pnml(to_pnml(server_net))

        while restored.enabled_transitions():
            restored.fire(restored.enabled_transitions()[0])
        while server_net.enabled_transitions():
            server_net.fire(server_net.enabled_transitions()[0])

        assert restored.marking == server_net.marking

    def test_a_written_net_reads_back_identically_twice(
        self, server_net: PetriNet
    ) -> None:
        """Writing is stable: a second trip changes nothing."""
        once = to_pnml(server_net)

        assert to_pnml(from_pnml(once)) == once

    def test_an_empty_net_survives(self) -> None:
        """The degenerate case round trips like any other."""
        restored = from_pnml(to_pnml(PetriNet()))

        assert restored.places == ()
        assert restored.transitions == ()


class TestReadingForeignDocuments:
    """Documents this library did not write."""

    def test_a_name_label_is_preferred_over_the_id(self) -> None:
        """Editors keep a stable id and a separate display name."""
        net = from_pnml(
            document(
                '<place id="p1"><name><text>waiting</text></name></place>'
            )
        )

        assert net.place('waiting').name == 'waiting'

    def test_the_id_is_used_when_there_is_no_name(self) -> None:
        """A node without a name label is still identified."""
        net = from_pnml(document('<place id="p1"/>'))

        assert net.place('p1').name == 'p1'

    def test_the_id_is_used_when_the_name_is_blank(self) -> None:
        """A blank name would be rejected by the model, so the id wins."""
        net = from_pnml(
            document('<place id="p1"><name><text>  </text></name></place>')
        )

        assert net.place('p1').name == 'p1'

    def test_arcs_refer_to_ids_not_names(self) -> None:
        """The id is the reference even when the name differs from it."""
        net = from_pnml(
            document(
                '<place id="p1"><name><text>waiting</text></name></place>'
                '<transition id="t1"><name><text>serve</text></name>'
                '</transition>'
                '<arc id="a1" source="p1" target="t1"/>'
            )
        )

        assert str(net.arcs[0]) == 'waiting --1--> serve'

    def test_a_missing_initial_marking_means_no_tokens(self) -> None:
        """The standard default is zero."""
        net = from_pnml(document('<place id="p1"/>'))

        assert net.marking == (0,)

    def test_a_missing_inscription_means_a_weight_of_one(self) -> None:
        """The standard default is one."""
        net = from_pnml(
            document(
                '<place id="p1"/><transition id="t1"/>'
                '<arc id="a1" source="p1" target="t1"/>'
            )
        )

        assert net.arcs[0].weight == 1

    def test_a_document_without_a_namespace_is_accepted(self) -> None:
        """Files in the wild are not always namespaced."""
        net = from_pnml(
            '<pnml><net id="n1"><page id="p1"><place id="p1"/>'
            '</page></net></pnml>'
        )

        assert net.place('p1').name == 'p1'

    def test_nodes_are_found_on_nested_pages(self) -> None:
        """PNML lets a net be split over pages, at any depth."""
        net = from_pnml(
            document(
                '<page id="inner"><place id="p1"/>'
                '<transition id="t1"/></page>'
            )
        )

        assert net.place('p1').name == 'p1'
        assert net.transition('t1').name == 't1'

    def test_whitespace_around_a_number_is_ignored(self) -> None:
        """Pretty-printed documents put the text on its own line."""
        net = from_pnml(
            document(
                '<place id="p1"><initialMarking><text>  3  </text>'
                '</initialMarking></place>'
            )
        )

        assert net.marking == (3,)


class TestReadingRejections:
    """Documents that cannot be read as a P/T net."""

    def test_malformed_xml(self) -> None:
        """A truncated file is reported as such, not as a stack trace."""
        with pytest.raises(PnmlError, match='not well-formed XML'):
            from_pnml('<pnml><net>')

    def test_a_root_that_is_not_pnml(self) -> None:
        """Some other XML document is not a Petri net."""
        with pytest.raises(PnmlError, match="must be 'pnml'"):
            from_pnml('<graphml/>')

    def test_a_document_with_no_net(self) -> None:
        """A PNML file has to hold a net to be useful."""
        with pytest.raises(PnmlError, match='holds no net'):
            from_pnml('<pnml/>')

    def test_a_document_with_several_nets(self) -> None:
        """One PetriNet models one net, so the ambiguity is refused."""
        with pytest.raises(PnmlError, match='holds 2 nets'):
            from_pnml('<pnml><net id="a"/><net id="b"/></pnml>')

    def test_another_net_type(self) -> None:
        """A coloured net cannot be read as a P/T net."""
        with pytest.raises(PnmlError, match='Only Place/Transition nets'):
            from_pnml(
                document(
                    '',
                    net_type=(
                        'http://www.pnml.org/version-2009/grammar/'
                        'highlevelnet'
                    ),
                )
            )

    def test_a_node_without_an_id(self) -> None:
        """Arcs refer to nodes by id, so a node without one is unusable."""
        with pytest.raises(PnmlError, match='place element has no id'):
            from_pnml(document('<place/>'))

    def test_a_repeated_id(self) -> None:
        """Two nodes sharing an id would make every reference ambiguous."""
        with pytest.raises(PnmlError, match="'p1' is used twice"):
            from_pnml(document('<place id="p1"/><place id="p1"/>'))

    def test_two_nodes_with_the_same_name(self) -> None:
        """The net refuses duplicate names, and the reason is reported."""
        with pytest.raises(PnmlError, match='already has a place named'):
            from_pnml(
                document(
                    '<place id="p1"><name><text>same</text></name></place>'
                    '<place id="p2"><name><text>same</text></name></place>'
                )
            )

    def test_an_initial_marking_that_is_not_a_number(self) -> None:
        """A marking counts tokens, so text is not acceptable."""
        with pytest.raises(PnmlError, match='not a whole number'):
            from_pnml(
                document(
                    '<place id="p1"><initialMarking><text>many</text>'
                    '</initialMarking></place>'
                )
            )

    def test_a_negative_initial_marking(self) -> None:
        """The model rejects it, and the failure is reported as PNML's."""
        with pytest.raises(PnmlError, match='cannot be negative'):
            from_pnml(
                document(
                    '<place id="p1"><initialMarking><text>-1</text>'
                    '</initialMarking></place>'
                )
            )

    def test_an_inscription_that_is_not_a_number(self) -> None:
        """An arc weight has to be a whole number too."""
        with pytest.raises(PnmlError, match='not a whole number'):
            from_pnml(
                document(
                    '<place id="p1"/><transition id="t1"/>'
                    '<arc id="a1" source="p1" target="t1">'
                    '<inscription><text>lots</text></inscription></arc>'
                )
            )

    def test_an_arc_without_a_source(self) -> None:
        """An arc has to say where it comes from."""
        with pytest.raises(PnmlError, match="Arc 'a1' has no source"):
            from_pnml(document('<arc id="a1" target="t1"/>'))

    def test_an_arc_without_a_target(self) -> None:
        """An arc has to say where it goes."""
        with pytest.raises(PnmlError, match="Arc 'a1' has no target"):
            from_pnml(
                document('<place id="p1"/><arc id="a1" source="p1"/>')
            )

    def test_an_arc_to_an_undefined_node(self) -> None:
        """A dangling reference is a broken document."""
        with pytest.raises(PnmlError, match='does not define'):
            from_pnml(
                document(
                    '<place id="p1"/>'
                    '<arc id="a1" source="p1" target="nowhere"/>'
                )
            )

    def test_an_arc_between_two_places(self) -> None:
        """The bipartite rule is enforced on the way in as well."""
        with pytest.raises(PnmlError, match='must join a place and a transition'):
            from_pnml(
                document(
                    '<place id="p1"/><place id="p2"/>'
                    '<arc id="a1" source="p1" target="p2"/>'
                )
            )

    def test_a_zero_weight_arc(self) -> None:
        """A weight below one is refused, as it is in the model."""
        with pytest.raises(PnmlError, match='at least 1'):
            from_pnml(
                document(
                    '<place id="p1"/><transition id="t1"/>'
                    '<arc id="a1" source="p1" target="t1">'
                    '<inscription><text>0</text></inscription></arc>'
                )
            )

    def test_a_transition_whose_id_is_only_whitespace(self) -> None:
        """A node named only by a blank id cannot be built."""
        with pytest.raises(PnmlError, match='cannot be empty'):
            from_pnml(document('<transition id=" "/>'))

    def test_a_place_whose_id_is_only_whitespace(self) -> None:
        """The same holds for a place, whose name would also be blank."""
        with pytest.raises(PnmlError, match='cannot be empty'):
            from_pnml(document('<place id=" "/>'))

    def test_an_arc_without_an_id(self) -> None:
        """An arc has to be identifiable to be reported on."""
        with pytest.raises(PnmlError, match='arc element has no id'):
            from_pnml(document('<arc source="p1" target="t1"/>'))


class TestFiles:
    """Reading and writing through the file system."""

    def test_a_net_survives_a_file(
        self, server_net: PetriNet, tmp_path: Path
    ) -> None:
        """The whole point: save a net and open it again.

        Parameters
        ----------
        server_net : PetriNet
            Net to save.
        tmp_path : pathlib.Path
            Directory provided by pytest for this test.
        """
        path = tmp_path / 'queue.pnml'

        write_pnml(server_net, path)
        restored = read_pnml(path)

        assert restored.marking == server_net.marking
        assert [place.name for place in restored.places] == [
            place.name for place in server_net.places
        ]

    def test_accepts_a_path_as_a_string(
        self, server_net: PetriNet, tmp_path: Path
    ) -> None:
        """Callers should not have to build a Path first.

        Parameters
        ----------
        server_net : PetriNet
            Net to save.
        tmp_path : pathlib.Path
            Directory provided by pytest for this test.
        """
        path = str(tmp_path / 'queue.pnml')

        write_pnml(server_net, path)

        assert read_pnml(path).marking == server_net.marking

    def test_the_file_is_utf8_with_a_declaration(
        self, server_net: PetriNet, tmp_path: Path
    ) -> None:
        """The file states its own encoding.

        Parameters
        ----------
        server_net : PetriNet
            Net to save.
        tmp_path : pathlib.Path
            Directory provided by pytest for this test.
        """
        path = tmp_path / 'queue.pnml'

        write_pnml(server_net, path)

        assert path.read_text(encoding='utf-8').startswith(
            "<?xml version='1.0' encoding='UTF-8'?>"
        )

    def test_a_missing_file_raises(self, tmp_path: Path) -> None:
        """Reading a file that is not there is an OSError, not a PnmlError.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Directory provided by pytest for this test.
        """
        with pytest.raises(OSError):
            read_pnml(tmp_path / 'nothing.pnml')

    def test_names_with_accents_survive(self, tmp_path: Path) -> None:
        """Files are UTF-8, so a Catalan or Spanish name is safe.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Directory provided by pytest for this test.
        """
        net = PetriNet()
        net.add_place(Place('màquina_aturada'))
        path = tmp_path / 'accents.pnml'

        write_pnml(net, path)

        assert read_pnml(path).place('màquina_aturada').name == (
            'màquina_aturada'
        )


class TestElementLevel:
    """The tree level, which is what a graphical editor builds on."""

    def test_to_element_returns_the_pnml_root(
        self, server_net: PetriNet
    ) -> None:
        """The caller is handed the document root, not a fragment."""
        root = to_element(server_net)

        assert root.tag == qname('pnml')

    def test_a_tree_serialises_to_the_same_document(
        self, server_net: PetriNet
    ) -> None:
        """The shorthand and the two steps agree."""
        assert element_to_pnml(to_element(server_net)) == to_pnml(server_net)

    def test_a_parsed_tree_reads_to_the_same_net(
        self, server_net: PetriNet
    ) -> None:
        """The shorthand and the two steps agree on the way in too."""
        document = to_pnml(server_net)

        from_the_tree = from_element(pnml_to_element(document))

        assert from_the_tree.marking == from_pnml(document).marking

    def test_a_net_id_is_carried_through_the_tree(
        self, server_net: PetriNet
    ) -> None:
        """Options of the shorthand are options of the tree builder."""
        root = to_element(server_net, net_id='queue')

        assert root[0].get('id') == 'queue'

    def test_parsing_rejects_a_bad_root(self) -> None:
        """The tree level validates what it can, as the shorthand does."""
        with pytest.raises(PnmlError, match="must be 'pnml'"):
            pnml_to_element('<graphml/>')

    def test_parsing_rejects_malformed_xml(self) -> None:
        """A truncated document fails at parse time."""
        with pytest.raises(PnmlError, match='not well-formed XML'):
            pnml_to_element('<pnml><net>')


class TestQualifiedNames:
    """Building element names without writing the namespace out."""

    def test_qualifies_a_local_name(self) -> None:
        """A caller adding elements needs the namespace on them."""
        assert qname('graphics') == f'{{{PNML_NAMESPACE}}}graphics'


class TestElementFor:
    """Finding the element that stands for a node of a net."""

    def test_finds_a_place(self, server_net: PetriNet) -> None:
        """A place is reachable from the net object that produced it."""
        root = to_element(server_net)

        element = element_for(root, server_net.place('waiting'))

        assert element.get('id') == 'waiting'

    def test_finds_a_transition(self, server_net: PetriNet) -> None:
        """So is a transition."""
        root = to_element(server_net)

        element = element_for(root, server_net.transition('serve'))

        assert element.get('id') == 'serve'

    def test_finds_an_arc_by_its_endpoints(
        self, server_net: PetriNet
    ) -> None:
        """Arcs are unnamed, so they are matched on what they join."""
        root = to_element(server_net)

        element = element_for(root, server_net.arcs[0])

        assert element.get('source') == 'waiting'
        assert element.get('target') == 'serve'

    def test_distinguishes_the_two_arcs_of_a_self_loop(
        self, server_net: PetriNet
    ) -> None:
        """The two directions between one pair are two different elements."""
        root = to_element(server_net)
        into = [arc for arc in server_net.arcs if arc.place.name == 'server'
                and arc.is_input][0]
        out_of = [arc for arc in server_net.arcs if arc.place.name == 'server'
                  and arc.is_output][0]

        assert element_for(root, into).get('source') == 'server'
        assert element_for(root, out_of).get('target') == 'server'

    def test_finds_an_element_by_identifier(
        self, server_net: PetriNet
    ) -> None:
        """A document from elsewhere is addressed by its own ids."""
        root = to_element(server_net)

        assert element_for(root, 'served').get('id') == 'served'

    def test_an_unknown_node_is_reported(
        self, server_net: PetriNet
    ) -> None:
        """Asking for something that is not there is an error, not None."""
        root = to_element(server_net)

        with pytest.raises(PnmlError, match='no element with id'):
            element_for(root, 'nowhere')

    def test_an_unknown_arc_is_reported(self, server_net: PetriNet) -> None:
        """The message names the endpoints that were looked for."""
        other = PetriNet()
        place = other.add_place(Place('a'))
        transition = other.add_transition(Transition('b'))
        arc = other.add_arc(Arc(place, transition))

        with pytest.raises(PnmlError, match="no arc from 'a' to 'b'"):
            element_for(to_element(server_net), arc)


class TestGraphics:
    """Carrying layout and colour on the tree, which the model does not hold."""

    def test_position_is_written(self, server_net: PetriNet) -> None:
        """The position is what an editor most needs to keep."""
        root = to_element(server_net)

        set_graphics(
            element_for(root, server_net.place('waiting')), position=(40, 120)
        )

        assert '<position x="40" y="120"' in element_to_pnml(root)

    def test_colours_are_written(self, server_net: PetriNet) -> None:
        """Fill and line carry the colours."""
        root = to_element(server_net)

        set_graphics(
            element_for(root, server_net.place('waiting')),
            fill={'color': '#B0D0FF'},
            line={'color': '#204060', 'width': '2'},
        )

        document = element_to_pnml(root)

        assert '<fill color="#B0D0FF"' in document
        assert '<line color="#204060" width="2"' in document

    def test_children_follow_the_order_of_the_standard(
        self, server_net: PetriNet
    ) -> None:
        """position, dimension, fill then line, whatever order they are given."""
        root = to_element(server_net)

        graphics = set_graphics(
            element_for(root, server_net.place('waiting')),
            line={'width': '1'},
            fill={'color': '#FFF'},
            dimension=(30, 30),
            position=(0, 0),
        )

        assert [child.tag.rpartition('}')[2] for child in graphics] == [
            'position',
            'dimension',
            'fill',
            'line',
        ]

    def test_whole_coordinates_are_written_without_a_decimal_point(
        self, server_net: PetriNet
    ) -> None:
        """A float that is a whole number should not read as 40.0."""
        root = to_element(server_net)

        set_graphics(
            element_for(root, server_net.place('waiting')),
            position=(40.0, 120.5),
        )

        assert '<position x="40" y="120.5"' in element_to_pnml(root)

    def test_nothing_is_written_when_nothing_is_given(
        self, server_net: PetriNet
    ) -> None:
        """An empty graphics element leaves the standard's defaults to apply."""
        root = to_element(server_net)

        graphics = set_graphics(
            element_for(root, server_net.place('waiting'))
        )

        assert list(graphics) == []

    def test_setting_graphics_twice_replaces_them(
        self, server_net: PetriNet
    ) -> None:
        """Moving a node must not leave its old position behind."""
        root = to_element(server_net)
        element = element_for(root, server_net.place('waiting'))

        set_graphics(element, position=(40, 120))
        set_graphics(element, position=(200, 300))

        document = element_to_pnml(root)

        assert document.count('<position') == 1
        assert '<position x="200" y="300"' in document

    def test_graphics_can_be_read_back(self, server_net: PetriNet) -> None:
        """An editor reopening a file finds the layout it saved."""
        root = to_element(server_net)
        set_graphics(
            element_for(root, server_net.place('waiting')), position=(40, 120)
        )

        reparsed = pnml_to_element(element_to_pnml(root))
        graphics = graphics_of(element_for(reparsed, 'waiting'))

        assert graphics is not None
        assert graphics[0].attrib == {'x': '40', 'y': '120'}

    def test_an_element_without_graphics_reads_as_none(
        self, server_net: PetriNet
    ) -> None:
        """Absence is reported as absence rather than as an empty element."""
        root = to_element(server_net)

        assert graphics_of(element_for(root, 'waiting')) is None

    def test_graphics_do_not_disturb_the_model(
        self, server_net: PetriNet
    ) -> None:
        """A decorated document still reads back as the same net."""
        root = to_element(server_net)
        for place in server_net.places:
            set_graphics(element_for(root, place), position=(10, 20))
        for transition in server_net.transitions:
            set_graphics(element_for(root, transition), fill={'color': '#EEE'})
        for arc in server_net.arcs:
            set_graphics(element_for(root, arc), line={'shape': 'line'})

        restored = from_element(pnml_to_element(element_to_pnml(root)))

        assert restored.marking == server_net.marking
        assert [str(arc) for arc in restored.arcs] == [
            str(arc) for arc in server_net.arcs
        ]

    def test_arcs_can_carry_graphics(self, server_net: PetriNet) -> None:
        """Bend points and line style belong to the arc element."""
        root = to_element(server_net)

        set_graphics(
            element_for(root, server_net.arcs[0]), position=(80, 120)
        )

        element = element_for(root, server_net.arcs[0])
        graphics = graphics_of(element)

        assert graphics is not None
        assert graphics[0].attrib == {'x': '80', 'y': '120'}


class TestNodesByElement:
    """Mapping the elements of a tree back to the nodes of a net."""

    def test_maps_a_written_tree(self, server_net: PetriNet) -> None:
        """A tree built from a net maps back onto that same net."""
        root = to_element(server_net)

        mapping = nodes_by_element(root, server_net)

        assert set(mapping.values()) == {
            *server_net.places,
            *server_net.transitions,
            *server_net.arcs,
        }

    def test_maps_a_read_tree(self, server_net: PetriNet) -> None:
        """The mapping is what a caller needs after reading a document."""
        root = pnml_to_element(to_pnml(server_net))
        restored = from_element(root)

        mapping = nodes_by_element(root, restored)

        assert {
            element.get('id'): node.name
            for element, node in mapping.items()
            if element.get('id') in {'waiting', 'serve'}
        } == {'waiting': 'waiting', 'serve': 'serve'}

    def test_maps_arcs_in_order(self, server_net: PetriNet) -> None:
        """Arcs are matched positionally, since they carry no name."""
        root = to_element(server_net)

        mapping = nodes_by_element(root, server_net)
        arcs = [
            node for element, node in mapping.items()
            if element.tag == qname('arc')
        ]

        assert arcs == list(server_net.arcs)

    def test_maps_a_node_whose_id_differs_from_its_name(self) -> None:
        """The reason the mapping exists: an id need not be a name."""
        root = pnml_to_element(
            document(
                '<place id="n17"><name><text>buffer</text></name></place>'
            )
        )
        net = from_element(root)

        mapping = nodes_by_element(root, net)
        element = next(iter(mapping))

        assert element.get('id') == 'n17'
        assert mapping[element].name == 'buffer'

    def test_can_be_inverted_for_a_node_to_element_lookup(self) -> None:
        """Inverting gives a lookup that works on a foreign document."""
        root = pnml_to_element(
            document(
                '<place id="n17"><name><text>buffer</text></name></place>'
            )
        )
        net = from_element(root)

        elements = {
            node: element
            for element, node in nodes_by_element(root, net).items()
        }

        assert elements[net.place('buffer')].get('id') == 'n17'

    def test_a_mismatched_net_is_rejected(
        self, server_net: PetriNet
    ) -> None:
        """A tree and a net that do not describe each other cannot be paired."""
        root = to_element(server_net)

        with pytest.raises(PnmlError, match='do not describe each other'):
            nodes_by_element(root, PetriNet())

    def test_a_tree_with_no_net_is_rejected(self) -> None:
        """The same rule as reading: one tree, one net."""
        with pytest.raises(PnmlError, match='holds no net'):
            nodes_by_element(pnml_to_element('<pnml/>'), PetriNet())


class TestEditorWorkflow:
    """The pattern a project such as the graphical editor is expected to use."""

    def test_a_layout_survives_a_save_and_a_load(
        self, server_net: PetriNet
    ) -> None:
        """The whole point: draw a net, save it, open it, find the layout.

        The view data is held beside the net, keyed by the node object, and
        never enters the model.
        """
        views = {
            place: (index * 100.0, 40.0)
            for index, place in enumerate(server_net.places)
        }

        root = to_element(server_net)
        for place, (x, y) in views.items():
            set_graphics(element_for(root, place), position=(x, y))
        document = element_to_pnml(root)

        reloaded_root = pnml_to_element(document)
        reloaded_net = from_element(reloaded_root)
        reloaded: dict[str, tuple[float, float]] = {}
        for element, node in nodes_by_element(
            reloaded_root, reloaded_net
        ).items():
            graphics = graphics_of(element)
            if graphics is None:
                continue
            position = graphics[0]
            reloaded[node.name] = (
                float(position.get('x', '0')),
                float(position.get('y', '0')),
            )

        assert reloaded == {
            place.name: position for place, position in views.items()
        }

    def test_renaming_does_not_disturb_a_view_table(
        self, server_net: PetriNet
    ) -> None:
        """Keying the view table by object is what makes renames free.

        A table keyed by name would need updating in step with every rename,
        and would go stale the first time that was forgotten.
        """
        waiting = server_net.place('waiting')
        views = {waiting: (40.0, 120.0)}

        server_net.rename_place(waiting, 'queue')

        assert views[waiting] == (40.0, 120.0)
        assert views[server_net.place('queue')] == (40.0, 120.0)
