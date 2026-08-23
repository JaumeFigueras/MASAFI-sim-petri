"""Reading and writing Place/Transition nets as PNML.

PNML, the Petri Net Markup Language, is the interchange format for Petri nets
standardised as ISO/IEC 15909-2. It is an XML format built on a core model
shared by every kind of net, with the features specific to one kind of net
defined by a separate grammar called a *Petri net type definition*, identified
by a URI. This module implements the Place/Transition type,
``http://www.pnml.org/version-2009/grammar/ptnet``.

The model knows nothing about this module. Serialisation reads a net through
its public interface and builds one the same way, so
:mod:`masafi_sim_petri.petri_net` never imports an XML library.

Notes
-----
The current marking of a net is not written. PNML records the *initial*
marking of each place, which is what
:attr:`~masafi_sim_petri.petri_net.place.Place.initial_marking` holds; a net
that has been run and then written out is written in its initial state. A net
read back is therefore always at its initial marking.

Parsing uses :mod:`xml.etree.ElementTree`, which is not hardened against
maliciously constructed XML. Documents from an untrusted source should be
parsed with a hardened parser such as ``defusedxml`` instead.
"""

from __future__ import annotations

import xml.etree.ElementTree as ElementTree
from collections.abc import Callable
from pathlib import Path

from masafi_sim_petri.petri_net.arc import Arc
from masafi_sim_petri.petri_net.petri_net import PetriNet
from masafi_sim_petri.petri_net.place import Place
from masafi_sim_petri.petri_net.transition import Transition

PNML_NAMESPACE = 'http://www.pnml.org/version-2009/grammar/pnml'
"""str: XML namespace of the PNML core model."""

PT_NET_TYPE = 'http://www.pnml.org/version-2009/grammar/ptnet'
"""str: Petri net type definition URI of Place/Transition nets."""

_XML_DECLARATION = "<?xml version='1.0' encoding='UTF-8'?>\n"


class PnmlError(ValueError):
    """Raised when a PNML document cannot be read as a P/T net.

    It derives from :exc:`ValueError` because a malformed document is a bad
    value, and because the rules the model itself enforces -- a bipartite arc,
    a non-negative marking, a unique name -- are reported the same way.
    """


def to_element(
    net: PetriNet, net_id: str = 'net1'
) -> ElementTree.Element:
    """Return a net as a PNML element tree.

    This is the level at which another project can add what the model does not
    hold. A graphical editor builds the tree from the net, attaches
    ``graphics`` elements carrying positions and colours, and serialises the
    result with :func:`element_to_pnml` -- without the model ever growing a
    coordinate.

    Parameters
    ----------
    net : PetriNet
        Net to serialise.
    net_id : str, optional
        Identifier written on the ``net`` element. Defaults to ``'net1'``.

    Returns
    -------
    xml.etree.ElementTree.Element
        The ``pnml`` root element, not indented.

    See Also
    --------
    element_to_pnml : Turn the tree into a document.
    element_for : Find the element that stands for a node of the net.
    set_graphics : Attach position, size and colours to an element.

    Notes
    -----
    Places and transitions are given the name of the node as their ``id``.
    Arcs, which the model does not name, are given ``arc1``, ``arc2`` and so
    on in the order they were added to the net.

    Examples
    --------
    >>> from masafi_sim_petri import PetriNet, Place
    >>> from masafi_sim_petri.io import element_for, set_graphics, to_element
    >>> net = PetriNet()
    >>> buffer = net.add_place(Place('buffer'))
    >>> root = to_element(net)
    >>> _ = set_graphics(
    ...     element_for(root, buffer),
    ...     position=(40, 120),
    ...     fill={'color': '#B0D0FF'},
    ... )
    >>> from masafi_sim_petri.io import element_to_pnml
    >>> print(element_to_pnml(root))  # doctest: +NORMALIZE_WHITESPACE
    <?xml version='1.0' encoding='UTF-8'?>
    <pnml xmlns="http://www.pnml.org/version-2009/grammar/pnml">
      <net id="net1" type="http://www.pnml.org/version-2009/grammar/ptnet">
        <page id="page1">
          <place id="buffer">
            <name>
              <text>buffer</text>
            </name>
            <graphics>
              <position x="40" y="120" />
              <fill color="#B0D0FF" />
            </graphics>
          </place>
        </page>
      </net>
    </pnml>
    """
    root = ElementTree.Element(_tag('pnml'))
    net_element = ElementTree.SubElement(
        root, _tag('net'), {'id': net_id, 'type': PT_NET_TYPE}
    )
    page = ElementTree.SubElement(net_element, _tag('page'), {'id': 'page1'})

    for place in net.places:
        element = ElementTree.SubElement(
            page, _tag('place'), {'id': place.name}
        )
        _append_labelled_text(element, 'name', place.name)
        if place.initial_marking:
            _append_labelled_text(
                element, 'initialMarking', str(place.initial_marking)
            )

    for transition in net.transitions:
        element = ElementTree.SubElement(
            page, _tag('transition'), {'id': transition.name}
        )
        _append_labelled_text(element, 'name', transition.name)

    for number, arc in enumerate(net.arcs, start=1):
        source, target = _arc_endpoints(arc)
        element = ElementTree.SubElement(
            page,
            _tag('arc'),
            {
                'id': f'arc{number}',
                'source': source.name,
                'target': target.name,
            },
        )
        if arc.weight != 1:
            _append_labelled_text(element, 'inscription', str(arc.weight))

    return root


