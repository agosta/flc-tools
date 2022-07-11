## Pilot Automaton Construction
 * Builds the pilot automaton from the machine net model of the language

## Basic Graph Definition
 *  axiom machine must be __S__
 *  machines are labeled with nonterminals, initial states are marked by a transition from an invisible state named init+NonTerm name (e.g., __initS__), states are names NonTerm + number (e.g., __S1__)
 *  epsilon moves are labeled __&epsilon;__
 *  the tap is denoted as __-\|__
