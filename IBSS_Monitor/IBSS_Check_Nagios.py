#! /usr/bin/env python3

import logging
import argparse

import sys

sys.path.append("/Users/gkirk/Documents/GitHub/TCC/");
from TCC import TCC
from datetime import datetime, timedelta, date
from pprint import pprint

#Setup the default logging here incase some thing sends a log message before we expect it
logging.basicConfig(level=logging.DEBUG)

logger=logging.getLogger("IBSS_Check_Nagios")



def parse_args():
   argp = argparse.ArgumentParser(description="Check if a device is connected to a IBSS MountPoint",fromfile_prefix_chars="@",
   epilog="""
   V1.0 (c) JCMBsoft 2020
   """);
   argp.add_argument('-u', '--user', metavar='USER', required=True,
                   help='TCC User Name')
   argp.add_argument('-o', '--org', metavar='ORG', required=True,
                   help='TCC organisation')
   argp.add_argument('-p', '--password', metavar='PASSWD', required=True,
                   help='TCC Password')

   argp.add_argument('-m', '--mount', metavar='MOUNT', required=True,
                   help='Mountpoint to check device is connected to')

   argp.add_argument('-d', '--device', metavar='DEVICE', required=True,
                   help='Device to check connected to the mount point')

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
   MOUNT=args.mount
   DEVICE=args.device

   if args.Tell:
      sys.stderr.write("User: {} Org: {}\n".format(USER,ORG))
      sys.stderr.write("Device {} to Check on MountPoint: {}\n".format(DEVICE,MOUNT))
      sys.stderr.write("Verbose: {}\n".format(Verbose))
      sys.stderr.write("\n")

   return (USER,ORG,PASSWD,MOUNT,DEVICE,Verbose)


def get_mountpointid (MountPoints,MountPoint_Name):
    mountpoint_id=None
#    pprint (MountPoints)

    for MountPoint in MountPoints['mountpoints']:
#        pprint (MountPoint)
#        print (MountPoint_Name)
        if MountPoint["name"] == MountPoint_Name:
            mountpoint_id=MountPoint["mountpointid"]
    return(mountpoint_id)


def main():
    (USER,ORG,PASSWD,MOUNT,DEVICE,Verbose)=process_args(parse_args())

    tcc=TCC(USER,ORG,PASSWD,Verbose)
    if tcc.Login("JCMBsoft_Mount_Point_Check"):
        AccountDetails=tcc.GetLoginAccount()
        ORGID=AccountDetails["data"]["orgId"]

        if not AccountDetails["success"]:
            print ("WARNING - Could not get Mountpoint Details")
            sys.exit(1)


        MountPoints=tcc.GetMountPoints("",wantallpublic="True",getinactive="False")
#        pprint(MountPoints)
        MountpointId=get_mountpointid(MountPoints,MOUNT)
        if MountpointId==None:
            print ("WARNING - Could not Find the Mountpoint {}".format(MOUNT))
            sys.exit(1)

        Connections=tcc.GetMountPointConnectionList(MountpointId)

#        pprint(Connections)

        found=False

        for Connection in Connections["mountPointConnections"]:
            if Connection["deviceshortname"] == DEVICE:
                found=True


        tcc.Logoff()

        if not found:
            print ("CRITICAL - {} is not connected to {}".format(DEVICE,MOUNT))
            sys.exit(2)
        else:
            print ("OK - {} is connected to {}".format(DEVICE,MOUNT))
            sys.exit(0)




if __name__ == "__main__":
    main()

