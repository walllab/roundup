##############################################
# NOTES ON CREATING ROUNDUP PACKAGE
##############################################

# commands and notes on how to create an archive of the roundup code and put it on the web so people can download it, though why anyone would do that is beyond me.

# put the code in a directory with a better name than "webapp".
cd ~/work/roundup
mkdir -p roundup
rsync -avz webapp/ roundup/

# clear backups and .pyc files
find . -type f -name "*~" -print0 -or -name "*\\.pyc" -print0 | xargs -0 rm

# tar the code and copy to the server
rm -f roundup.tar.gz; tar cvzf roundup.tar.gz roundup/
scp roundup.tar.gz orchestra.med.harvard.edu:/www/wall.hms.harvard.edu/docroot/sites/default/files/
rm -rf roundup.tar.gz roundup/