def element_to_pnml(root: ElementTree.Element) -> str:
    """Return a PNML element tree as a document.

    The tree is indented in place, so an element added by hand is laid out
    like the rest of the document.

    Parameters
    ----------
    root : xml.etree.ElementTree.Element
        The ``pnml`` root element.

    Returns
    -------
    str
        A complete PNML document, indented, with an XML declaration.

    See Also
    --------
    to_element : Build the tree from a net.
    """
    ElementTree.register_namespace('', PNML_NAMESPACE)
    ElementTree.indent(root, space='  ')
    return _XML_DECLARATION + ElementTree.tostring(root, encoding='unicode')


def to_pnml(net: PetriNet, net_id: str = 'net1') -> str:
    """Return a net as a PNML document.

    A shorthand for :func:`to_element` followed by :func:`element_to_pnml`,
    for when nothing needs to be added to the document.

    Parameters
    ----------
    net : PetriNet
        Net to serialise.
    net_id : str, optional
        Identifier written on the ``net`` element. Defaults to ``'net1'``.

    Returns
    -------
    str
        A complete PNML document, indented, with an XML declaration.

    See Also
    --------
    to_element : Build the tree instead, to add graphics or tool data.
    write_pnml : Write the document straight to a file.
    from_pnml : Read a document back into a net.

    Examples
    --------
    >>> from masafi_sim_petri import PetriNet, Place
    >>> from masafi_sim_petri.io import to_pnml
    >>> net = PetriNet()
    >>> _ = net.add_place(Place('waiting', initial_marking=2))
    >>> print(to_pnml(net))  # doctest: +NORMALIZE_WHITESPACE
    <?xml version='1.0' encoding='UTF-8'?>
    <pnml xmlns="http://www.pnml.org/version-2009/grammar/pnml">
      <net id="net1" type="http://www.pnml.org/version-2009/grammar/ptnet">
        <page id="page1">
          <place id="waiting">
            <name>
              <text>waiting</text>
            </name>
            <initialMarking>
              <text>2</text>
            </initialMarking>
          </place>
        </page>
      </net>
    </pnml>
    """
    return element_to_pnml(to_element(net, net_id=net_id))


def write_pnml(
    net: PetriNet, path: str | Path, net_id: str = 'net1'
) -> None:
    """Write a net to a file as a PNML document.

    Parameters
    ----------
    net : PetriNet
        Net to serialise.
    path : str or pathlib.Path
        File to write. An existing file is replaced.
    net_id : str, optional
        Identifier written on the ``net`` element. Defaults to ``'net1'``.

    See Also
    --------
    to_pnml : Return the document as a string instead.
    """
    Path(path).write_text(to_pnml(net, net_id=net_id), encoding='utf-8')


