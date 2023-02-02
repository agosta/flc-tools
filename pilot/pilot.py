#!/usr/bin/python3

__doc__ = '''This module implements the generation of the LR pilot automaton from a machine net representation of the grammar.
The input machine net is represented by a graphviz dot file. 
See the build_pilot function documentation for more details.

Global variables:
  index  used to provide the numbering of macro-states

(todo: move to Python 3.9 so we can document this)
'''

import mnet as mn
import dot2tex

index = 0


class MachineNetPilot(mn.MachineNet):
  '''Extension of the generic machine net with properties needed to compute the pilot:
  - Computation of the Initials
  - isNullable property'''
  def get_states(self):
    return sum([ self[m].nodes for m in self ],[])

  def get_state(self,name):
    '''Fails if name is not the name of a state; also, all names should be different'''
    return [ n for n in [ self[m].nodes for m in self ] if n.name==name][0]
      
  def isNullable(self, state):
    '''Check whether a state is nullable.
    Note: Epsilon moves are untested!'''
    if state.final : return True
    for n in state.to : 
      if state.to[n]=='&epsilon;' and self.isNullable(n) : return True
    return False

  def compute_initials(self):
    '''Compute initials for a all states'''
    for s in self.get_states():
      self.initials(s)

  def initials(self, state):
    '''Compute and return initials for a single state'''
    print("Ini({})".format(state.name))
    edge_labels_term = [ l for n, l in state.get_arcs() if l not in self.keys() ]
    edge_labels_nonterm = [ l for n, l in state.get_arcs() if l in self.keys() ]
    edges_and_labels_nonterm = [ (n, l) for n, l in state.get_arcs() if l in self.keys() ]
    clause1 = set(edge_labels_term)
    print('--------',[ (s, self[s].get_initial()) for s in edge_labels_nonterm])
    clause2 = set().union(*[ self.initials(self[s].get_initial()) for s in edge_labels_nonterm ])
    clause3 = set([ self.initials(n) for n, s in edges_and_labels_nonterm if self.isNullable(self[s].get_initial()) ])
    state.ini = clause1|clause2|clause3
    return state.ini

  def print_initials(self):
    '''Print out the initials of all states. 
    Note: method compute_initials should be called before calling the print method.'''
    print("Initials")
    for s in self.get_states():
      print("  Ini("+s.name+'): {',end=" ")
      for i in s.ini :
        print(i,end=" ")
      print('}')

class Item(object):
  '''Class representing a candidate or item for the pilot'''
  def __init__(self,state,la):
    self.state=state
    self.la=la

  def __hash__(self):
    return hash((self.state.name, self.la))

  def __eq__(self, other):
    if self.state.name==other.state.name and self.la == other.la : return True
    return False

  def __ne__(self, other):
    return not self.__eq__(other)

  def __lt__(self, other):
    if self.state.name<other.state.name : return 1
    if self.state.name==other.state.name and self.la < other.la : return 1
    return 0

  def __repr__(self):
     name = self.state.name if not self.state.final else '({})'.format(self.state.name)
     return "{}, {}".format(name,self.la)

class MacroState(mn.Node):
  '''Class representing a macro-state, or a set of items, closed under the closure operation. 
  Note: the closure is computed during the initialization'''
  def __init__(self,base, machine_net):
    self.base=set(base)
    self.mn=machine_net
    self.closure=set()
    self.get_closure()
    global index
    self.name="I{}".format(index) #TODO: The index should actually be set only if the macro-state is not merged with another
    index+=1
    self.label=self.name
    self.to={}
    self.initial=False
    self.final=False

  def __hash__(self):
    return hash((tuple(sorted(list(self.base))), tuple(sorted(list(self.closure)))))

  def __eq__(self, other):
    return hash(self)==hash(other)

  def __ne__(self, other):
    return hash(self)!=hash(other)

  def __repr__(self):
    base = '\l'.join([ str(i) for i in self.base])
    clos = '\l'.join([ str(i) for i in self.closure])
    res = ' ' +self.name + ' [xlabel="{}" label="'.format(self.name) + base +"|"+ (clos if len(self.closure) else " ") +'" ];\n'
    for s in self.to :
      for l in self.to[s] :
        res+=' {} -> {} [label="{}"];\n'.format(self.name,s,l)
    return res

  def get_closure(self):
    '''Computes the closure of the macro-state according to the algorithm seen in class.'''
    for item in self.base:
      state=item.state
      la=item.la
      edges_and_labels_nonterm = [ (n, l) for n, l in self.mn.get_node(state).get_arcs() if l in self.mn.keys() ]
      for n, l in edges_and_labels_nonterm :
        node=self.mn.get_node(n)
        print("TEST", state, node, n, l, node.ini, self.mn.isNullable(node), la)
        if self.mn.isNullable(node) :
          self.closure.add(Item(self.mn[l].get_initial(), la))
        for b in node.ini:
          self.closure.add(Item(self.mn[l].get_initial(), b))
    length=len(self.closure)
    while True :
      for item in self.closure :
        state=item.state
        la=item.la
        edges_and_labels_nonterm = [ (n, l) for n, l in state.get_arcs() if l in self.mn.keys() ]
        for n, l in edges_and_labels_nonterm :
          node=self.get_node(n)
          if self.isNullable(node) :
            self.closure.add(Item(self.mn[l].get_initial(), la))
          for b in node.ini():
            self.closure.add(Item(self.mn[l].get_initial(), b))
      if len(self.closure)>length : length=len(self.closure)
      else : return

  def get_nodes(self):
    #print(self.base|self.closure)
    return self.base|self.closure

