"""Petri net modelling, simulation and analysis.

This package models and simulates Petri nets. It is a library only: the
graphical editor that builds the nets is a separate application that imports
this package.

The public API is re-exported here so that consumer projects can import the
names they need directly from :mod:`masafi_sim_petri`, without depending on
the internal module layout.

Subpackages
-----------
petri_net
    The net model itself: places, transitions, arcs and tokens.
analysis
    Analysis over a net, such as the reachability graph.
simulation
    Execution engines: a state stepper for untimed nets and a SimPy-based
    engine for timed nets.
"""

from importlib.metadata import PackageNotFoundError, version

from masafi_sim_petri.petri_net.arc import Arc
from masafi_sim_petri.petri_net.petri_net import PetriNet
from masafi_sim_petri.petri_net.place import Place
from masafi_sim_petri.petri_net.transition import Transition

try:
    __version__: str = version("masafi-sim-petri")
except PackageNotFoundError:  # pragma: no cover - only when not installed
    __version__ = "0.0.0"

__all__: list[str] = ['Arc', 'PetriNet', 'Place', 'Transition', '__version__']
