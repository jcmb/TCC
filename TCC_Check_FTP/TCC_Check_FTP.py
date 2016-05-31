#! /usr/bin/env python

import ftplib

from pprint import pprint
import sys
import logging
import json
import os
import argparse

#Setup the default logging here incase some thing sends a log message before we expect it
logging.basicConfig(level=logging.DEBUG)

logger=logging.getLogger("Check_TCC_FTP")


def parse_args():
   argp = argparse.ArgumentParser(description="Check a FTP Server for operation",
   epilog="""

   V1.0 (c) JCMBsoft 2016
   """);
   argp.add_argument('-u', '--user', metavar='USER', required=True,
                   help='TCC User Name')
   argp.add_argument('-o', '--org', metavar='ORG', required=True,
                   help='TCC organisation')
   argp.add_argument('-p', '--password', metavar='PASSWD', required=True,
                   help='TCC Password')

   argp.add_argument('-d', '--download', metavar='FILE',
                   help='File to download')

   argp.add_argument('-t','--timeout', type=int,default=20,
                   help='Timeout in seconds for each operation. Default 20s')


   argp.add_argument('--invalid_user', action='store_true',
                   help='TCC Password or user name is invalid')

   argp.add_argument('--TSD', action='store_true',
                   help='Check that TrimbleSynchronizerData is available to the user')

   argp.add_argument('--BDC', action='store_true',
                   help='Check that BusinessDataCenter is available to the user')
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
   INVALID_User=args.invalid_user
   TSD=args.TSD
   BDC=args.BDC
   DOWNLOAD=args.download
   TIMEOUT=args.timeout

   if args.Tell:
      sys.stderr.write("User: {} Org: {}\n".format(USER,ORG))
      sys.stderr.write("Verbose: {}\n".format(Verbose))
      sys.stderr.write("Expect invalid user: {}\n".format(INVALID_User))
      sys.stderr.write("Check access to TSD: {} BDC: {}\n".format(TSD,BDC))
      sys.stderr.write("File to download: {} \n".format(DOWNLOAD))
      sys.stderr.write("Timeout: {}\n".format(TIMEOUT))
      sys.stderr.write("\n")

   return (USER,ORG,PASSWD,INVALID_User,TSD,BDC,DOWNLOAD,TIMEOUT,Verbose)


def main():
    args=parse_args()
    (USER,ORG,PASSWD,INVALID_User,TSD,BDC,DOWNLOAD,TIMEOUT,Verbose)=process_args(args)

    try:
        ftp=ftplib.FTP(ORG+".myconnectedsite.com",timeout=TIMEOUT)
    except:
        logger.debug("Got unknown exception connecting")
        print "UNKNOWN - Got unknown exception connecting, check connection"
        sys.exit(3)

    if Verbose>=3:
        ftp.set_debuglevel(1)

    try:
        ftp.login(USER+"."+ORG,PASSWD)
    except ftplib.error_perm:
        logger.debug("Got Invalid User return")
        if INVALID_User:
            print "OK - Got invalid authenication return when expected"
            sys.exit(0)
        else:
            print "CRITICAL - got invalid authenication return when expected to be able to login"
            sys.exit(2)
    except:
        logger.debug("Got unknown exception logging in")
        print "UNKNOWN - Got unknown exception logging in, check connection"
        sys.exit(3)

    if INVALID_User:
        print "CRITICAL - got logged in when expected not to be able to login"
        sys.exit(2)

    dir=ftp.nlst("/TCC/"+ORG+'/')

    if not "TrimbleSynchronizerData" in dir:
        logger.debug("Trimble Synchronizer Data Not visible")
        if TSD:
            print "CRITICAL - Can not see Trimble Synchronizer Data"
            sys.exit(2)

    if not "BusinessDataCenter" in dir:
        logger.debug("Business Data Center Not visible")
        if BDC:
            print "CRITICAL - Can not see Business Data Center"
            sys.exit(2)

    if BDC:
        try:
            ftp.cwd("/TCC/"+ORG+'/BusinessDataCenter')
        except:
            logger.debug("Got exception changing to BDC")
            print "CRITICAL - Can not change to Business Data Center"
            sys.exit(2)

    if TSD:
        try:
            ftp.cwd("/TCC/"+ORG+'/TrimbleSynchronizerData')
        except:
            logger.debug("Got exception changing to TSD")
            print "CRITICAL - Can not change to Trimble Synchronizer Data"
            sys.exit(2)


    if DOWNLOAD != None:
        try:
            ftp.retrbinary("RETR "+DOWNLOAD,open('/dev/null', 'wb').write)
        except:
            logger.debug("Got exception downloading file: " + DOWNLOAD)
            print "CRITICAL - Can not download file: " + DOWNLOAD
            sys.exit(2)

    ftp.quit()

    print "OK - FTP Checked as expected"
    sys.exit(0)


if __name__ == "__main__":
    main()
