'''
module for running roundup computations on the cloud.

This module defines command lines to be used in blastmapper and roundupmapper files.

blastrunner commands would look like:
python -c 'import roundup_cloud; roundup_cloud.blast(queryFastaPath="./genomes/genomes/Acaryochloris_marina_MBIC11017.aa/Acaryochloris_marina_MBIC11017.aa", subjectDbPath="./genomes/genomes/Staphylococcus_aureus_USA300_TCH1516.aa/Staphylococcus_aureus_USA300_TCH1516.aa", outPath="./blastinput/blastinput/Acaryochloris_marina_MBIC11017.aa_Staphylococcus_aureus_USA300_TCH1516.aa_blast_hits_f", evalue="1e-5")'

rounduprunner commmands would look like:
python -c 'import roundup_cloud, roundup_common; divEvalueAndOutfiles = [(div, evalue, "./result/result/Acaryochloris_marina_MBIC11017.aa_Staphylococcus_aureus_USA300_TCH1516.aa_"+div+"_"+evalue) for div, evalue in roundup_common.genDivEvalueParams()]; roundup_cloud.roundup(queryFastaPath="./genomes/genomes/Acaryochloris_marina_MBIC11017.aa/Acaryochloris_marina_MBIC11017.aa", subjectFastaPath="./genomes/genomes/Staphylococcus_aureus_USA300_TCH1516.aa/Staphylococcus_aureus_USA300_TCH1516.aa", divEvalueAndOutfileList=divEvalueAndOutfiles, forwardhits="./blastinput/blastinput/Acaryochloris_marina_MBIC11017.aa_Staphylococcus_aureus_USA300_TCH1516.aa_blast_hits_f", reversehits="./blastinput/blastinput/Acaryochloris_marina_MBIC11017.aa_Staphylococcus_aureus_USA300_TCH1516.aa_blast_hits_r")'
'''


import os

import blast_results_db
import RoundUp


def blast(*args, **keywords):
    # do files need to be copied from s3 to here first?
    outPath = keywords['outPath']
    blast_results_db.computeBlastHits(*args, **keywords)
    os.system('/home/hadoop/bin/hadoop fs -copyFromLocal %s s3n://rsdblasttest/output/'%outPath)


def roundup(*args, **keywords):
    # do files need to be copied from s3 to here first?
    divEvalueAndOutfileList = keywords['divEvalueAndOutfileList']
    RoundUp.roundup(*args, **keywords)
    for div, evalue, outPath in divEvalueAndOutfileList:
        os.system('/home/hadoop/bin/hadoop fs -copyFromLocal %s s3n://rsdblasttest/output/'%outPath)
        



