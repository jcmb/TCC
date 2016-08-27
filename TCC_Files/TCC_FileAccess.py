#! /usr/bin/env python
import sys
reload(sys)
sys.setdefaultencoding('utf-8')

try:
    assert sys.version_info >= (2,7,9       )
except:
    sys.exit("Need Python V2.7.9 or higher to run due to TLS Requirements" )

import os
import json
import time
import calendar
from collections import defaultdict
from pprint import pprint
import urllib2
from cookielib import CookieJar
from datetime import datetime, timedelta, date
import logging
import logging.handlers

import argparse

from operator import itemgetter
import TSD_Process

try:
    from JCMBSoftPyLib.HumanBytes import humanbytes
    from JCMBSoftPyLib import HTML_Unit
except:
    sys.exit("JCMBSoftPyLib must be installed. ")

my_logger = logging.getLogger('TCC_FileAccess')
my_logger.setLevel(logging.DEBUG)

handler = logging.StreamHandler()
syslog_handler = logging.handlers.SysLogHandler()
my_logger.addHandler(handler)
my_logger.addHandler(syslog_handler)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)


def parse_args():
   argp = argparse.ArgumentParser("Report information on all accessble TSD filespaces on TCC",
   epilog="""
   V1.0 (c) JCMBsoft 2016
   """);
   argp.add_argument('-u', '--user', metavar='USER', required=True,
                   help='TCC User')
   argp.add_argument('-o', '--org', metavar='ORG', required=True,
                   help='TCC Organisation')
   argp.add_argument('-p', '--password', metavar='PASSWD', required=True,
                   help='TCC Password')

   argp.add_argument('-n', '--nocache', action='store_true',
                   help='Do not use Cache files if they exist')

   argp.add_argument('-v', '--verbose', action='count', default=0,
                   help='increase output verbosity (use up to 3 times)')
   argp.add_argument("-T","--Tell", action='store_true',help="Tell the settings before starting")
   args=argp.parse_args()

   return(args)

def process_args(args):

   Verbose=args.verbose

   if Verbose==0:
      my_logger.setLevel(logging.WARNING)
   elif Verbose==1:
      my_logger.setLevel(logging.INFO)
   elif Verbose==2:
      my_logger.setLevel(logging.DEBUG)
   else:
      my_logger.setLevel(logging.DEBUG)
      logging.getLogger("requests").setLevel(logging.DEBUG)
      logging.getLogger("urllib3").setLevel(logging.DEBUG)

   USER=args.user
   ORG=args.org.title()
   PASSWD=args.password
   Cacheing=not args.nocache

   if args.Tell:
      sys.stderr.write("User: {} Org: {}\n".format(USER,ORG))
      sys.stderr.write("Verbose: {}\n".format(Verbose))
      sys.stderr.write("Use Cache: {}\n".format(Cacheing))
      sys.stderr.write("\n")
   return (USER,ORG,PASSWD,Cacheing)


(User,Org,Password,Cacheing)=process_args(parse_args())

cj = CookieJar()
opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))

start_time=datetime.now()

HTML_File=sys.stdout

HTML_Unit.output_html_header(HTML_File,"Sync Details for CE&C TCC Orgs")

HTML_Unit.output_html_body(HTML_File)

HTML_File.write ('<br/><a href="#Summary">Goto Summary</a><br/>')

HTML_File.write ("Generation Started at: {0}<br>".format(start_time.strftime("%Y-%m-%d %H:%M:%S")))

#print "Logging In"
#print "https://"+Org+".myconnectedsite.com/tcc/login\?username="+User+"&orgname="+Org+"&password="+Password+"&applicationkey=grk_user_login"
try:
   data=opener.open("https://"+Org+".myconnectedsite.com/tcc/login\?username="+User+"&orgname="+Org+"&password="+Password+"&applicationkey=grk_user_login")
