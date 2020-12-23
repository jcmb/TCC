#!/usr/bin/python -u

import sys
reload(sys)
sys.setdefaultencoding('utf-8')


try:
    assert sys.version_info >= (2,7,9       )
except:
    sys.exit("Need Python V2.7.9 or higher to run due to TLS Requirements" )

from pprint import pprint
import logging
import json
import os
import argparse
import urllib
from collections import defaultdict

from TCC import TCC

try:
    from JCMBSoftPyLib import HTML_Unit
    from JCMBSoftPyLib import HumanBytes

except:
    sys.exit("JCMBSoftPyLib must be installed. ")


from datetime import datetime, timedelta, date

#Setup the default logging here incase some thing sends a log message before we expect it
logging.basicConfig(level=logging.DEBUG)

logger=logging.getLogger("TSD_Check")


def parse_args():
   argp = argparse.ArgumentParser(description="Check a Trimble Syncronizer Data for files of a give type.\nMostly used to check for tag files being stuck",
   epilog="""
   V1.1 (c) JCMBsoft 2020
   """);
   argp.add_argument('-u', '--user', metavar='USER', required=True,
                   help='TCC User Name')
   argp.add_argument('-o', '--org', metavar='ORG', required=True,
                   help='TCC organisation')
   argp.add_argument('-p', '--password', metavar='PASSWD', required=True,
                   help='TCC Password')

   argp.add_argument('--HTML', action='store_true',
                   help='Output a summary in HTML format')

   argp.add_argument('--HTMLFILE', nargs='?', type=argparse.FileType('w'),default=sys.stdout,
                   help='Output HTML to this file. Otherwise stdout. Only valid in HTML mode')

   argp.add_argument('--LS', action='store_true',
                   help='Output each file on a single line, suitable for sending into another program.')

   argp.add_argument('--LSFILE', nargs='?', type=argparse.FileType('w'),default=sys.stdout,
                   help='Output LS to this file. Otherwise stdout. Only valid in LS mode')

   argp.add_argument('-t', '--type', metavar='EXTENSION', default=None,
                   help='file types to be checked. Defualt .tag & .tds')

   argp.add_argument('-1', '--single', action='store_true',
                   help='Ignore machines with only 1 file. Automatically set for Nagios')

   argp.add_argument('--nagios', action='store_true',
                   help='Return information in a way suitable for Nagios monitoring')
   argp.add_argument('-w', '--warning', metavar='COUNT', type=int, default=10,
                   help='return warning unprocssed files are more than COUNT. Nagios Mode only')
   argp.add_argument('-c', '--critical', metavar='COUNT', type=int, default=30,
                   help='return critical unprocssed files are more than COUNT, Nagios Mode only')
   argp.add_argument('-v', '--verbose', action='count', default=0,
                   help='increase output verbosity (use up to 3 times)')
   argp.add_argument("-T","--Tell", action='store_true',help="Tell the settings before starting")
   args=argp.parse_args()
   return (args)

def process_args(args):

   Verbose=args.verbose



   if Verbose==0:
      logger.setLevel(logging.WARNING)
   elif Verbose==1:
      logger.setLevel(logging.INFO)
   else:
      logger.setLevel(logging.DEBUG)

   USER=args.user
   ORG=args.org
   PASSWD=args.password
   TYPES=args.type
   NAGIOS=args.nagios
   WARNING=args.warning
   CRITICAL=args.critical
   HTML=args.HTML
   HTML_File=args.HTMLFILE
   Skip_Single=args.single or args.nagios
   LS=args.LS
   LS_File=args.LSFILE


   if NAGIOS:
       if WARNING>= CRITICAL:
          sys.exit("Warning level must be smaller than the critical value")

   if ((TYPES != None) and TYPES[0]!="."):
      logger.debug("File type did not have a . at the start, have added it")
      TYPES="."+TYPES

   if args.Tell:
      sys.stderr.write("User: {} Org: {}\n".format(USER,ORG))
      sys.stderr.write("Nagios: {} Warning: {} Critical: {}\n".format(NAGIOS,WARNING,CRITICAL))
      sys.stderr.write("Types: {}\n".format(TYPES))
      sys.stderr.write("Skip Single: {}\n".format(Skip_Single))
      sys.stderr.write("Verbose: {}\n".format(Verbose))
      sys.stderr.write("HTML: {} to {}\n".format(HTML,HTML_File.name))

      sys.stderr.write("\n")

   if not (HTML or NAGIOS or LS):
      sys.exit("You must select HTML, LS or NAGIOS output")

   return (USER,ORG,PASSWD,TYPES,WARNING,CRITICAL,NAGIOS,HTML,HTML_File,LS,LS_File,Skip_Single,Verbose)



