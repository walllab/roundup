#!/usr/bin/env python

'''
to use this code after deployment (ant in a computing node)
the following command should be in one line
To use in dev code dir:
ROUNDUP_MYSQL_SERVER=mysql.cl.med.harvard.edu ROUNDUP_MYSQL_DB=roundup bsub -q cbmi_2h -o /home/jc280/ppla/getPhylogeneticMatrix.log /home/td23/bin/python getPhylogeneticMatrix.py '/home/jc280/ppla/query182' '/home/jc280/ppla/ppmatrix182.5.5' 1e-5 0.5

if there are too many genomes, the program requires large RAM. Use this:
ROUNDUP_MYSQL_SERVER=mysql.cl.med.harvard.edu ROUNDUP_MYSQL_DB=roundup bsub -q shared_7d -R "mem > 30000" -o /home/jc280/ppla/tmp.log  /home/td23/bin/python getPhylogeneticMatrix.py /home/jc280/ppla/query182 /home/jc280/ppla/ppmatrix182

To use in prod code dir:
bsub -q cbmi_2h -o /home/jc280/repos/ppla/log.tmp /home/td23/bin/python getPhylogeneticMatrix.py '/home/jc280/repos/ppla/query182' '/home/jc280/repos/ppla/ppmatrix.new.182.20.0.2.Ecoli.only'
'''

import orthology_query
import format_orthology_cluster_result
import re
import sys

if len(sys.argv)<2:
    print "Usage: queryFileName ppmatrixFileName Evalue(optional) divergence(optional)"
    sys.exit()

queryFileName=sys.argv[1]
ppmatrixFileName=sys.argv[2]

sp=re.compile('[=#]')
reps={'None':None,'y':True,'n':False}
f=lambda x: x.strip()
param={}
iFile = open(queryFileName, 'r')
for line in iFile:
    line=line.strip()
    if line and line.find("#")!=0:
        line=line.replace(' ','')
        tmpList=map(f,sp.split(line))
        if tmpList[1] in reps:
            param[tmpList[0]]=reps[tmpList[1]]
        else:param[tmpList[0]]=tmpList[1]
iFile.close()

param['genomes']=param['genomes'].split(',')
if len(sys.argv)==5:
    param['evalue']=sys.argv[3]
    param['divergence']=sys.argv[4]

resultDict=orthology_query.doOrthologyQuery4(**param)
format_orthology_cluster_result.clusterResultToPhylogeneticProfileWithoutCaching_wGiID_3_newClustering(resultDict,ppmatrixFileName)