except:
    my_logger.critical("Could not connect to TCC")
    HTML_File.write("Error: Could not login, check connection\n")
    quit(2)

#print (data.read())
json_login = json.load(data)
success=json_login["success"]

if not success:
   my_logger.critical("Could not login, check password")
   HTML_File.write("Error: Could not login, check password\n")
   quit(1)


try:
   data=opener.open("https://"+Org+".myconnectedsite.com/tcc/getfilespaces")
except:
    my_logger.critical("Error: Could not get files spaces, connection error")
    HTML_File.write("Error: Could not get files spaces\n")
    quit(2)

#print (data.read())
json_filespaces = json.load(data)
#print json_filespaces
success=json_filespaces["success"]
filespaces = json_filespaces["filespaces"]

if not success:
   my_logger.critical("Error: Could not get files spaces")
   quit(1)

#print "Getting device information"

"""
        {
            "ACLAnonymousAccess": false,
            "authority": "OWNER",
            "description": "This filespace is for syncing your SCS900 and GCS900 Data",
            "fileSpaceId": "u5f908c62-7d36-11e3-b3eb-023e6d9f168c",
            "filespacetype": "regular",
            "ftppath": "/TCC/CE14/TrimbleSynchronizerData",
            "orgDisplayName": "CONEXPO 2014  (442025)",
            "orgId": "u7fcd86c8-3c47-4c14-b418-298555d24271",
            "orgShortname": "CE14",
            "shortname": "TrimbleSynchronizerData",
            "title": "Trimble Synchronizer Data"
        },
"""

found=False

Table_Names=[]

Total_Machines=0
Total_SCS900s=0
Total_Files=0
Total_FileSize=0
Total_FastDir_Size=0
Total_Directories=0
Total_Workgroups=0
Total_Orgs=0

#pprint (filespaces)
sorted_filespaces = sorted(filespaces, key=itemgetter('orgShortname'),cmp=lambda x,y: cmp(x.lower(), y.lower()))


for filespace in sorted_filespaces:
   org=filespace["orgShortname"].title()
   org_long_name=filespace["orgDisplayName"]

for filespace in sorted_filespaces:
#   print "\n\n"
#   pprint (filespace)
#   print "\n\n"
   if filespace["shortname"].lower()=="trimblesynchronizerdata":
      found=True
      org=filespace["orgShortname"].title()
      org_long_name=filespace["orgDisplayName"]
      fileSpaceId=filespace["fileSpaceId"]
#      fileSpaceId="u4958cc2d-81d2-11e2-9fed-000c2938bf10"

      my_logger.debug("TCC Org: " + org)
      my_logger.debug("TCC Org Name: " + org_long_name.encode('utf-8'))
      my_logger.debug("TCC fileSpaceId: " + fileSpaceId)

      if Cacheing:
         if os.path.isfile(org+".Sync.FastDir"): #The File exists just use it:
            my_logger.debug("Cache hit for " + org)
            data=open(org+".Sync.FastDir")
         else:
            my_logger.debug("Cache miss for " + org)
            try:
               net_data=opener.open("https://"+Org+".myconnectedsite.com/tcc/fastdir?recursive=true&path=/&filespaceid="+fileSpaceId)
            except:
               my_logger.critical("TCC Org: " + org + " Could not access file space: " + fileSpaceId)
               continue
            data=open(org+".Sync.FastDir","w")
            for line in  net_data:
               data.write(line)
            data.close
            data=open(org+".Sync.FastDir")
      else:
         my_logger.debug("Getting " + org + " https://"+Org+".myconnectedsite.com/tcc/fastdir?recursive=true&path=/&filespaceid="+fileSpaceId)
         try:
            data=opener.open("https://"+Org+".myconnectedsite.com/tcc/fastdir?recursive=true&path=/&filespaceid="+fileSpaceId)
         except:
            my_logger.critical("TCC Org: " + org + " Could not access file space: " + fileSpaceId)
            continue