class Pilot(mn.Machine):
   '''Subclass of Machine used to represent the Pilot. It represents a single graph/automaton, and the nodes must be of type MacroState.'''
   def __init__(self, machine_net):
     self.name='pilot'
     self.mn=machine_net
     self.nodes=[]
     initial_state=MacroState([Item(self.mn['S'].get_initial(),'-\|')],self.mn)
     self.nodes.append(initial_state)
     self.set_initial(initial_state.name)
     self.built=False
     self.built=self.build()

   def update(self,l):
     '''Perform the pilot automaton building step, adding new macro-states'''
     # for each mstate and symbol in alphabet, for which we have a transition (i.e., compute all possible shifts)
     for I in self.nodes[l:] :
       shifts = sum([ [ (item.state, to, label, item.la) for to, label in item.state.get_arcs() ] for item in I.get_nodes() ],[])
       labels = set([ shift[2] for shift in shifts ]) # set of all outgoing labels
       # collect the shifts by label, and build the closure of each macro-state (the latter is done by the macro-state constructor)
       for l in labels :
         new_state=MacroState([ Item(self.mn.get_node(shift[1]), shift[3]) for shift in shifts if shift[2]==l ],self.mn)
         # check if it is a new state, then add it, otherwise add just the arc, to the old state.
         if new_state not in self.nodes:
           self.nodes.append(new_state)
           name=new_state.name
         else :
            for old_state in self.nodes: 
              if new_state == old_state : 
                name=old_state.name
         self.add_arc(I.name,name,l)
                   
   def build(self):
     '''Perform the pilot automaton building loop, up to fixed point'''
     if self.built : return True
     lold=0
     l=len(self.nodes)
     while True:
       self.update(lold)
       lold=l
       print(self)
       if len(self.nodes)>l and l<9 : l=len(self.nodes)
       else : return True

   def __repr__(self): 
     res='digraph P {{\nrankdir="LR";\nnode [shape="record"];\n init{} [shape="none" style="invis"];\n'.format(self.name)
     for n in self.nodes: 
        res+=repr(n)
     return res + ' init{} -> {}'.format(self.name, self.get_initial().name)+'\n}'
  

def basename(s):
  '''Support function for removing the extension from file names'''
  return ".".join(s.split(".")[:-1])

def build_pilot(input_graph="gram0.dot", output_graph="pilot.dot", latex=True):
  '''Driver function for building the pilot out of a graphviz file representing a machine net.
  How to write the graphviz file: 
  - The axiom machine must be named S; machine names are implicit and derived from the state names, which must follow the pattern described below
  - Machines must labeled with nonterminals (a single uppercase letter NonTerm): initial states are marked by a transition from an invisible state named init+NonTerm name, states are names NonTerm + number
  - Epsilon moves must labeled "&epsilon;"
  - Other moves must be labeled with a terminal (a single lowercase letter) or nonterminal (a single uppercase letter that is used as the name of a machine)
  - The tap must be denoted as "-\|"

  Note: the latex output is highly experimental -- i.e., at the moment it just dumps the current version of the dot file into tex via dot2tex. The dot needs to be modified to better support the tex output.
  ''' 
  M = MachineNetPilot(input_graph)
  M.compute_initials()
  M.print_initials()
  pilot=Pilot(M)
  pilot.build()
  with open(output_graph,"w") as fout:
    fout.write(str(pilot))
  if latex: 
    in_graph=''
    with open(input_graph,"r") as fin:
       in_graph=fin.read()
    tex_in = dot2tex.dot2tex(in_graph, format='tikz', crop=True)
    tex_out = dot2tex.dot2tex(str(pilot), format='tikz', crop=True)
    with open(basename(input_graph)+'.tex','w') as fout:
       fout.write(tex_in)
    with open(basename(output_graph)+'.tex','w') as fout:
       fout.write(tex_out)

if __name__ == '__main__':
  g = "gram0.dot"
  from sys import argv
  if len(argv)>1 : g = argv[-1]
  print(g)
  outname = g.split(".")[0]+'.pilot.dot'
  build_pilot(g, outname)
