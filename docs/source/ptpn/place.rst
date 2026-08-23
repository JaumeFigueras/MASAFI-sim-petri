The Place class
===============

.. currentmodule:: masafi_sim_petri.petri_net.place

A place holds tokens. In a P/T net that is all it does, and the class is
deliberately no larger than that.

:class:`Place` is created with a name and,
optionally, the number of tokens it starts with:

.. code-block:: python

   from masafi_sim_petri import Place

   buffer = Place('buffer', initial_marking=2)

Initial and current marking
---------------------------

A place carries two numbers, and the distinction matters more than it first
appears.

:attr:`Place.initial_marking`
   The marking the place starts from. It is fixed at construction and never
   changes.

:attr:`Place.marking`
   The marking right now. It changes as transitions fire.

The initial marking is kept because it is needed twice over. A simulation that
is run repeatedly — to compare policies, or to gather statistics — must return
the net to its starting state between runs, and :meth:`~Place.reset`
is what does that. Reachability analysis needs it for a different reason: the
initial marking :math:`M_0` is the root of the reachability graph, so a net
that cannot state where it began cannot be analysed at all.

.. doctest::

   >>> from masafi_sim_petri import Place
   >>> buffer = Place('buffer', initial_marking=2)
   >>> buffer.remove_tokens(2)
   >>> buffer.marking
   0
   >>> buffer.reset()
   >>> buffer.marking
   2

Asking, then taking
-------------------

Three methods make up the working interface, and they come in a deliberate
order:

:meth:`~Place.has_tokens`
   Does this place hold at least ``count`` tokens? A pure query. This is the
   enabling test: before a transition fires, each of its input places is asked
   whether it can supply the weight of the arc that connects them.

:meth:`~Place.remove_tokens`
   Take ``count`` tokens out. Used when a transition consumes its inputs.

:meth:`~Place.add_tokens`
   Put ``count`` tokens in. Used when a transition produces its outputs.

Removing more tokens than the place holds raises :exc:`ValueError` rather than
emptying the place or clamping at zero. This is a guard, not a control flow:
the caller is expected to have asked :meth:`~Place.has_tokens` first, so a
failure here
means the firing rule skipped its enabling test. Failing loudly at the point of
the mistake is worth more than a marking that silently drifts.

.. doctest::

   >>> buffer = Place('buffer', initial_marking=1)
   >>> buffer.has_tokens(2)
   False
   >>> buffer.remove_tokens(2)
   Traceback (most recent call last):
       ...
   ValueError: Cannot remove 2 tokens from place 'buffer', which holds 1

Why methods rather than arithmetic
----------------------------------

:attr:`Place.marking` is a plain integer, so ``place.marking -= 1`` would work.
The methods exist anyway, and the reason is the nets that come later.

In a coloured net a place holds tokens that carry values, and the question
"does this place have two tokens?" becomes "does this place have two tokens *of
this colour*?". A coloured place answers that by overriding
:meth:`~Place.has_tokens`, :meth:`~Place.remove_tokens` and
:meth:`~Place.add_tokens` — the three methods widen, while
:attr:`Place.marking` keeps meaning exactly what it means here: the total
number of tokens. Every rule written against the base class stays true of the
subclass.

If the rest of the library manipulated :attr:`Place.marking` arithmetically
instead, that
extension point would not exist, and coloured nets would need a parallel
implementation of the firing rule.

Assigning a marking directly
----------------------------

:attr:`Place.marking` can also be assigned, and the assignment is validated so
that it can never go negative:

.. doctest::

   >>> buffer = Place('buffer')
   >>> buffer.marking = 5
   >>> buffer.marking
   5
   >>> buffer.marking = -1
   Traceback (most recent call last):
       ...
   ValueError: The marking of a place cannot be negative, got -1

This bypasses the firing rule on purpose. Reachability analysis explores
markings out of order: having reached a marking, examined its successors and
moved on, it must be able to put the net back into an earlier marking to
continue from there. Replaying every firing from :math:`M_0` each time would be
correct but needlessly expensive, so the analysis restores markings by
assignment.

For ordinary simulation, use the three methods. Assignment is for code that is
managing the state space itself.

What a place does not have
--------------------------

Several things are absent by design.

**No capacity.** Places are unbounded, so there is no capacity attribute and no
check against one. Boundedness is a property to be analysed, not a constraint
to be imposed.

**No arcs.** A place does not know what is connected to it. The net owns the
connectivity, which keeps the object graph free of cycles, lets a place be
tested entirely on its own, and leaves one source of truth for the topology.
To ask what is attached to a place, ask the net.

**No token objects.** A P/T marking is a count. The
:class:`~masafi_sim_petri.petri_net.token.Token` class becomes meaningful only
for coloured nets.

**No layout or display data.** No coordinates, no colour, no arbitrary metadata
dictionary. The graphical editor is a separate application and keeps its own
view model; the library models the net, not the drawing of it.

Naming
------

A place is named at construction, and :attr:`Place.name` cannot be assigned
afterwards. The net indexes its places by name, so a place that renamed itself
would leave that index stale.

Renaming a place that belongs to a net goes through the net:

.. code-block:: python

   net.rename_place(place, 'new_name')

See :ref:`renaming` for what that guarantees — in particular that the order of
the places, and therefore the meaning of the marking vector, is unaffected.

Full API
--------

Every method, with its parameters and the exceptions it raises, is in the
:doc:`API reference </api/masafi_sim_petri.petri_net.place>`.
