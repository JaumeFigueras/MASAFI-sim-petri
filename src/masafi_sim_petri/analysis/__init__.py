"""Analysis over a Petri net.

Structural and behavioural analysis, such as the reachability tree.
"""

from masafi_sim_petri.analysis.boundedness import (
    is_bounded,
    is_k_bounded,
    is_safe,
)
from masafi_sim_petri.analysis.conservation import is_strictly_conservative
from masafi_sim_petri.analysis.reachability_tree import (
    NodeLabel,
    ReachabilityTree,
    ReachabilityTreeNode,
    UnboundedNetError,
)

__all__: list[str] = [
    'NodeLabel',
    'ReachabilityTree',
    'ReachabilityTreeNode',
    'UnboundedNetError',
    'is_bounded',
    'is_k_bounded',
    'is_safe',
    'is_strictly_conservative',
]
