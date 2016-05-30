#! /usr/bin/env python

import sys
reload(sys)
sys.setdefaultencoding('utf-8')

import logging
import argparse

from TCC import TCC
from datetime import datetime, timedelta, date

#Setup the default logging here incase some thing sends a log message before we expect it
logging.basicConfig(level=logging.DEBUG)

logger=logging.getLogger("TSD_Check")


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

   argp.add_argument('-c', '--check', metavar='user', required=True,
                   help='TCC user to confirm is active')

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
   Check_User=args.check.title()

   if args.Tell:
      sys.stderr.write("User: {} Org: {}\n".format(USER,ORG))
      sys.stderr.write("User to Check: {}\n".format(Check_User))
      sys.stderr.write("Verbose: {}\n".format(Verbose))
      sys.stderr.write("\n")

   return (USER,ORG,PASSWD,Check_User,Verbose)


def main():
    (USER,ORG,PASSWD,Check_User,Verbose)=process_args(parse_args())

    tcc=TCC(USER,ORG,PASSWD,Verbose)
    if tcc.Login("JCMBsoft_TSD_Check"):

        Accounts=tcc.GetLoginAccounts()

        if not Accounts["success"]:
            print "WARNING - Could not get Account Information"
            sys.exit(1)

        found=False;

        for user in Accounts["users"]:
            if user["username"].title() == Check_User:
                found=True
                break

        tcc.Logoff()

        if not found:
            print "CRITICAL - {} is not a user".format(Check_User)
            sys.exit(2)
        else:
            print "OK - {} is a user".format(Check_User)
            sys.exit(0)


if __name__ == "__main__":
    main()
