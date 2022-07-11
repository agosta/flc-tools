#!/usr/bin/python3

import mnet as mn
index = 0

class MachineNetPilot(mn.MachineNet):
  def get_states(self):
    return sum([ self[m].nodes for m in self ],[])

  def get_state(self,name):
    '''Fails if name is not the name of a state; also, all names should be different'''
    return [ n for n in [ self[m].nodes for m in self ] if n.name==name][0]
      
  def isNullable(self, state):
    '''Epsilon moves are untested!'''
    if state.final : return True
    for n in state.to : 
      if state.to[n]=='&epsilon;' and self.isNullable(n) : return True
    return False

  def compute_initials(self):
    for s in self.get_states():
      self.initials(s)

  def initials(self, state):
    #print("Ini({})".format(state.name))
    edge_labels_term = [ l for n, l in state.get_arcs() if l not in self.keys() ]
    edge_labels_nonterm = [ l for n, l in state.get_arcs() if l in self.keys() ]
    edges_and_labels_nonterm = [ (n, l) for n, l in state.get_arcs() if l in self.keys() ]
    clause1 = set(edge_labels_term)
    clause2 = set().union(*[ self.initials(self[s].get_initial()) for s in edge_labels_nonterm ])
    clause3 = set([ self.initials(n) for n, s in edges_and_labels_nonterm if self.isNullable(self[s].get_initial()) ])
    state.ini = clause1|clause2|clause3
    return state.ini

  def print_initials(self):
    print("Initials")
    for s in self.get_states():
      print("  Ini("+s.name+'): {',end=" ")
      for i in s.ini :
        print(i,end=" ")
      print('}')

class Item(object):
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
  def __init__(self,base, machine_net):
    self.base=set(base)
    self.mn=machine_net
    self.closure=set()
    self.get_closure()
    global index
    self.name="I{}".format(index)
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
    for item in self.base:
      state=item.state
      la=item.la
      edges_and_labels_nonterm = [ (n, l) for n, l in self.mn.get_node(state).get_arcs() if l in self.mn.keys() ]
      for n, l in edges_and_labels_nonterm :
        n=self.mn.get_node(n)
        if self.mn.isNullable(n) :
          self.closure.add(Item(self.mn[l].get_initial(), la))
        else :
          for b in n.ini:
            self.closure.add(Item(self.mn[l].get_initial(), b))
    length=len(self.closure)
    while True :
      for item in self.closure :
        state=item.state
        la=item.la
        edges_and_labels_nonterm = [ (n, l) for n, l in state.get_arcs() if l in self.mn.keys() ]
        for n, l in edges_and_labels_nonterm :
          n=self.get_node(n)
          if self.isNullable(n) :
            self.closure.add(Item(self.mn[l].get_initial(), la))
          else :
            for b in n.ini():
              self.closure.add(Item(self.mn[l].get_initial(), b))
      if len(self.closure)>length : length=len(self.closure)
      else : return

  def get_nodes(self):
    #print(self.base|self.closure)
    return self.base|self.closure

class Pilot(mn.Machine):
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
  

if __name__ == '__main__':
  M = MachineNetPilot("gram0.dot")
  M.compute_initials()
  M.print_initials()
  pilot=Pilot(M)
  pilot.build()
  with open("pilot.dot","w") as fout:
    fout.write(str(pilot))

