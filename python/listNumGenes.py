#! /usr/bin/python

'''
This script lists the names of organisms in Prod genomes
and the number of proteins in each genome
'''

# by Jike Cui

import os
dir = "/groups/rodeo/roundup/genomes/current/"

for f in  os.listdir(dir):
    fileName=dir+f+"/"+f
    iFile = open(fileName, 'r')
    protNum = 0
    for aline in iFile:
        aline=aline.strip()
        if aline:
            if aline.rfind(">")==0:
                protNum+=1
    iFile.close()

    print f+"\t"+str(protNum)
