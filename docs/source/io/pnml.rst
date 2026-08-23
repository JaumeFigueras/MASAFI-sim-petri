PNML
====

.. currentmodule:: masafi_sim_petri.io.pnml

PNML, the Petri Net Markup Language, is the interchange format for Petri nets,
standardised as **ISO/IEC 15909-2**. It is the format this library reads and
writes.

.. doctest::

   >>> from masafi_sim_petri import Arc, PetriNet, Place, Transition
   >>> from masafi_sim_petri.io import to_pnml, from_pnml
   >>> net = PetriNet()
   >>> waiting = net.add_place(Place('waiting', initial_marking=2))
   >>> serve = net.add_transition(Transition('serve'))
   >>> _ = net.add_arc(Arc(waiting, serve))
   >>> restored = from_pnml(to_pnml(net))
   >>> restored.marking
   (2,)

Why a standard and not our own format
-------------------------------------

Inventing a format would have been quicker. Using PNML buys three things that
a private format cannot.

**Other tools read it.** TINA, LoLA, PIPE, WoPeD, Renew and the Model Checking
Contest all speak PNML. A net built in your editor can be handed to a model
checker that this library will never contain, and a net from elsewhere can be
brought in.

**It is already designed.** The awkward questions — how to represent a marking,
where a name goes, how tools add data without breaking each other — were
settled by people who had solved them before, and reviewed through an ISO
process.

**Free models to test against.** The Model Checking Contest publishes a large
public corpus of benchmark nets in PNML, including nets far larger and stranger
than anything one would write by hand.

The ISO documents themselves must be bought, but the format does not depend on
them: the RELAX NG grammars and the type definitions are published openly at
`pnml.org <https://www.pnml.org/version-2009/version-2009.php>`_, and this
implementation was written from them.

The shape of a document
-----------------------

PNML has a *core model* shared by every kind of Petri net, and a separate
grammar — a **Petri net type definition**, named by a URI — for the features
particular to one kind. This library implements the Place/Transition type,
:data:`PT_NET_TYPE`.

.. doctest::

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
         <transition id="serve">
           <name>
             <text>serve</text>
           </name>
         </transition>
         <arc id="arc1" source="waiting" target="serve" />
       </page>
     </net>
   </pnml>

The mapping onto our model is close to exact, which is a good sign for both:

=========================  ===============================================
PNML                       Model
=========================  ===============================================
``initialMarking``         :attr:`~masafi_sim_petri.petri_net.place.Place.initial_marking`
``inscription``            :attr:`~masafi_sim_petri.petri_net.arc.Arc.weight`
``source`` / ``target``    the endpoints of an :class:`~masafi_sim_petri.petri_net.arc.Arc`
``type``                   the class of net, here Place/Transition
=========================  ===============================================

Bipartiteness is not stated anywhere in the document. It is implied by which
element each ``source`` and ``target`` refers to, and checked when the arc is
built.

Defaults are omitted
~~~~~~~~~~~~~~~~~~~~

The standard says an absent ``initialMarking`` means no tokens and an absent
``inscription`` means a weight of one, so the writer leaves both out when they
would say nothing. The reader accepts either form:

.. doctest::

   >>> 'inscription' in to_pnml(net)
   False
   >>> from_pnml(to_pnml(net)).arcs[0].weight
   1

Identifier and name
~~~~~~~~~~~~~~~~~~~

PNML separates the ``id``, which arcs refer to, from the ``name`` label, which
is what a person reads. Our model has only a name, so:

* **Writing** puts the name in both.
* **Reading** names a node after its ``name`` label when it has a usable one,
  and after its ``id`` otherwise. Arcs are always resolved through the ``id``.

That second rule is what lets a document from another editor come in with
readable names rather than identifiers like ``n17``:

.. doctest::

   >>> document = '''<pnml>
   ...   <net id="n1" type="http://www.pnml.org/version-2009/grammar/ptnet">
   ...     <page id="p1">
   ...       <place id="n17"><name><text>buffer</text></name></place>
   ...     </page>
   ...   </net>
   ... </pnml>'''
   >>> from_pnml(document).place('buffer').name
   'buffer'

