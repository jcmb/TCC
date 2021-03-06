#! /usr/bin/env python

import requests
from pprint import pprint
import sys
import logging
import json
import os
import argparse
import TCC

#Setup the default logging here incase some thing sends a log message before we expect it
logging.basicConfig(level=logging.WARNING)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

def parse_args():
   argp = argparse.ArgumentParser("Download a Trimble Syncronizer data filespace",
   epilog="""
   V1.1 (c) JCMBsoft 2016
   """);
   argp.add_argument('-u', '--user', metavar='USER', required=True,
                   help='TCC User')
   argp.add_argument('-o', '--org', metavar='ORG', required=True,
                   help='TCC Organisation')
   argp.add_argument('-p', '--password', metavar='PASSWD', required=True,
                   help='TCC Password')

   argp.add_argument('-t', '--type', metavar='EXTENSION', default="",
                   help='file types to be downloaded')

   argp.add_argument('--noarchived', action='store_true',
                   help='Ignore files in the Production-Data (Archived) folder')


   argp.add_argument('-v', '--verbose', action='count', default=0,
                   help='increase output verbosity (use up to 3 times)')
   argp.add_argument("-T","--Tell", action='store_true',help="Tell the settings before starting")
   args=argp.parse_args()

   return(args)

def process_args(args):

   Verbose=args.verbose

   if Verbose==0:
      logging.basicConfig(level=logging.WARNING)
   elif Verbose==1:
      logging.basicConfig(level=logging.INFO)
   elif Verbose==2:
      logging.basicConfig(level=logging.DEBUG)
   else:
      logging.basicConfig(level=logging.DEBUG)
      logging.getLogger("requests").setLevel(logging.DEBUG)
      logging.getLogger("urllib3").setLevel(logging.DEBUG)

   USER=args.user
   ORG=args.org
   PASSWD=args.password
   TYPES=args.type
   NO_ARCHIVE=args.noarchived
   
   if args.Tell:
      sys.stderr.write("User: {} Org: {}\n".format(USER,ORG))
      sys.stderr.write("Types: {}\n".format(TYPES))
      sys.stderr.write("Skip Archived: {}\n".format(NO_ARCHIVE))
      sys.stderr.write("Verbose: {}\n".format(Verbose))
      sys.stderr.write("\n")
   return (USER,ORG,PASSWD,TYPES,NO_ARCHIVE,Verbose)



def process_directory(dir,filespace_ID,tcc,NO_ARCHIVE):
   for entry in dir:
#      pprint (entry)
      if entry["isFolder"]:
         try:
#            print "Dir: " + entry["entryName"]
            os.mkdir(entry["entryName"])
         except:
            logging.debug("Failed to make Dir: " + entry["entryName"])
            pass #Assume that the dir is already there
         process_directory(entry["entries"],filespace_ID,tcc,NO_ARCHIVE)
      else:
         if (not NO_ARCHIVE) or (entry["entryName"].find("Production-Data (Archived)")==-1):
            if os.path.isfile(entry["entryName"]) and (os.path.getsize(entry["entryName"]) == int(entry["size"])):
              print 'Skipping (Downloaded already): '+ entry["entryName"] 
            else:             
              if tcc.Download(filespace_ID,entry["entryName"],entry["entryName"]):
                 print 'Downloaded: '+ entry["entryName"]
              else:
                 print 'Failed to download: '+ entry["entryName"]
         else:
            print 'Skipping (Archived): '+ entry["entryName"]


# The dir json is a list of entries, if it is a folder then it has a a list of entrys which might be more directories, welcome to recursion


def main():
    args=parse_args()
    (USER,ORG,PASSWD,TYPES,NO_ARCHIVE,Verbose)=process_args(args)
    tcc=TCC.TCC(USER,ORG,PASSWD,Verbose)
    if tcc.Login("JCMBsoft_TSD_Download"):

        filespaces=tcc.GetFileSpaces()

        TSD_ID=tcc.Find_TSD_ID(filespaces)

        if TSD_ID == None:
            raise ("Could not find TSD")

        data=tcc.Dir(TSD_ID,TYPES)

# The dir json is a list of entries, if it is a folder then it has a a list of entrys which might be more directories, welcome to recursion
        process_directory(data["entries"],TSD_ID,tcc,NO_ARCHIVE)

        tcc.Logoff()

if __name__ == "__main__":
    main()

