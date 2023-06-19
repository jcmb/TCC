#!/usr/bin/env python3

from distutils.core import setup

setup(name='TCC Utils',
      version='1.2',
      description='Trimble Connected Community Python Utilities',
      author='JCMBsoft',
      author_email='Geoffrey@jcmbsoft.com',
      url='https://jcmbsoft.com/',
      license="MIT For Trimble, GPL V3 for everyone else",
      py_modules=['TCC','TSD_Process'],
      scripts=[
        'TCC_Check_User/TCC_Check_User.py',
        'TCC_Check_FTP/TCC_Check_FTP.py',
        'TCC_Files/TCC_Files.sh',
        'TCC_Files/TCC_FileAccess.py',
        'TSD_Tools/TSD_Check.py',
        'TSD_Tools/TSD_Download.py',
        'TCC_Touch/TCC_Touch.py',
        'TAM_Items/TAM_Items.py']
     )