If two nodes carry the same name the net refuses the second, since names
identify a node within a net. That is reported as a
:class:`PnmlError` naming the document's own identifier, so the offending
element can be found.

What the model does not hold
----------------------------

**The current marking.** PNML records the initial marking, so a net that has
been run and then saved is saved in the state it started from, and a net read
back is always at its initial marking. This is the standard's design, not an
omission: a PNML file describes a net, not a moment in a simulation.

**Graphics.** PNML has a ``graphics`` element for positions, sizes, colours and
line styles. The model deliberately holds no layout data — the editor is a
separate application and keeps its own view model. But the *document* has a
defined place for it, which is why the next section exists.

.. _tree-level:

Working with the tree
---------------------

This library is one part of a larger system. A graphical editor built on top of
it has to save things the model does not know about: where each place sits on
the canvas, what colour it is, whatever else that application needs. If the only
way in and out were a string, that data would have nowhere to live.

So serialisation is offered at two levels.

**The document level** — :func:`to_pnml`, :func:`from_pnml`, :func:`write_pnml`,
:func:`read_pnml` — is for when only the net matters.

**The tree level** — :func:`to_element`, :func:`from_element`,
:func:`pnml_to_element`, :func:`element_to_pnml` — hands over the
:mod:`xml.etree.ElementTree` document itself. The document-level functions are
thin wrappers over these, so the two can be mixed freely.

Saving with a layout
~~~~~~~~~~~~~~~~~~~~

Build the tree from the net, decorate it, then serialise:

.. doctest::

   >>> from masafi_sim_petri import Arc, PetriNet, Place, Transition
   >>> from masafi_sim_petri.io import (
   ...     element_for, element_to_pnml, set_graphics, to_element,
   ... )
   >>> net = PetriNet()
   >>> buffer = net.add_place(Place('buffer', initial_marking=1))
   >>> take = net.add_transition(Transition('take'))
   >>> arc = net.add_arc(Arc(buffer, take))
   >>> root = to_element(net)
   >>> _ = set_graphics(
   ...     element_for(root, buffer),
   ...     position=(40, 120),
   ...     dimension=(30, 30),
   ...     fill={'color': '#B0D0FF'},
   ... )
   >>> _ = set_graphics(element_for(root, take), position=(140, 120))
   >>> document = element_to_pnml(root)
   >>> '<position x="40" y="120" />' in document
   True

:func:`element_for` is what connects the two worlds: give it a
:class:`~masafi_sim_petri.petri_net.place.Place`,
:class:`~masafi_sim_petri.petri_net.transition.Transition` or
:class:`~masafi_sim_petri.petri_net.arc.Arc` from the net and it returns the
element that stands for it. Arcs are matched on their two endpoints rather than
on an identifier, since the model does not name arcs — and because a net never
holds two arcs joining the same pair the same way round, that is unambiguous.
The two halves of a self loop are two distinct elements.

Loading a layout back
~~~~~~~~~~~~~~~~~~~~~

Parse once, then take the model and the decoration from the same tree:

.. doctest::

   >>> from masafi_sim_petri.io import (
   ...     from_element, graphics_of, nodes_by_element, pnml_to_element,
   ... )
   >>> root = pnml_to_element(document)
   >>> restored = from_element(root)
   >>> restored.marking
   (1,)

:func:`nodes_by_element` says which element produced which node, which is what
lets the decoration be attached to the right object:

.. doctest::

   >>> for element, node in nodes_by_element(root, restored).items():
   ...     graphics = graphics_of(element)
   ...     if graphics is not None:
   ...         print(node.name, graphics[0].attrib)
   buffer {'x': '40', 'y': '120'}
   take {'x': '140', 'y': '120'}

The ``id`` alone could not answer that. A node is named after its ``name``
label when it has one, so in a document from another editor the ``id`` may be
``n17`` while the node is called ``buffer``. The mapping is positional instead,
which is exact: nodes are read in document order and written in net order, so
the correspondence holds whichever way the tree was made.