def pnml_to_element(document: str) -> ElementTree.Element:
    """Parse a PNML document into an element tree.

    Reading a document at this level lets a project take the model from
    :func:`from_element` and read whatever else it needs -- ``graphics``,
    ``toolspecific`` -- from the same tree, which the model does not carry.

    Parameters
    ----------
    document : str
        A PNML document.

    Returns
    -------
    xml.etree.ElementTree.Element
        The ``pnml`` root element.

    Raises
    ------
    PnmlError
        If the document is not well-formed XML, or its root is not ``pnml``.

    See Also
    --------
    from_element : Build a net from the tree.
    """
    try:
        root = ElementTree.fromstring(document)
    except ElementTree.ParseError as error:
        raise PnmlError(
            f'The document is not well-formed XML: {error}'
        ) from error

    if _local_name(root) != 'pnml':
        raise PnmlError(
            "The root element of a PNML document must be 'pnml', got "
            f'{_local_name(root)!r}'
        )
    return root


def from_element(root: ElementTree.Element) -> PetriNet:
    """Build a net from a PNML element tree.

    Places, transitions and arcs are added in the order they appear in the
    tree, so a net written by :func:`to_element` and read back has the same
    place order and therefore the same marking vector.

    A node is named by its ``name`` label when it has one, and by its ``id``
    otherwise. The ``id`` is what arcs refer to, whichever is used as the name.

    Anything the model does not hold -- ``graphics``, ``toolspecific`` -- is
    ignored here rather than lost: it is still in the tree, for the caller to
    read.

    Parameters
    ----------
    root : xml.etree.ElementTree.Element
        The ``pnml`` root element.

    Returns
    -------
    PetriNet
        The net described by the tree, at its initial marking.

    Raises
    ------
    PnmlError
        If the tree holds anything other than exactly one net, declares a net
        type other than Place/Transition, or describes a net this library
        cannot build.

    See Also
    --------
    pnml_to_element : Parse a document into a tree.
    """
    net_element = _net_element(root)
    declared_type = net_element.get('type')
    if declared_type is not None and declared_type != PT_NET_TYPE:
        raise PnmlError(
            f'Only Place/Transition nets can be read, got net type '
            f'{declared_type!r}'
        )

    net = PetriNet()
    nodes: dict[str, Place | Transition] = {}

    for element in _descendants(net_element, 'place'):
        identifier = _identifier(element, 'place')
        marking = _integer_label(element, 'initialMarking', default=0)
        name = _node_name(element, identifier)
        try:
            place = Place(name, initial_marking=marking)
        except ValueError as error:
            raise PnmlError(
                f'Place {identifier!r} cannot be read: {error}'
            ) from error
        _add(net.add_place, place, identifier, nodes)

    for element in _descendants(net_element, 'transition'):
        identifier = _identifier(element, 'transition')
        name = _node_name(element, identifier)
        try:
            transition = Transition(name)
        except ValueError as error:
            raise PnmlError(
                f'Transition {identifier!r} cannot be read: {error}'
            ) from error
        _add(net.add_transition, transition, identifier, nodes)

    for element in _descendants(net_element, 'arc'):
        identifier = _identifier(element, 'arc')
        source = _endpoint(element, 'source', identifier, nodes)
        target = _endpoint(element, 'target', identifier, nodes)
        weight = _integer_label(element, 'inscription', default=1)
        try:
            net.add_arc(Arc(source, target, weight=weight))
        except ValueError as error:
            raise PnmlError(
                f'Arc {identifier!r} cannot be added: {error}'
            ) from error

    return net


def from_pnml(document: str) -> PetriNet:
    """Read a PNML document into a net.

    A shorthand for :func:`pnml_to_element` followed by :func:`from_element`,
    for when nothing but the net is wanted from the document.

    Parameters
    ----------
    document : str
        A PNML document.

    Returns
    -------
    PetriNet
        The net described by the document, at its initial marking.

    Raises
    ------
    PnmlError
        If the document is not well-formed XML, is not PNML, holds anything
        other than exactly one net, declares a net type other than
        Place/Transition, or describes a net this library cannot build.

    See Also
    --------
    pnml_to_element : Parse the document into a tree, to read graphics too.
    read_pnml : Read the document from a file.
    to_pnml : Write a net back out.

    Examples
    --------
    >>> from masafi_sim_petri import PetriNet, Place, Transition
    >>> from masafi_sim_petri.io import from_pnml, to_pnml
    >>> net = PetriNet()
    >>> _ = net.add_place(Place('waiting', initial_marking=2))
    >>> _ = net.add_transition(Transition('serve'))
    >>> restored = from_pnml(to_pnml(net))
    >>> [place.name for place in restored.places]
    ['waiting']
    >>> restored.marking
    (2,)
    """
    return from_element(pnml_to_element(document))