#         my_logger.debug("Get Returned: "+str(data.getcode()))



      Tree={}

      (Tree,Number_Dirs,Number_Files,Files_Size,Fast_Dir_Size)=TSD_Process.Load_TSD_FastDir(Tree,data)
      my_logger.info('Number Directories: ' + str (Number_Dirs))
      my_logger.info('Number Files: ' + str (Number_Files))
      my_logger.info('File Size: ' + humanbytes(Files_Size))
      my_logger.info('Fast Dir Size: ' + humanbytes (Fast_Dir_Size))

      Total_Directories+=Number_Dirs
      Total_Files+=Number_Files
      Total_FileSize+=Files_Size
#      Total_FastDir_Size+=Fast_Dir_Size

      (Number_Machines,Number_SCS900s,Number_Workgroups,GCS900s,SCS900s)=TSD_Process.Process_TSD(Tree)
      my_logger.info('Number Machines: ' + str (Number_Machines))
      my_logger.info('Number SCS900: ' + str (Number_SCS900s))
      my_logger.info('Number Workgroups: ' + str (Number_Workgroups))

      Total_Machines+=Number_Machines
      Total_SCS900s+=Number_SCS900s
      Total_Workgroups+=Number_Workgroups
      Total_Orgs+=1

      #   pprint (Tree)

#      if len(GCS900s) + len(SCS900s) == 0 :
#         HTML_File.write("<h3>No devices</h3><p/>")


      if len(GCS900s) != 0 :
         TSD_Process.output_machines(HTML_File,org,GCS900s)
         Table_Names.append(org+"-GCS900")
         HTML_File.write("<p/>")

         for machine in GCS900s:
            Total_FastDir_Size+=machine[2]
         


      if len(SCS900s) != 0 :
         TSD_Process.output_SCS900(HTML_File,org,SCS900s)
         Table_Names.append(org+"-SCS900")
         HTML_File.write("<p/>")

      if Cacheing:
         data.close()


HTML_File.write ('<a name="Summary"><H2>Totals</H2><br/>')
HTML_File.write('<table>\n')
HTML_File.write('<tr><td>\n')
HTML_File.write('Orgs</td><td>' + str (Total_Orgs))
HTML_File.write('</td></tr>\n')
HTML_File.write('<tr><td>\n')
HTML_File.write('GCS900</td><td>' + str (Total_Machines))
HTML_File.write('</td></tr>\n')
HTML_File.write('<tr><td>\n')
HTML_File.write('SCS900</td><td>' + str (Total_SCS900s))
HTML_File.write('</td></tr>\n')
HTML_File.write('<tr><td>\n')
HTML_File.write('Workgroup</td><td>' + str (Total_Workgroups))
HTML_File.write('</td></tr>\n')
HTML_File.write('<tr><td>\n')
HTML_File.write('Files</td><td>' + str (Total_Files))
HTML_File.write('</td></tr>\n')
HTML_File.write('<tr><td>\n')
HTML_File.write('File Size</td><td>' + humanbytes(Total_FileSize))
HTML_File.write('</td></tr>\n')
HTML_File.write('<tr><td>\n')
HTML_File.write('Number Directories</td><td>' + str (Total_Directories))
HTML_File.write('</td></tr>\n')
HTML_File.write('<tr><td>\n')
HTML_File.write('Production Data Sync Size (Month)</td><td>' + humanbytes(Total_FastDir_Size*TSD_Process.Syncs_Per_Month))
#HTML_File.write('</td></tr>\n')
HTML_File.write('</table><br/>\n')

end_time=datetime.now()

HTML_File.write ("Generation Finished at: {0}\n".format(end_time.strftime("%Y-%m-%d %H:%M:%S")))
HTML_Unit.output_html_footer(HTML_File,Table_Names)


HTML_File.close

try:
   data=opener.open("https://"+Org+".myconnectedsite.com/tcc/logoff")
except:
   pass