:func:`from_element` ignores everything it does not understand rather than
discarding it — ``graphics``, ``toolspecific`` and anything else stay in the
tree for the caller to read. That is the whole point of splitting the two
levels: the model gets what it can use, the application keeps the rest, and
neither has to know about the other.

Where view data belongs
~~~~~~~~~~~~~~~~~~~~~~~

The model holds no graphics, and it should not: the same net may be drawn by
more than one application, and each will want to draw it differently. A net is
also frequently used with no display at all — analysed in a test suite,
simulated on a server.

The pattern that follows from this is a **side table in the application, keyed
by the node object**:

.. code-block:: python

   @dataclass
   class NodeView:
       x: float
       y: float
       fill: str = '#FFFFFF'

   class NetDocument:
       def __init__(self) -> None:
           self.net = PetriNet()
           self.views: dict[Place | Transition | Arc, NodeView] = {}

       def add_place(self, name: str, x: float, y: float) -> Place:
           place = self.net.add_place(Place(name))
           self.views[place] = NodeView(x, y)
           return place

Keying by the object rather than by the name is what makes this hold together.
Renaming a node goes through the net and does not touch the view table at all,
because the key is the object and the object has not changed. A table keyed by
name would have to be updated in step with every rename, and would go stale the
first time that was forgotten.

Subclassing :class:`~masafi_sim_petri.petri_net.place.Place` to add coordinates
looks tempting and works while a net is being built — the model checks node
kinds with :func:`isinstance`, so subclasses are accepted. It comes apart on
loading: :func:`from_element` constructs base-class nodes, so an opened file
yields a net with nowhere to put the graphics read from the same document. It
also ties a net to a single view, which rules out two applications displaying
one live net in their own ways.

Adding your own elements
~~~~~~~~~~~~~~~~~~~~~~~~

:func:`set_graphics` covers what the standard defines for appearance. For
anything else, add elements directly — :func:`qname` supplies the namespace so
it need never be written out:

.. code-block:: python

   import xml.etree.ElementTree as ElementTree
   from masafi_sim_petri.io import element_for, qname, to_element

   root = to_element(net)
   tool = ElementTree.SubElement(
       element_for(root, place),
       qname('toolspecific'),
       {'tool': 'MASAFI-SimTwin', 'version': '1.0'},
   )

``toolspecific`` is the standard's escape hatch: a conforming tool that does not
recognise the ``tool`` attribute ignores the element rather than refusing the
file. It is where anything outside the standard belongs — including, later, the
timing of a timed net.

Extending it later
------------------

Timing information for timed nets will go in ``toolspecific``, which is why a
timed net will still be readable — as an untimed net — by a tool that knows
nothing about this library.

Inhibitor arcs are better provided for: ``pnml.org`` publishes a type
definition for inhibitor nets, and ISO/IEC 15909-3 defines their semantics
formally, so they will be a change of net type rather than a private extension.

Reading documents you did not write
-----------------------------------

The reader is deliberately tolerant of things that do not change meaning, and
strict about things that do.

Tolerated: a missing namespace, nodes spread over nested pages, whitespace
around numbers, missing optional labels, and nodes declared in any order.

Refused, each with a message naming the element at fault: XML that is not
well-formed, a root element that is not ``pnml``, a document holding no net or
more than one, a net type other than Place/Transition, a repeated identifier,
an arc referring to a node that is not defined, an arc joining two places, and
any value the model itself would reject such as a negative marking or a weight
below one.

.. doctest::

   >>> from masafi_sim_petri.io import PnmlError
   >>> try:
   ...     from_pnml('<graphml/>')
   ... except PnmlError as error:
   ...     print(error)
   The root element of a PNML document must be 'pnml', got 'graphml'

.. warning::

   Parsing uses :mod:`xml.etree.ElementTree`, which is not hardened against
   maliciously constructed XML. A document from an untrusted source should be
   parsed with a hardened parser such as ``defusedxml``.

Full API
--------

Every function, with its parameters and the exceptions it raises, is in the
:doc:`API reference </api/masafi_sim_petri.io.pnml>`.
