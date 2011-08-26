##########################################
# NOTES ON CREATING RSD_STANDALONE PACKAGE
##########################################

################
# 2011/06/11 TFD
################

How to update the standalone version of rsd with the latest code.

[todo] rebuild and redeploy rsd_standalone, b/c previous version was built using fastacmd and formatdb which are not distributed with the blast executables anymore.
[done]
previously fixed rsd/roundup to use blastdbcmd and makeblastdb, not the (deprecated) fastacmd and formatdb

cd ~/work/roundup

# update code
mkdir -p rsd_standalone
cd webapp
cp rsd.py fasta.py nested.py util.py codeml.ctl jones.dat ../rsd_standalone/
chmod 775 ../rsd_standalone/rsd.py
cd ..

# update example genomes
rm -rf rsd_standalone/examples
mkdir -p rsd_standalone/examples/genomes
mkdir rsd_standalone/examples/genomes/Mycoplasma_genitalium.aa rsd_standalone/examples/genomes/Mycobacterium_leprae.aa
rsync -avz orchestra.med.harvard.edu:/groups/rodeo/roundup/genomes/current/Mycoplasma_genitalium.aa/Mycoplasma_genitalium.aa \
  rsd_standalone/examples/genomes/Mycoplasma_genitalium.aa/.
rsync -avz orchestra.med.harvard.edu:/groups/rodeo/roundup/genomes/current/Mycobacterium_leprae.aa/Mycobacterium_leprae.aa \
  rsd_standalone/examples/genomes/Mycobacterium_leprae.aa/.
python -c 'import sys; sys.path.append("rsd_standalone"); import rsd; rsd.formatForBlast("rsd_standalone/examples/genomes/Mycoplasma_genitalium.aa/Mycoplasma_genitalium.aa")'
python -c 'import sys; sys.path.append("rsd_standalone"); import rsd; rsd.formatForBlast("rsd_standalone/examples/genomes/Mycobacterium_leprae.aa/Mycobacterium_leprae.aa")'

# update example sequence ids:
python -c 'import sys; sys.path.append("rsd_standalone"); import fasta; ids = list([id for id in fasta.readIds("rsd_standalone/examples/genomes/Mycoplasma_genitalium.aa/Mycoplasma_genitalium.aa")])[:5]; [sys.stdout.write("{}\n".format(x)) for x in ids]' > rsd_standalone/examples/Mycoplasma_genitalium.aa.ids.txt

# update example orthologs
rsd_standalone/rsd.py -v -d 0.2 -e 1e-20 -q rsd_standalone/examples/genomes/Mycoplasma_genitalium.aa/Mycoplasma_genitalium.aa \
--subject-genome=rsd_standalone/examples/genomes/Mycobacterium_leprae.aa/Mycobacterium_leprae.aa \
-o rsd_standalone/examples/Mycoplasma_genitalium.aa_Mycobacterium_leprae.aa_0.2_1e-20.orthologs.txt

# test with ids
rsd_standalone/rsd.py -v -q rsd_standalone/examples/genomes/Mycoplasma_genitalium.aa/Mycoplasma_genitalium.aa \
--subject-genome=rsd_standalone/examples/genomes/Mycobacterium_leprae.aa/Mycobacterium_leprae.aa \
-o foo_ids.txt --no-blast-cache --ids rsd_standalone/examples/Mycoplasma_genitalium.aa.ids.txt
less foo_ids.txt
rm -f foo_ids.txt

# package up tarball and put on website
find . -type f -name "*~" -print0 -or -name "*\\.pyc" -print0 | xargs -0 rm
rm -f rsd_standalone.tar.gz; tar cvzf rsd_standalone.tar.gz rsd_standalone/
scp rsd_standalone.tar.gz orchestra.med.harvard.edu:/www/wall.hms.harvard.edu/docroot/sites/default/files/
rm -f rsd_standalone.tar.gz


################
# 2011/06/03 TFD
################

rsd.py has been refactored to have very few dependencies on other roundup python modules.
a commandline interface has been added to rsd.py to make it easy to compute orthologs given two genome fasta files.

# make an id file with Mycoplasma_genitalium.aa ids
echo '108885075
108885076
12044853
12044854
12044855
# test

# blank line' > ids.txt

# test for a subset of ids
python rsd.py --no-format -q /groups/rodeo/roundup/genomes/current/Mycoplasma_genitalium.aa/Mycoplasma_genitalium.aa \
--subject-genome=/groups/rodeo/roundup/genomes/current/Mycobacterium_leprae.aa/Mycobacterium_leprae.aa -o out.txt --ids ids.txt

# compute orthologs using --no-format and not using it, and using --no-blast-cache (on the fly) and not using it (precomputing).
python rsd.py --no-format -q /groups/rodeo/roundup/genomes/current/Mycoplasma_genitalium.aa/Mycoplasma_genitalium.aa \
--subject-genome=/groups/rodeo/roundup/genomes/current/Mycobacterium_leprae.aa/Mycobacterium_leprae.aa -o out2.txt
python rsd.py --no-format -q /groups/rodeo/roundup/genomes/current/Mycoplasma_genitalium.aa/Mycoplasma_genitalium.aa 
--subject-genome=/groups/rodeo/roundup/genomes/current/Mycobacterium_leprae.aa/Mycobacterium_leprae.aa -o out.txt --no-blast-cache
python rsd.py -q /groups/rodeo/roundup/genomes/current/Mycoplasma_genitalium.aa/Mycoplasma_genitalium.aa \
--subject-genome=/groups/rodeo/roundup/genomes/current/Mycobacterium_leprae.aa/Mycobacterium_leprae.aa -o out3.txt --no-blast-cache
./rsd.py -q /groups/rodeo/roundup/genomes/current/Mycoplasma_genitalium.aa/Mycoplasma_genitalium.aa \
--subject-genome=/groups/rodeo/roundup/genomes/current/Mycobacterium_leprae.aa/Mycobacterium_leprae.aa -o out4.txt