def qname(local_name: str) -> str:
    """Return an element name qualified with the PNML namespace.

    PNML elements are namespaced, and :mod:`xml.etree.ElementTree` spells a
    qualified name ``{namespace}name``. Use this rather than writing the
    namespace out, so a change of PNML version is a change in one place.

    Parameters
    ----------
    local_name : str
        Local name of the element, such as ``'graphics'``.

    Returns
    -------
    str
        The qualified name.

    Examples
    --------
    >>> from masafi_sim_petri.io import qname
    >>> qname('graphics')
    '{http://www.pnml.org/version-2009/grammar/pnml}graphics'
    """
    return _tag(local_name)


def element_for(
    root: ElementTree.Element, node: Place | Transition | Arc | str
) -> ElementTree.Element:
    """Return the element of a tree that stands for a node of a net.

    This is how a caller finds the place to hang a ``graphics`` or
    ``toolspecific`` element on. An arc is matched on its two endpoints rather
    than on an identifier, because the model does not name arcs and a net
    never holds two arcs joining the same pair the same way round.

    Parameters
    ----------
    root : xml.etree.ElementTree.Element
        The ``pnml`` root element, as built by :func:`to_element`.
    node : Place, Transition, Arc or str
        Node to look for, or the ``id`` of an element to look for directly.

    Returns
    -------
    xml.etree.ElementTree.Element
        The matching element.

    Raises
    ------
    PnmlError
        If the tree holds no element for that node.

    Notes
    -----
    A place or transition is matched on the ``id`` written by
    :func:`to_element`, which is the name of the node. In a document read from
    elsewhere the ``id`` and the name may differ, and the ``id`` should be
    passed as a string.
    """
    if isinstance(node, Arc):
        source, target = _arc_endpoints(node)
        for element in _descendants(root, 'arc'):
            if (
                element.get('source') == source.name
                and element.get('target') == target.name
            ):
                return element
        raise PnmlError(
            f'The tree holds no arc from {source.name!r} to {target.name!r}'
        )

    identifier = node if isinstance(node, str) else node.name
    for name in ['place', 'transition']:
        for element in _descendants(root, name):
            if element.get('id') == identifier:
                return element
    raise PnmlError(f'The tree holds no element with id {identifier!r}')


def nodes_by_element(
    root: ElementTree.Element, net: PetriNet
) -> dict[ElementTree.Element, Place | Transition | Arc]:
    """Return which element of a tree stands for which node of a net.

    This is the counterpart of :func:`element_for`, for going the other way.
    After :func:`from_element` has built a net, a caller reading the graphics
    or the tool data out of the same tree needs to know which node each
    element produced -- and the ``id`` cannot answer that on its own, because
    a node is named after its ``name`` label when it has one.

    The correspondence is positional and holds in both directions:
    :func:`from_element` adds nodes in document order, and :func:`to_element`
    writes them in the order the net holds them. So this works whether the
    tree was read or written.

    Parameters
    ----------
    root : xml.etree.ElementTree.Element
        The ``pnml`` root element.
    net : PetriNet
        The net that tree describes, as returned by :func:`from_element` or as
        passed to :func:`to_element`.

    Returns
    -------
    dict
        Mapping from ``place``, ``transition`` and ``arc`` elements to the
        nodes of the net.

    Raises
    ------
    PnmlError
        If the tree and the net do not hold the same number of places,
        transitions or arcs, which means they do not describe each other.

    See Also
    --------
    element_for : Go from a node to its element.

    Notes
    -----
    Inverting the mapping gives a node-to-element lookup that works for a tree
    read from elsewhere, where an ``id`` need not equal a name::

        elements = {node: element
                    for element, node in nodes_by_element(root, net).items()}

    Examples
    --------
    >>> from masafi_sim_petri import PetriNet, Place
    >>> from masafi_sim_petri.io import (
    ...     from_element, nodes_by_element, pnml_to_element, to_pnml,
    ... )
    >>> net = PetriNet()
    >>> _ = net.add_place(Place('buffer', initial_marking=1))
    >>> root = pnml_to_element(to_pnml(net))
    >>> restored = from_element(root)
    >>> {element.get('id'): node.name
    ...  for element, node in nodes_by_element(root, restored).items()}
    {'buffer': 'buffer'}
    """
    net_element = _net_element(root)
    mapping: dict[ElementTree.Element, Place | Transition | Arc] = {}
    for name, nodes in [
        ('place', net.places),
        ('transition', net.transitions),
        ('arc', net.arcs),
    ]:
        elements = _descendants(net_element, name)
        if len(elements) != len(nodes):
            raise PnmlError(
                f'The tree holds {len(elements)} {name} elements but the net '
                f'holds {len(nodes)}, so they do not describe each other'
            )
        mapping.update(zip(elements, nodes, strict=True))
    return mapping