def check_directory(dir,Machines_With_Files,LS,LS_File):
   chunk_size=1024*60
   files=0
   total_files=0


   for entry in dir:
#      pprint (entry)
      if entry["isFolder"]:
         logger.debug('Folder : '+ entry["entryName"])
         (New_Files,Machines_With_Files,Total_Files)=check_directory(entry["entries"],Machines_With_Files,LS,LS_File)
         files+=New_Files
         total_files+=Total_Files
      else:
         total_files+=1
         if not (("Production-Data (Archived)" in  entry["entryName"]) or (".Archived" in  entry["entryName"]) or ("Project Boundary (Issue)" in  entry["entryName"]) or ("Other... (Issue)" in  entry["entryName"]) or  ("Subscription (Issue)"  in  entry["entryName"])):
            logger.info('File Not Processed: '+ entry["entryName"])
            files+=1
            if LS:
               LS_File.write("/{}\n".format(entry["entryName"]))
            MCD_Location=entry["entryName"].find("/Machine Control Data/")
            if MCD_Location == -1:
                logger.warning('Did not find Machine Control Data in file name: '+ entry["entryName"])
            else:
                Machine_Name=entry["entryName"][:MCD_Location]
#                print Machine_Name, entry["entryName"]
                Machines_With_Files[Machine_Name]+=1
         else:
            logger.debug('File Archived: '+ entry["entryName"])

      logger.debug("Files: " + entry["entryName"] + " ("+str(files)+")")
#   pprint (Machines_With_Files)
   return (files,Machines_With_Files,total_files)