# no differences in the orthologs.  good.
diff out.txt out2.txt
diff out.txt out3.txt
diff out.txt out4.txt

# format some example genomes on orchestra
td23@flute000-171:~/tmp$ mkdir Mycoplasma_genitalium.aa
td23@flute000-171:~/tmp$ mkdir Mycobacterium_leprae.aa
td23@flute000-171:~/tmp$ cp /groups/rodeo/roundup/genomes/current/Mycoplasma_genitalium.aa/Mycoplasma_genitalium.aa Mycoplasma_genitalium.aa/
td23@flute000-171:~/tmp$ cp /groups/rodeo/roundup/genomes/current/Mycobacterium_leprae.aa/Mycobacterium_leprae.aa Mycobacterium_leprae.aa/
td23@flute000-171:~/tmp$ python -c 'import rsd; rsd.formatForBlast("Mycoplasma_genitalium.aa/Mycoplasma_genitalium.aa")'
td23@flute000-171:~/tmp$ python -c 'import rsd; rsd.formatForBlast("Mycobacterium_leprae.aa/Mycobacterium_leprae.aa")'

# make standalone rsd tarball with code, a readme, and some example files.
mkdir ~/work/roundup/rsd_standalone
cp rsd.py fasta.py nested.py util.py codeml.ctl jones.dat ../rsd_standalone/
chmod 775 ../rsd_standalone/rsd.py
cd ~/work/roundup/rsd_standalone
mkdir examples
mkdir examples/genomes
rsync -avz orchestra:tmp/Mycoplasma_genitalium.aa examples/genomes/
rsync -avz orchestra:tmp/Mycobacterium_leprae.aa examples/genomes/
rsync -avz orchestra:tmp/out4.txt examples/Mycoplasma_genitalium.aa_Mycobacterium_leprae.aa_0.2_1e-20.orthologs.txt
echo '108885075
108885076
12044853
12044854
12044855' > examples/Mycoplasma_genitalium.aa.ids.txt

# How to compute orthologs between all the sequences in the query and subject genomes.
./rsd.py -q examples/genomes/Mycoplasma_genitalium.aa/Mycoplasma_genitalium.aa \
--subject-genome=examples/genomes/Mycobacterium_leprae.aa/Mycobacterium_leprae.aa \
-o examples/Mycoplasma_genitalium.aa_Mycobacterium_leprae.aa_0.2_1e-20.orthologs.txt \

# How to compute orthologs between all the sequences in the query and subject genomes using genomes that have already been formatted for blast.
./rsd.py -q examples/genomes/Mycoplasma_genitalium.aa/Mycoplasma_genitalium.aa \
--subject-genome=examples/genomes/Mycobacterium_leprae.aa/Mycobacterium_leprae.aa \
-o examples/Mycoplasma_genitalium.aa_Mycobacterium_leprae.aa_0.2_1e-20.orthologs.txt \
--no-format

# How to compute orthologs for only a few sequences in the query genome. --no-blast-cache speeds up RSD when only a few orthologs are being computed.
./rsd.py -q examples/genomes/Mycoplasma_genitalium.aa/Mycoplasma_genitalium.aa \
--subject-genome=examples/genomes/Mycobacterium_leprae.aa/Mycobacterium_leprae.aa \
-o examples/Mycoplasma_genitalium.aa_Mycobacterium_leprae.aa_0.2_1e-20.orthologs.txt \
--ids examples/Mycoplasma_genitalium.aa.ids.txt --no-blast-cache

# package up tarball
cd ~/work/roundup
find . -type f -name '*~' | xargs rm; rm -f rsd_standalone.tar.gz; tar cvzf rsd_standalone.tar.gz rsd_standalone/

# copy to orchestra and test
cp webapp/rsd.py rsd_standalone/ && find . -type f -name '*~' | xargs rm && rm -f rsd_standalone.tar.gz && \
tar cvzf rsd_standalone.tar.gz rsd_standalone/ && scp rsd_standalone.tar.gz orchestra.med.harvard.edu:.
ssh orchestra.med.harvard.edu
cd && tar xvzf rsd_standalone.tar.gz && cd rsd_standalone
./rsd.py -q examples/genomes/Mycoplasma_genitalium.aa/Mycoplasma_genitalium.aa \
--subject-genome=examples/genomes/Mycobacterium_leprae.aa/Mycobacterium_leprae.aa \
-o examples/Mycoplasma_genitalium.aa_Mycobacterium_leprae.aa_0.2_1e-20.orthologs.txt \
--ids examples/Mycoplasma_genitalium.aa.ids.txt --no-blast-cache -v
./rsd.py -q examples/genomes/Mycoplasma_genitalium.aa/Mycoplasma_genitalium.aa \
--subject-genome=examples/genomes/Mycobacterium_leprae.aa/Mycobacterium_leprae.aa \
-o examples/Mycoplasma_genitalium.aa_Mycobacterium_leprae.aa_0.2_1e-20.orthologs.txt -v