def set_graphics(
    element: ElementTree.Element,
    position: tuple[float, float] | None = None,
    dimension: tuple[float, float] | None = None,
    fill: dict[str, str] | None = None,
    line: dict[str, str] | None = None,
) -> ElementTree.Element:
    """Attach a ``graphics`` element to a node, transition or arc element.

    PNML has a defined place for how a net looks, which is what lets a layout
    survive a trip through a tool that does not care about it. The model holds
    no layout data, so this writes it onto the tree instead.

    Any ``graphics`` element already on `element` is replaced. Arguments left
    as ``None`` are not written, so the standard's own defaults apply.

    Parameters
    ----------
    element : xml.etree.ElementTree.Element
        Element to attach the graphics to.
    position : tuple of float, optional
        ``(x, y)`` of the node, or of a bend point of an arc.
    dimension : tuple of float, optional
        ``(width, height)`` of the node.
    fill : dict, optional
        Attributes of the ``fill`` element. The standard defines ``color``,
        ``gradient-color``, ``gradient-rotation`` and ``image``.
    line : dict, optional
        Attributes of the ``line`` element. The standard defines ``color``,
        ``shape``, ``style`` and ``width``.

    Returns
    -------
    xml.etree.ElementTree.Element
        The ``graphics`` element, so that anything else can be added to it.

    See Also
    --------
    graphics_of : Read the graphics of an element back.

    Examples
    --------
    >>> from masafi_sim_petri import PetriNet, Place
    >>> from masafi_sim_petri.io import element_for, set_graphics, to_element
    >>> net = PetriNet()
    >>> buffer = net.add_place(Place('buffer'))
    >>> root = to_element(net)
    >>> graphics = set_graphics(
    ...     element_for(root, buffer),
    ...     position=(40, 120),
    ...     dimension=(30, 30),
    ...     fill={'color': '#B0D0FF'},
    ...     line={'color': '#204060', 'width': '2'},
    ... )
    >>> [child.tag.rpartition('}')[2] for child in graphics]
    ['position', 'dimension', 'fill', 'line']
    """
    existing = graphics_of(element)
    if existing is not None:
        element.remove(existing)

    graphics = ElementTree.SubElement(element, _tag('graphics'))
    if position is not None:
        ElementTree.SubElement(
            graphics,
            _tag('position'),
            {'x': _number(position[0]), 'y': _number(position[1])},
        )
    if dimension is not None:
        ElementTree.SubElement(
            graphics,
            _tag('dimension'),
            {'x': _number(dimension[0]), 'y': _number(dimension[1])},
        )
    if fill is not None:
        ElementTree.SubElement(graphics, _tag('fill'), dict(fill))
    if line is not None:
        ElementTree.SubElement(graphics, _tag('line'), dict(line))
    return graphics


def graphics_of(
    element: ElementTree.Element,
) -> ElementTree.Element | None:
    """Return the ``graphics`` element of an element, if it has one.

    Parameters
    ----------
    element : xml.etree.ElementTree.Element
        Element to look under.

    Returns
    -------
    xml.etree.ElementTree.Element or None
        The ``graphics`` child, or ``None`` when there is none.

    See Also
    --------
    set_graphics : Write the graphics of an element.
    """
    for child in element:
        if _local_name(child) == 'graphics':
            return child
    return None


