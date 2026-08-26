"""Analysis over a Petri net.

Structural and behavioural analysis, such as the reachability graph.
"""

from masafi_sim_petri.analysis.boundedness import is_k_bounded, is_safe

__all__: list[str] = ['is_k_bounded', 'is_safe']
