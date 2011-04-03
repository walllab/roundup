'''
module for construction of a weighted network/graph.
nodes are genes in a genome.
edges are the association/weight/distance between genes based on phylogenetic profiles of those genes derived from Roundup orthology data.
'''

# genomes -> clusters/genes
# clusters -> profiles
# profiles -> gene-gene association
# clusters -> gene ids

import orthology_query

def foo(genomes):
    print orthology_query.doOrthologyQuery(genomes=genomes)

if __name__ == '__main__':
    pass

# last line python mode emacs bug fix.
