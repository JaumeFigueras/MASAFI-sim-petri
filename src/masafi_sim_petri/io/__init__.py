"""Reading and writing Petri nets in interchange formats.

Serialisation lives outside the model: these functions build a net through its
public interface and read one the same way, so the model classes never depend
on a file format.
"""

from masafi_sim_petri.io.pnml import (
    PNML_NAMESPACE,
    PT_NET_TYPE,
    PnmlError,
    from_pnml,
    read_pnml,
    to_pnml,
    write_pnml,
)

__all__: list[str] = [
    'PNML_NAMESPACE',
    'PT_NET_TYPE',
    'PnmlError',
    'from_pnml',
    'read_pnml',
    'to_pnml',
    'write_pnml',
]
