2011/06/11 TFD

How to update the standalone version of rsd with the latest code.

[todo] rebuild and redeploy rsd_standalone, b/c previous version was built using fastacmd and formatdb which are not distributed with the blast executables anymore.
[done]
previously fixed rsd/roundup to use blastdbcmd and makeblastdb, not the (deprecated) fastacmd and formatdb

cd ~/work/roundup

# update code
mkdir rsd_standalone
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
rsd_standalone/rsd.py -v -q rsd_standalone/examples/genomes/Mycoplasma_genitalium.aa/Mycoplasma_genitalium.aa \
--subject-genome=rsd_standalone/examples/genomes/Mycobacterium_leprae.aa/Mycobacterium_leprae.aa \
-o rsd_standalone/examples/Mycoplasma_genitalium.aa_Mycobacterium_leprae.aa_0.2_1e-20.orthologs.txt

# test with ids
rsd_standalone/rsd.py -v -q rsd_standalone/examples/genomes/Mycoplasma_genitalium.aa/Mycoplasma_genitalium.aa \
--subject-genome=rsd_standalone/examples/genomes/Mycobacterium_leprae.aa/Mycobacterium_leprae.aa \
-o foo_ids.txt --no-blast-cache --ids rsd_standalone/examples/Mycoplasma_genitalium.aa.ids.txt
less foo_ids.txt
rm -f foo_ids.txt

# package up tarball and put on website
find . -type f -name '*~' | xargs rm; find . -type f -name '*.pyc' | xargs rm; 
rm -f rsd_standalone.tar.gz; tar cvzf rsd_standalone.tar.gz rsd_standalone/
scp rsd_standalone.tar.gz orchestra.med.harvard.edu:/www/wall.hms.harvard.edu/docroot/sites/default/files/
