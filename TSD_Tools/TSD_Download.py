#! /usr/bin/env python3

import sys
sys.path.append("/Users/gkirk/Documents/GitHub/TCC")

import requests
from pprint import pprint
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

   argp.add_argument('--PREFIX', metavar='PREFIX', default="",
                   help='Only download files that start with the prefix')

   group = argp.add_mutually_exclusive_group()
   group.add_argument('-a', '--ALL', action='store_true', default=False,
                   help='If to download from all GCS900 and Earthworks filespaces')

   group.add_argument('-g', '--TSD', action='store_true', default=False,
                   help='If to download from all Trimble Synchronizer Data (GCS900 & SCS900/SiteWorks) filespaces')

   group.add_argument('-l', '--PL', action='store_true', default=False,
                   help='If to download from all Earthworks project library filespaces')


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
   PREFIX=args.PREFIX
   NO_ARCHIVE=args.noarchived
   ALL=args.ALL
   TSD=args.TSD
   PL=args.PL

   if args.Tell:
      sys.stderr.write("User: {} Org: {}\n".format(USER,ORG))
      sys.stderr.write("Types: {}\n".format(TYPES))
      sys.stderr.write("Prefix: {}\n".format(PREFIX))
      sys.stderr.write("Skip Archived: {}\n".format(NO_ARCHIVE))
      sys.stderr.write("All Orgs (GCS900 and EW): {}\n".format(ALL))
      sys.stderr.write("All Orgs (TSD Only): {}\n".format(TSD))
      sys.stderr.write("All Orgs (PL Only): {}\n".format(PL))
      sys.stderr.write("Verbose: {}\n".format(Verbose))
      sys.stderr.write("\n")
   return (USER,ORG,PASSWD,TYPES,NO_ARCHIVE,ALL,TSD,PL,PREFIX,Verbose)



def process_directory(dir,filespace_ID,tcc,NO_ARCHIVE,TYPES,PREFIX,path=""):
#   print("Path: " + path)
   for entry in dir:
#      pprint (entry)
      if entry["isFolder"]:
         try:
            print ("Dir: " + path + entry["entryName"])
            os.mkdir("./"+path+entry["entryName"])
         except:
            logging.debug("Failed to make Dir: " + entry["entryName"])
            pass #Assume that the dir is already there
         data=tcc.Dir(filespace_ID,TYPES,False,path+entry["entryName"])
         if data != None:
             process_directory(data["entries"],filespace_ID,tcc,NO_ARCHIVE,TYPES,PREFIX, path+entry["entryName"]+'/')
      else:
         if (not NO_ARCHIVE) or (entry["entryName"].find("Production-Data (Archived)")==-1):
            if entry["entryName"].startswith(PREFIX):
                if os.path.isfile(path+entry["entryName"]) and (os.path.getsize(path+entry["entryName"]) == int(entry["size"])):
                  print('Skipping (Downloaded already): '+ path+ entry["entryName"])
                else:
                  if tcc.Download(filespace_ID,path+entry["entryName"],"./"+path+entry["entryName"]):
                     print('Downloaded: '+ path+entry["entryName"])
                  else:
                     print('Failed to download: '+ entry["entryName"])
         else:
            print('Skipping (Archived): '+ entry["entryName"])


# The dir json is a list of entries, if it is a folder then it has a a list of entrys which might be more directories, welcome to recursion


def main():
    args=parse_args()
    (USER,ORG,PASSWD,TYPES,NO_ARCHIVE,ALL,TSD,PL,PREFIX,Verbose)=process_args(args)
    tcc=TCC.TCC(USER,ORG,PASSWD,Verbose)
    if tcc.Login("JCMBsoft_TSD_Download"):

        if ALL or PL or TSD:
            filespaces=tcc.GetFileSpaces(filter="all")
        else:
            filespaces=tcc.GetFileSpaces()

        if not TSD:
            for (filespace,orgShortname) in tcc.FileSpace_ID_generator(filespaces,"Project Library"):
                print ("Org: " + orgShortname, end = '')
                data=tcc.Dir(filespace,TYPES,False)

                if data == None:
                    print(". Dir Failed for " + orgShortname + ":Project Library")
                else:
                    print (". Dir Processed")
                    os.makedirs(orgShortname + os.sep  + "Project Library",exist_ok=True)
                    os.chdir(orgShortname + os.sep  + "Project Library")
                    process_directory(data["entries"],filespace,tcc,NO_ARCHIVE,TYPES,PREFIX)
                    os.chdir(".." + os.sep  + ".." )

        if not PL:
            for (filespace,orgShortname) in tcc.FileSpace_ID_generator(filespaces,"Trimble Synchronizer Data"):
                print ("Org: " + orgShortname)
                data=tcc.Dir(filespace,TYPES,False)
                if data == None:
                    print("Dir Failed for " + orgShortname + ":Project Library")
                else:
                    os.makedirs(orgShortname + os.sep  + "Trimble Synchronizer Data",exist_ok=True)
                    os.chdir(orgShortname + os.sep  + "Trimble Synchronizer Data")
                    process_directory(data["entries"],filespace,tcc,NO_ARCHIVE,TYPES,PREFIX)
                    os.chdir(".." + os.sep  + ".." )

        tcc.Logoff()

if __name__ == "__main__":
    main()