def read_pnml(path: str | Path) -> PetriNet:
    """Read a net from a PNML file.

    Parameters
    ----------
    path : str or pathlib.Path
        File to read.

    Returns
    -------
    PetriNet
        The net described by the file, at its initial marking.

    Raises
    ------
    PnmlError
        If the file does not describe a single Place/Transition net.
    OSError
        If the file cannot be read.

    See Also
    --------
    from_pnml : Read a document already held as a string.
    """
    return from_pnml(Path(path).read_text(encoding='utf-8'))


# ----------------------------------------------------------------------
# Internals
# ----------------------------------------------------------------------


def _net_element(root: ElementTree.Element) -> ElementTree.Element:
    """Return the single ``net`` element of a PNML tree.

    Parameters
    ----------
    root : xml.etree.ElementTree.Element
        The ``pnml`` root element.

    Returns
    -------
    xml.etree.ElementTree.Element
        The ``net`` element.

    Raises
    ------
    PnmlError
        If the tree holds no net, or more than one. One tree describes one
        :class:`~masafi_sim_petri.petri_net.petri_net.PetriNet`.
    """
    nets = [child for child in root if _local_name(child) == 'net']
    if not nets:
        raise PnmlError('The document holds no net')
    if len(nets) > 1:
        raise PnmlError(
            f'The document holds {len(nets)} nets, and only a document with '
            'a single net can be read into one PetriNet'
        )
    return nets[0]


def _arc_endpoints(arc: Arc) -> tuple[Place | Transition, Place | Transition]:
    """Return the endpoints of an arc in the direction the tokens move.

    Parameters
    ----------
    arc : Arc
        Arc to read.

    Returns
    -------
    tuple
        The source and the target, which is the order PNML writes them in.
    """
    if arc.is_input:
        return arc.place, arc.transition
    return arc.transition, arc.place


def _number(value: float) -> str:
    """Return a coordinate as PNML text.

    Parameters
    ----------
    value : float
        Coordinate or length.

    Returns
    -------
    str
        The value without a trailing ``.0``, so whole numbers stay readable.
    """
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _tag(name: str) -> str:
    """Return an element name qualified with the PNML namespace.

    Parameters
    ----------
    name : str
        Local name of the element.

    Returns
    -------
    str
        The name in ``{namespace}name`` form, which is how
        :mod:`xml.etree.ElementTree` spells a qualified name.
    """
    return f'{{{PNML_NAMESPACE}}}{name}'


def _local_name(element: ElementTree.Element) -> str:
    """Return the name of an element without its namespace.

    Documents in the wild are not always namespaced, so elements are matched
    on their local name and a missing namespace is tolerated.

    Parameters
    ----------
    element : xml.etree.ElementTree.Element
        Element to name.

    Returns
    -------
    str
        The local name.
    """
    return element.tag.rpartition('}')[2]


def _descendants(
    element: ElementTree.Element, name: str
) -> list[ElementTree.Element]:
    """Return every descendant of an element with the given local name.

    PNML allows the nodes of a net to be spread over nested pages, so nodes
    are collected at any depth rather than only as direct children.

    Parameters
    ----------
    element : xml.etree.ElementTree.Element
        Element to search under.
    name : str
        Local name to match.

    Returns
    -------
    list of xml.etree.ElementTree.Element
        The matching descendants, in document order.
    """
    return [
        descendant
        for descendant in element.iter()
        if _local_name(descendant) == name
    ]


def _append_labelled_text(
    parent: ElementTree.Element, name: str, value: str
) -> None:
    """Append a PNML label carrying a text value.

    A PNML label is an element holding a ``text`` element, which is how names,
    initial markings and arc inscriptions are all written.

    Parameters
    ----------
    parent : xml.etree.ElementTree.Element
        Element to append the label to.
    name : str
        Local name of the label, such as ``'name'`` or ``'initialMarking'``.
    value : str
        Text of the label.
    """
    label = ElementTree.SubElement(parent, _tag(name))
    ElementTree.SubElement(label, _tag('text')).text = value


