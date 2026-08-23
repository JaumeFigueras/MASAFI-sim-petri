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

What is not written
-------------------

**The current marking.** PNML records the initial marking, so a net that has
been run and then saved is saved in the state it started from, and a net read
back is always at its initial marking. This is the standard's design, not an
omission: a PNML file describes a net, not a moment in a simulation. Saving a
run in progress would need an extension, and there is a defined way to add one
— see below.

**Graphics.** PNML has a ``graphics`` element for positions, colours and line
styles. The model deliberately holds no layout data, so none is written. When
the editor needs its layout preserved, the natural design is for the serialiser
to carry ``graphics`` elements through a load and save unchanged, without the
model ever growing an ``x`` and a ``y``.

Extending it later
------------------

PNML's escape hatch is the ``toolspecific`` element, which conforming tools
ignore when they do not recognise the tool. That is where timing information
will go for timed nets, and it is why a timed net will still be readable — as
an untimed net — by a tool that knows nothing about this library.

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
