Analysis
========

Simulating a net shows what *did* happen on one run. Analysis answers what
*can* happen on every run, and the two are not the same question: a run that
never deadlocked is not a proof that no deadlock exists.

This section covers the analyses the library implements. It grows one property
at a time, and each one is added only when it can be answered exactly, which
for Petri nets is a real constraint rather than a matter of effort — several
natural questions about unbounded nets are decidable in theory and hopeless in
practice.

.. toctree::
   :maxdepth: 2

   boundedness
