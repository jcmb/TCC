#! /bin/bash
cd /data/TCC_Files
rm *.FastDir
/mnt/hgfs/admin/TCC_Files/TCC_FileAccess.py > TCC_Files.html
mv -f TCC_Files.html /var/www/automat/TCC_Files.html