def _identifier(element: ElementTree.Element, kind: str) -> str:
    """Return the ``id`` of an element.

    Parameters
    ----------
    element : xml.etree.ElementTree.Element
        Element to read.
    kind : str
        What the element is, used in the error message.

    Returns
    -------
    str
        The identifier.

    Raises
    ------
    PnmlError
        If the element has no ``id``, since arcs refer to nodes by it.
    """
    identifier = element.get('id')
    if not identifier:
        raise PnmlError(f'A {kind} element has no id')
    return identifier


def _node_name(element: ElementTree.Element, identifier: str) -> str:
    """Return the name to give a node.

    Parameters
    ----------
    element : xml.etree.ElementTree.Element
        The ``place`` or ``transition`` element.
    identifier : str
        The ``id`` of the element, used when it carries no usable name.

    Returns
    -------
    str
        The text of the ``name`` label when there is one, and the identifier
        otherwise.
    """
    text = _label_text(element, 'name')
    return text if text and text.strip() else identifier


def _label_text(element: ElementTree.Element, name: str) -> str | None:
    """Return the text held by a PNML label of an element.

    Parameters
    ----------
    element : xml.etree.ElementTree.Element
        Element holding the label.
    name : str
        Local name of the label.

    Returns
    -------
    str or None
        The text, or ``None`` when the element has no such label.
    """
    for child in element:
        if _local_name(child) != name:
            continue
        for grandchild in child:
            if _local_name(grandchild) == 'text':
                return grandchild.text
    return None


def _integer_label(
    element: ElementTree.Element, name: str, default: int
) -> int:
    """Return the whole number held by a PNML label.

    Parameters
    ----------
    element : xml.etree.ElementTree.Element
        Element holding the label.
    name : str
        Local name of the label, ``'initialMarking'`` or ``'inscription'``.
    default : int
        Value to use when the label is absent, which is what the standard
        prescribes: no initial marking means no tokens, no inscription means
        a weight of one.

    Returns
    -------
    int
        The value of the label.

    Raises
    ------
    PnmlError
        If the label holds something that is not a whole number.
    """
    text = _label_text(element, name)
    if text is None:
        return default
    try:
        return int(text.strip())
    except ValueError as error:
        identifier = element.get('id', '?')
        raise PnmlError(
            f'The {name} of {identifier!r} is not a whole number: '
            f'{text.strip()!r}'
        ) from error


def _add(
    add: Callable[..., Place | Transition],
    node: Place | Transition,
    identifier: str,
    nodes: dict[str, Place | Transition],
) -> None:
    """Add a node to the net and record it under its PNML identifier.

    Parameters
    ----------
    add : callable
        The ``add_place`` or ``add_transition`` method of the net.
    node : Place or Transition
        Node to add.
    identifier : str
        The ``id`` the document gave it, which is what arcs refer to.
    nodes : dict
        Mapping from identifier to node, filled in as nodes are added.

    Raises
    ------
    PnmlError
        If the identifier is used twice, or if the net refuses the node.
    """
    if identifier in nodes:
        raise PnmlError(f'The identifier {identifier!r} is used twice')
    try:
        add(node)
    except ValueError as error:
        raise PnmlError(f'{identifier!r} cannot be added: {error}') from error
    nodes[identifier] = node


def _endpoint(
    element: ElementTree.Element,
    attribute: str,
    identifier: str,
    nodes: dict[str, Place | Transition],
) -> Place | Transition:
    """Return the node an arc refers to.

    Parameters
    ----------
    element : xml.etree.ElementTree.Element
        The ``arc`` element.
    attribute : str
        ``'source'`` or ``'target'``.
    identifier : str
        The ``id`` of the arc, used in error messages.
    nodes : dict
        Mapping from identifier to node.

    Returns
    -------
    Place or Transition
        The node the attribute refers to.

    Raises
    ------
    PnmlError
        If the attribute is missing, or refers to a node the document does not
        define.
    """
    reference = element.get(attribute)
    if not reference:
        raise PnmlError(f'Arc {identifier!r} has no {attribute}')
    if reference not in nodes:
        raise PnmlError(
            f'Arc {identifier!r} refers to {reference!r}, which the document '
            'does not define'
        )
    return nodes[reference]