def main():
    (USER,ORG,PASSWD,TYPES,WARNING,CRITICAL,NAGIOS,HTML,HTML_File,LS,LS_File,Skip_Single,Verbose)=process_args(parse_args())

    tcc=TCC(USER,ORG,PASSWD,Verbose)


    if HTML:
        logger.info('Outputting HTML')

        HTML_Unit.output_html_header(HTML_File,"Trimble Synronizer Data Information for: " + ORG)
        HTML_Unit.output_html_body(HTML_File)
        HTML_File.write ("Generation started at: {0}<br>".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

    if not tcc.Login("JCMBsoft_TSD_Check"):
        if HTML:
          HTML_File.write ("<h1>Could not login, check user name and passowrd</h1>")
          sys.exit(10)
        else:
          raise ("Could not login to TCC, check user name and password")






    filespaces=tcc.GetFileSpaces()

    TSD_ID=tcc.Find_TSD_ID(filespaces)

    if TSD_ID == None:
        if HTML:
          HTML_File.write ("<h1>Organisation does not have a Trimble Synronizer Data folder</h1>")
          sys.exit(10)
        else:
          raise ("Could not find TSD")

    if HTML:
        FileSpaceStatistics=tcc.GetFileSpaceStatistics(TSD_ID)

        if FileSpaceStatistics != None:
            logger.info("Total number of files: {}".format(FileSpaceStatistics["numberoffiles"]))
            logger.info("Size of all files: {}".format(HumanBytes.humanbytes(FileSpaceStatistics["sizeoffiles"])))

            HTML_File.write ("<ul>")
            HTML_File.write ("<li>Total number of files: {}\n</li>".format(FileSpaceStatistics["numberoffiles"]))
            HTML_File.write ("<li>Size of all files: {}\n</li>".format(HumanBytes.humanbytes(FileSpaceStatistics["sizeoffiles"])))
            HTML_File.write ("</ul>\n")

    if TYPES == None:
        data=tcc.Dir(TSD_ID,".tag")
    else:
        data=tcc.Dir(TSD_ID,TYPES)


# The dir json is a list of entries, if it is a folder then it has a a list of entrys which might be more directories, welcome to recursion
    Machines_With_Files=defaultdict(int)

    if "entries" in data:
      (un_processed,Machines_With_Files,total_files)=check_directory(data["entries"], defaultdict(int),LS,LS_File)
    else:
      un_processed=0
      total_files=0
      Machines_With_Files=[]


    if Skip_Single:
        un_processed=0
        for Machine in Machines_With_Files:
           if Machines_With_Files[Machine] >1:
               un_processed+=Machines_With_Files[Machine]

    if TYPES == None:
        logger.info("Total TAG Files: {}".format(total_files))
        logger.info("Total Unprocessed TAG Files: {}".format(un_processed))
        HTML_File.write("Total TAG Files: {}<br/>".format(total_files))
        HTML_File.write("Total TAG Unprocessed Files: {}<br/>".format(un_processed))
    else:
        logger.info("Total Files: {}".format(total_files))
        logger.info("Total Unprocessed {} Files: {}".format(TYPES, un_processed))
        HTML_File.write("Total {} Files: {}<br/>".format(TYPES, total_files))
        HTML_File.write("Total {} Unprocessed Files: {}<br/>".format(TYPES,un_processed))

    if HTML:
        HTML_Unit.output_table_header(HTML_File,"Machines","Machines with Unprocessed files",["Machine","Files"])
        for Machine in sorted(Machines_With_Files):
            if Skip_Single:
                if Machines_With_Files[Machine]>1:
                    HTML_Unit.output_table_row(HTML_File,[Machine,Machines_With_Files[Machine]])
            else:
                HTML_Unit.output_table_row(HTML_File,[Machine,Machines_With_Files[Machine]])
        HTML_Unit.output_table_footer(HTML_File)

#        parms={ 'USER' : USER, 'ORG' : ORG, "PASS" : PASSWD}
#        param_string=urllib.urlencode(parms)
        param_string="USER={}&ORG={}&PASS={}".format(USER,ORG,PASSWD)
        #We assume that the parameters have already been encoded, which is what they are in the cgi script case
        HTML_File.write("<br><a href=\"/cgi-bin/Touch_Tags?{}\">Resubmit Tags</a><br/>".format(param_string))
        HTML_File.write("Note that resubmitting the TAG files for processing will update there time stamp to the current time<br>")

    if TYPES == None:
        HTML_File.write("<p/>".format(total_files))

        data=tcc.Dir(TSD_ID,".tds")

# The dir json is a list of entries, if it is a folder then it has a a list of entrys which might be more directories, welcome to recursion
        Machines_With_Files=defaultdict(int)

        if "entries" in data:
          (un_processed,Machines_With_Files,total_files)=check_directory(data["entries"], defaultdict(int),LS,LS_File)
        else:
          un_processed=0
          total_files=0
          Machines_With_Files=[]


        if Skip_Single:
            un_processed=0
            for Machine in Machines_With_Files:
               if Machines_With_Files[Machine] >1:
                   un_processed+=Machines_With_Files[Machine]

        logger.info("Total TDS Files: {}".format(total_files))
        logger.info("Total TDS Unprocessed Files: {}".format(un_processed))

        if HTML:

            HTML_File.write("Total TDS Files: {}<br/>".format(total_files))
            HTML_File.write("Total TDS Unprocessed Files: {}<br/>".format(un_processed))
            HTML_Unit.output_table_header(HTML_File,"Machines_TDS","Machines with Unprocessed TDS files",["Machine","Files"])
            for Machine in sorted(Machines_With_Files):
                if Skip_Single:
                    if Machines_With_Files[Machine]>1:
                        HTML_Unit.output_table_row(HTML_File,[Machine,Machines_With_Files[Machine]])
                else:
                    HTML_Unit.output_table_row(HTML_File,[Machine,Machines_With_Files[Machine]])
            HTML_Unit.output_table_footer(HTML_File)

    #        parms={ 'USER' : USER, 'ORG' : ORG, "PASS" : PASSWD}
    #        param_string=urllib.urlencode(parms)
            #We assume that the parameters have already been encoded, which is what they are in the cgi script case

    tcc.Logoff()

    HTML_File.write ("Generation ended at: {0}<br>".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    HTML_Unit.output_html_footer(HTML_File,["Machines","Machines_TDS"])

    if NAGIOS:
        if un_processed >= CRITICAL:
            print "CRITICAL - {} unprocessed files".format(un_processed)
            sys.exit(2)
        elif un_processed >= WARNING:
            print "WARNING - {} unprocessed files".format(un_processed)
            sys.exit(1)
        else:
            print "OK - {} unprocessed files".format(un_processed)
            sys.exit(0)



if __name__ == "__main__":
    main()
