MASAFI Sim Petri
================

Petri nets for discrete event simulation.

This library models, simulates and analyses Petri nets. It is a library only:
the graphical editor used to draw the nets is a separate application that
imports this package.

Four classes of net are planned, each building on the previous one:

======================  ==========================================  ==========
Net class               Adds                                        Status
======================  ==========================================  ==========
Place/Transition        The base model: places, transitions, arcs   In progress
Timed                   A notion of time, driven by SimPy           Planned
Coloured                Tokens that carry a value                   Planned
Coloured Timed          Both of the above                           Planned
======================  ==========================================  ==========

Installation
------------

.. code-block:: bash

   pip install -e ".[dev,docs]"

.. toctree::
   :maxdepth: 2
   :caption: User guide

   ptpn/index
   io/index

.. toctree::
   :maxdepth: 2
   :caption: API reference

   api/modules
