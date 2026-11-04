"""Topology gate for meshes intended to be closed building shells, not roads."""
from collections import Counter
import math

def closed_shell_report(points,counts,indices,tolerance_m=.0001):
    if not math.isfinite(tolerance_m) or tolerance_m<=0:raise ValueError('Invalid weld tolerance')
    if sum(counts)!=len(indices) or any(n<3 for n in counts):raise ValueError('Invalid face index layout')
    if not points or any(len(p)!=3 or not all(math.isfinite(float(v)) for v in p) for p in points):raise ValueError('Invalid mesh points')
    if any(i<0 or i>=len(points) for i in indices):raise ValueError('Index outside mesh')
    vertices=[tuple(round(float(v)/tolerance_m) for v in p) for p in points]
    undirected=Counter();directed=Counter();collapsed=0;offset=0
    for count in counts:
        ring=[vertices[i] for i in indices[offset:offset+count]];offset+=count
        for a,b in zip(ring,ring[1:]+ring[:1]):
            if a==b:collapsed+=1;continue
            undirected[tuple(sorted((a,b)))]+=1;directed[(a,b)]+=1
    boundary=sum(n==1 for n in undirected.values());nonmanifold=sum(n>2 for n in undirected.values())
    orientation=sum(n==2 and (directed[(a,b)]!=1 or directed[(b,a)]!=1) for (a,b),n in undirected.items())
    return {'weld_tolerance_m':tolerance_m,'edge_count':len(undirected),'boundary_edges':boundary,'nonmanifold_edges':nonmanifold,'inconsistent_edge_orientation':orientation,'collapsed_edges':collapsed,'passed_closed_shell':bool(undirected) and not any([boundary,nonmanifold,orientation,collapsed]),'limits':'Edge-incidence gate only; does not establish self-intersection freedom, geographic accuracy or architectural correctness.'}
