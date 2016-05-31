#! /usr/bin/env python
import sys
reload(sys)
sys.setdefaultencoding('utf-8')
#sys.path.append("/Users/gkirk/GitHub/TCC")
#sys.path.append("/Users/gkirk/Dropbox/Git/PyLib")



import json
from pprint import pprint
from collections import defaultdict
import argparse
from TCC import TCC
import requests
import logging
from JCMBSoftPyLib import HTML_Unit
import os

logging.basicConfig(level=logging.DEBUG)

logger=logging.getLogger("TAM_Check")


def parse_args():
   argp = argparse.ArgumentParser(description="Check TAM and TCC consistency",
   epilog="""
   V1.0 (c) JCMBsoft 2016
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

   argp.add_argument('--nagios', action='store_true',
                   help='Return information in a way suitable for Nagios monitoring')

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

   NAGIOS=args.nagios
   HTML=args.HTML
   HTML_File=args.HTMLFILE

   if args.Tell:
      sys.stderr.write("User: {} Org: {}\n".format(USER,ORG))
      sys.stderr.write("Verbose: {}\n".format(Verbose))
      sys.stderr.write("Nagios: {}\n".format(NAGIOS))
      sys.stderr.write("HTML: {} to {}\n".format(HTML,HTML_File.name))
      sys.stderr.write("\n")



   if not (HTML or NAGIOS ):
      sys.exit("You must select HTML or NAGIOS output")

   return (USER,ORG,PASSWD,NAGIOS,HTML,HTML_File,Verbose)


(USER,ORG,PASSWD,NAGIOS,HTML,HTML_File,Verbose)=process_args(parse_args())

if not HTML:
    HTML_File=open(os.devnull,"w")

tcc=TCC(USER,ORG,PASSWD,Verbose)

if not tcc.Login("JCMBsoft_TAM_Check"):
    sys.exit("Could not log into TCC, check password and connection")

ticket=tcc.ticket()
Devices=tcc.GetDevices()

#pprint(Devices)

asset_serials=defaultdict(str)
asset_types=defaultdict(str)
asset_name=defaultdict(str)


for device in Devices['devices']:
    if device["devicetype"] == "CB450" or device["devicetype"] == "CB460":
#       print device["devicetype"], device["serialnumber"]
       asset_serials[device["serialnumber"]]=None
       asset_types[device["serialnumber"]]=device["devicetype"]
       asset_name[device["serialnumber"]]=device["description"]


#pprint (Devices)
headers={"Content-Type": "application/json" }
payload={"tccTicket":ticket}
r=requests.post("https://"+ORG+".myconnectedsite.com/tam/api/users/login",headers=headers,json=payload)
TAM_Cookies=r.cookies;

r=requests.get("https://"+ORG+".myconnectedsite.com/tam/api/assets?limit=100&offset=0&query=%7B%7D",headers=headers,cookies=TAM_Cookies)

data = r.json()

devices=defaultdict(str)
asset_IDs=defaultdict(int)
asset_ID_radio=defaultdict(str)

HTML_Unit.output_html_header(HTML_File,"TCC & TAM Consistency")
HTML_Unit.output_html_body(HTML_File)

HTML_File.write("<h1>Asset consistency check</h1><br>")
HTML_File.write("Duplicate Radio check<br/>")

Message=""
OK=True

dups=0

for row in data["rows"]:
#   print "Row:"
#   pprint (row)
#   print "\nNew Asset\n"
   fields={}

   for field in row["fieldValues"]:
#      print "{} has value {}".format(field["field"]["name"], field["value"])
      fields[field["field"]["name"]]= field["value"]

#   pprint (fields)

   if "ASSET_ID" in fields:
     asset_IDs[fields["ASSET_ID"]]+=1
     asset_ID_radio[fields["ASSET_ID"]]=fields["Radio Serial Number"]

   if "Radio Serial Number" in fields:
      if fields["Radio Serial Number"] == "0"*len(fields["Radio Serial Number"]):
         logger.info("Radio {} Has Serial number of {}".format(row["assetId"],fields["Radio Serial Number"]))
      else:

         if devices[fields["Radio Serial Number"]]:
            HTML_File.write(fields["Radio Serial Number"] + " : " + devices[fields["Radio Serial Number"]]+"</br>")
            HTML_File.write(fields["Radio Serial Number"] + " : " + row["assetId"]+"</br>")
            dups+=1
         devices[fields["Radio Serial Number"]]=row["assetId"]

if dups == 0:
    HTML_File.write("No Duplicates<br/>")
else:
    Message+=" Duplicate Radio Serial Numbers"
    OK=False

HTML_File.write("<br/>")
HTML_File.write("Control Box Serial Numbers with duplicates<br/>\n")

dups=0

for row in data["rows"]:
   fields={}

   for field in row["fieldValues"]:
      fields[field["field"]["name"]]= field["value"]
#   pprint (fields)

   if ("Asset Serial #" in fields) and ("Radio Serial Number" in fields) :
      if fields["Asset Serial #"] == "0"*len(fields["Asset Serial #"]):
         logger.info("CB {} Has Zero Serial number of {}".format(row["assetId"],fields["Asset Serial #"]))
      elif fields["Radio Serial Number"] == "0"*len(fields["Radio Serial Number"]):
         logger.info("Radio {} Has Serial number of {} in CB check".format(row["assetId"],fields["Radio Serial Number"]))
      else:
          if asset_serials[fields["Asset Serial #"]]:
             HTML_File.write(fields["Asset Serial #"] + " : " + asset_serials[fields["Asset Serial #"]]+"<br/>\n")
             HTML_File.write(fields["Asset Serial #"] + " : " +  fields["Radio Serial Number"]+"<br/>\n")
             dups+=1

          asset_serials[fields["Asset Serial #"]]=fields["Radio Serial Number"]

if dups == 0:
    HTML_File.write("No Duplicates<br/>")
else:
    Message+=" Duplicate Asset Serial Number!"
    OK=False

HTML_File.write("<br/>")

#dups=0
#HTML_File.write("Control boxes that have not reported<br/>")

#for asset in sorted(asset_serials):
#    if asset_serials[asset] == None:
#        HTML_File.write("Control box that has not reported: " + str(asset_types[asset]) + "-" + str(asset)+ " : " + asset_name[asset]+"<br/>")
#        dups+=1
#
#if dups == 0:
#    HTML_File.write("All Control Boxes have reported<br/>")
#
#HTML_File.write("<br/>")


if 0 in asset_IDs:
   del asset_IDs[0]

HTML_File.write("Duplicate Asset ID's<br/>")

dups=0
for asset in sorted(asset_IDs):
    if asset_IDs[asset] > 1:
        HTML_File.write("Duplicate Asset ID: " + str(asset)+"<br/>")
        dups+=1

if dups == 0:
    HTML_File.write("No Duplicates<br/>")

HTML_File.write("Asset Checkout Complete</br>")
HTML_File.write("<br/>")


HTML_File.write("Radio Serial Numbers</br>")
for radio in sorted(devices):
    HTML_File.write(radio+" : " + str(devices[radio])+"<br/>")
    dups+=1

HTML_File.write("<br/>")

HTML_File.write("Asset ID's</br>")
for asset in sorted(asset_ID_radio):
    HTML_File.write(str(asset)+" : " + str(asset_ID_radio[asset]) + "<br/>")
HTML_File.write("<br/>")


HTML_File.write("Control Box Radio Serial Numbers, None if unkown</br>")
for asset in sorted(asset_serials):
    HTML_File.write(str(asset)+" : " + str(asset_serials[asset]) + " : " + str(devices[asset_serials[asset]])+ "<br/>")
HTML_File.write("<br/>")


if NAGIOS:
    if not OK:
        print "CRITICAL - {} ".format(Message)
        sys.exit(2)
    else:
        print "OK - TAM TCC Checked out ok"
        sys.exit(0)


