#!/usr/bin/python3

# networkx represents graphs, pydot does conversion to/from graphviz
import networkx as nx
import pydot   
import matplotlib.pyplot as plt

# Basic Graph Definition
#  axiom machine must be S
#  machines are labeled with nonterminals, initial states are marked by a transition from an invisible state named init+NonTerm name, states are names NonTerm + number
#  epsilon moves are labeled "&epsilon;"
#  the tap is denoted as "-\|"

class Node(object):
  def __init__(self, name, label=""):
     self.name=name
     self.label=label
     self.to={}
     self.initial=False
     self.final=False
 
  def add_arc_to(self,name,label=""):
     if name not in self.to : self.to[name]=[label]
     else : self.to[name].append(label)

  def del_arc_to(self,name,label):
     if len(self.to[name])==1 : self.to.remove(name)
     elif len(self.to[name])>1 : self.to[name].remove(label)

  def get_arcs(self):
     return sum([ [ (n, l) for l in self.to[n] ] for n in self.to ],[])

  def __repr__(self):
     res=' '+self.name
     if self.final : res+=' [shape="doublecircle"];\n' 
     else : res+='\n'
     for s in self.to :
        for l in self.to[s] :
          res+=' {} -> {} [label="{}"];\n'.format(self.name,s,l)
     return res

class Machine(object):
   def __init__(self, name):
     self.name=name
     self.nodes=[]

   def get_initial(self):
     for n in self.nodes :
       if n.initial : return n

   def set_initial(self, name):
     for n in self.nodes :
       if n.name == name : n.initial=self.name
     
   def get_final(self):
     return [ n for n in self.nodes if n.final ]

   def set_final(self, name):
     for n in self.nodes :
       if n.name == name : n.final=self.name

   def add_arc(self, nfrom, nto, label=""):
     for n in self.nodes :
       if n.name == nfrom : 
          n.add_arc_to(nto, label)
          return
     #print([ n.name for n in self.nodes ])
     #print([ nfrom, nto ])
     raise KeyError
   
   def del_arc(self, nfrom, nto):
     for n in self.nodes :
       if n.name == nfrom : n.del_arc_to(nto)

   def add_node(self, name, label=""):
     self.nodes.append(Node(name, label))

   def del_node(self, name):
     to_remove = [n for n in self.nodes if n.name==name]
     for n in to_remove:
       self.nodes.remove(n)

   def get_node(self, name):
     return [n for n in self.nodes if n.name==name][0]

   def __repr__(self): 
     res=' init{} [shape="none" style="invis"];\n'.format(self.name)
     for n in self.nodes: 
        res+=repr(n)
     return res + ' init{} -> {}'.format(self.name, self.get_initial().name)

# Importing from Graphviz through networkx

class MachineNet(dict):
  def __init__(self,filename=None):
    self.from_dot(filename) if filename else {}

  def from_dot(self,fname="gram0.dot"):
    G = nx.nx_pydot.read_dot(fname)
    for c in nx.weakly_connected_components(G):
      print(c)
      current = None
      for n in c :
        if 'init' in n :
          M = Machine(n[4:])
          self[n[4:]]=M
          current=n[4:]
      M=self[current] 
      for n in c :
        if 'init' in n : continue
        M.add_node(n)
        try : 
          if G._node[n]['shape'] == '"doublecircle"' : M.set_final(n)
        except KeyError : pass
        for p in G.predecessors(n):
          if 'init' in p : M.set_initial(n)
        for s in G.successors(n):
          for i in range(G.number_of_edges(n,s)):
            M.add_arc(n,s,eval(G.get_edge_data(n,s,i)['label']))

  def to_dot(self,fname="out.dot"):
    res = 'digraph G {\n rankdir="LR";\n node [shape="circle"];\n\n'
    for M in self :
      res+=repr(self[M])+'\n'
    res+='}'
    with open(fname,"w") as fout:
      fout.write(res)

  def get_node(self, name):
    for M in self :
      try : return self[M].get_node(name)
      except Exception: pass
    return name

if __name__ == '__main__': 
  g = "gram0.dot"
  from sys import argv
  if len(argv)>1 : g = argv[-1]
  print(g)
  G = MachineNet(g)
  outname = g.split(".")[0]+'.out.dot'
  G.to_dot(outname)
