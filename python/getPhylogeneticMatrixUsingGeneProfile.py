#! /home/jc280/Python-2.6.4/python 
from ppla import GeneProfile

gp = GeneProfile()
gp.getProfileFromRoundup('/home/jc280/ppla/query')
gp.writeProfileToFile('/home/jc280/ppla/ppmatrix')
