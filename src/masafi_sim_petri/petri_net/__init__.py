"""The Petri net model.

Places, transitions, arcs and tokens, plus the net that holds them.
"""

from masafi_sim_petri.petri_net.place import Place
from masafi_sim_petri.petri_net.transition import Transition

__all__: list[str] = ['Place', 'Transition']
