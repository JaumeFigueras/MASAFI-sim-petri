"""Reading and writing Petri nets in interchange formats.

Serialisation lives outside the model: these functions build a net through its
public interface and read one the same way, so the model classes never depend
on a file format.

Two levels are offered. The document level -- :func:`~.pnml.to_pnml`,
:func:`~.pnml.from_pnml`, :func:`~.pnml.write_pnml`, :func:`~.pnml.read_pnml`
-- is for when only the net matters. The tree level --
:func:`~.pnml.to_element`, :func:`~.pnml.from_element`,
:func:`~.pnml.pnml_to_element`, :func:`~.pnml.element_to_pnml` -- exposes the
XML itself, so a project built on this library can carry data the model does
not hold, such as the positions and colours a graphical editor needs.
"""

from masafi_sim_petri.io.pnml import (
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

__all__: list[str] = [
    'PNML_NAMESPACE',
    'PT_NET_TYPE',
    'PnmlError',
    'element_for',
    'element_to_pnml',
    'from_element',
    'from_pnml',
    'graphics_of',
    'nodes_by_element',
    'pnml_to_element',
    'qname',
    'read_pnml',
    'set_graphics',
    'to_element',
    'to_pnml',
    'write_pnml',
]
