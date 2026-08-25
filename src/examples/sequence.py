from masafi_sim_petri import PetriNet
from masafi_sim_petri import Place
from masafi_sim_petri import Transition
from masafi_sim_petri import Arc

p1 = Place("P1", initial_marking=3)
p2 = Place("P2", initial_marking=0)
p3 = Place("P3", initial_marking=0)
t1 = Transition("T1")
t2 = Transition("T2")
t3 = Transition("T3")
a1 = Arc(p1, t1)
a2 = Arc(t1, p2)
a3 = Arc(p2, t2)
a4 = Arc(t2, p3)
a5 = Arc(p3, t3)
net = PetriNet(
    places=[p1, p2, p3],
    transitions=[t1, t2, t3],
    arcs=[a1, a2, a3, a4, a5],
)

print(net)
print(net.marking)
net.fire(t1)
print(net.marking)
net.fire(t2)
print(net.marking)
net.fire(t3)
print(net.marking)
net.fire(t1)
print(net.marking)
net.fire(t1)
print(net.marking)
net.fire(t2)
print(net.marking)



