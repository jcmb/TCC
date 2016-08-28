#! /usr/bin/env python

import sys
reload(sys)
sys.setdefaultencoding('utf-8')

try:
    assert sys.version_info >= (2,7,9       )
except:
    sys.exit("Need Python V2.7.9 or higher to run due to TLS Requirements" )


import logging
import argparse

from pprint import pprint

from TCC import TCC
from datetime import datetime, timedelta, date

#Setup the default logging here incase some thing sends a log message before we expect it
logging.basicConfig(level=logging.DEBUG)

logger=logging.getLogger("TCC_Touch")


def parse_args():
   argp = argparse.ArgumentParser(description="Check a Trimble Syncronizer Data for files of a give type.\nMostly used to check for tag files being stuck",
   epilog="""
   V1.0 (c) JCMBsoft 2016
   """);
   argp.add_argument('-u', '--user', metavar='USER', required=True,
                   help='TCC User Name')
   argp.add_argument('-o', '--org', metavar='ORG', required=True,
                   help='TCC organisation')
   argp.add_argument('-p', '--password', metavar='PASSWD', required=True,
                   help='TCC Password')

   argp.add_argument('file', nargs='+', help='File in TSD to touch. Use - for file names from StdIn')

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
   Files=args.file
   if Files == ['-']:
      logger.info("Reading fileanmes from Stdinput")
      Files=[]
      for line in sys.stdin:
         Files.append(line.rstrip())
#         print line
#      print Files

   if args.Tell:
      sys.stderr.write("User: {} Org: {}\n".format(USER,ORG))
      sys.stderr.write("Files: {}\n".format(Files))
      sys.stderr.write("Verbose: {}\n".format(Verbose))
      sys.stderr.write("\n")

   return (USER,ORG,PASSWD,Files,Verbose)


def main():
    (USER,ORG,PASSWD,Files,Verbose)=process_args(parse_args())
    tcc=TCC(USER,ORG,PASSWD,Verbose)
    if tcc.Login("JCMBsoft_TSD_Check"):
        TSD_ID=tcc.Find_TSD_ID(tcc.GetFileSpaces())
    else:
        sys.exit("Could not login to TCC, check user name, password and connection")
    logger.info("TSD_ID: {}".format(TSD_ID))
    for file in Files:
       sys.stdout.write(file)
#       sys.stdout.flush() 
       tcc_return=tcc.UpdateDateTime(TSD_ID,file)
       if tcc_return["success"]:
         logger.debug("Set Date Time on: {}".format(file))
         sys.stdout.write(" Updated\n")
       else:
         logger.warning("Failed to set Date Time on: {}".format(file))
         sys.stdout.write(" NOT updated\n")
         pprint (tcc_return)
    sys.stdout.flush() 
    tcc.Logoff 

if __name__ == "__main__":
    main()
