#! /usr/bin/env python
from __future__ import division
import logging
import os
import re
from pprint import pprint
from JCMBSoftPyLib.HumanBytes import humanbytes
from JCMBSoftPyLib import HTML_Unit
import sys

from datetime import datetime
#import logging.handlers

Syncs_Per_Month=12*10*5*4

"""
BEGIN
folder|beafd7bb-d71a-43db-8039-7eb698e0df10|2010-06-07 23:23:32.179|2010-06-07 23:23:32.179|0|/
folder|1fa113c2-f057-492d-aa4f-9d306d8e8791|2015-04-08 22:57:37.853|2015-04-08 22:57:37.853|0|/001 Site Pulse Reports/
folder|98d0914d-ed05-4a61-98fe-1e39917db513|2012-06-26 21:11:50.218|2012-06-26 21:11:50.218|0|/14M/
folder|f17eaf5b-d36b-4046-9eda-866214455ea6|2012-06-26 21:11:50.565|2012-06-26 21:11:50.565|0|/14M/Machine Control Data/
folder|f16bfd73-226a-43cb-9bb4-588b1f91d528|2012-06-26 21:15:59.950|2012-06-26 21:15:59.950|0|/14M/Machine Control Data/.Production-Data/
folder|3299fe53-c43e-4cde-9f31-97a8e5cfd785|2012-06-26 21:16:00.097|2012-06-26 21:16:00.097|0|/14M/Machine Control Data/.Production-Data/0202J019SW--14M--120626/
folder|fb198d99-ff9c-4b1b-8330-7ff47e1ab817|2012-09-14 17:45:04.995|2012-09-14 17:45:04.995|0|/14M/Machine Control Data/.Production-Data/0202J019SW--CMPR--120729/
folder|97ddc5ed-1c1f-4124-821f-7d589b6aaa23|2012-09-14 20:14:09.912|2012-09-14 20:14:09.912|0|/14M/Machine Control Data/.Production-Data/0202J019SW--CMPR--120804/
folder|11e4b4eb-9b84-49e6-9ec2-62741b1b0651|2012-09-20 23:16:52.867|2012-09-20 23:16:52.867|0|/14M/Machine Control Data/.Production-Data/0202J019SW--CMPR--120822/
folder|51d9c55f-53bc-4c6b-b508-105bbb5a090d|2012-06-26 21:16:09.711|2012-06-26 21:16:09.711|0|/14M/Machine Control Data/.Production-Data/0202J019SW--TEST COMP--120626/
folder|4d0cf69d-2299-4c2a-9f14-96d5e2178764|2012-06-26 21:16:10.788|2012-06-26 21:16:10.788|0|/14M/Machine Control Data/.Production-Data/2491J005SW--14M--120626/
folder|4c04594e-c470-46a2-b122-66418d8b60b0|2013-06-04 21:42:38.573|2013-06-04 21:42:38.573|0|/14M/Machine Control Data/Eric/
folder|61e722d9-e27f-4c0c-bcec-52a616da462d|2013-06-04 21:47:03.267|2013-06-04 21:47:03.267|0|/14M/Machine Control Data/Eric II/
file|79646a14-7d91-4dcb-993a-924d079a354f|2013-06-04 21:47:05.050|2013-06-04 21:47:05.050|215202|/14M/Machine Control Data/Eric II/Eric II.bg.dxf
file|38bd030a-14a8-4227-ad44-9f75f15a4acf|2013-06-04 21:47:04.347|2013-06-04 21:47:04.347|69222|/14M/Machine Control Data/Eric II/Eric II.ttm
file|d1696488-2078-40bb-bafd-653739f0f3e7|2013-06-04 21:47:05.497|2013-06-04 21:47:05.497|649|/14M/Machine Control Data/Eric II/TNCO_CURBS.cfg
folder|1b8dd62c-fc7d-44ad-b070-3c6902f8e564|2013-06-04 22:51:17.599|2013-06-04 22:51:17.599|0|/14M/Machine Control Data/Eric II_20130604_220737/
"""


my_logger = logging.getLogger('TSD_FastDir')
my_logger.setLevel(logging.INFO)

handler = logging.StreamHandler()
my_logger.addHandler(handler)

#handler = logging.handlers.SysLogHandler()
#my_logger.addHandler(handler)

dirs3 = re.compile('/(.*?)/(.*?)/(.*?)/')
dirs2 = re.compile('/(.*?)/(.*?)/')
dir1 = re.compile('/(.*?)/')
last_dir = re.compile('.*/(.*?)$')
first_dir = re.compile('(.*?)/.*$')

def Parse_Fast_Dir(Line):
   result=[None]*9

   split_line=Line.split("|")
   if len (split_line) <6 :
      my_logger.warning("Did not get a full Fast Dir Line: " + Line)
      return None

#   print split_line

   if split_line[0]=="folder":
      result[0]=True
   elif split_line[0]=="file":
      result[0]=False
   else:
      raise ValueError('Invalid type field in line: ' + Line)

   result[8]=len(Line)+2

   result[1]=split_line[1]
#2011-07-20 21:49:33.562
   try :
      date=datetime.strptime(split_line[2],"%Y-%m-%d %H:%M:%S.%f")
   except:
      date=datetime.strptime(split_line[2],"%Y-%m-%d %H:%M:%S")
   result[2]=date

   try:
      date=datetime.strptime(split_line[3],"%Y-%m-%d %H:%M:%S.%f")
   except:
      date=datetime.strptime(split_line[3],"%Y-%m-%d %H:%M:%S")
   result[3]=date

   result[4]=int(split_line[4])

   (result[5],result[6])=os.path.split(split_line[5])
   result[5]=result[5][1:] # Remove the leading / from the directory, this means the root folder is now ''
   if len (split_line) == 7 :
      result[7]=split_line[6]

#   print result
   return (result)


def Add_Dir(Tree,Directory,Length):

#   print "DIRS"
#   pprint (Dir)
   Dirs=Directory.split('/')
#   pprint (Dirs)
   if Dirs[0]=='':
      return Tree
      #With the root we do nothing

   New_Dir=Dirs[len(Dirs)-1]
#   print "New Dir: "+New_Dir.encode('utf-8')
   current_dir=Tree
   for Dir in Dirs[:-1]:
#      pprint (current_dir)
#      print  "Dir: " + Dir.encode('utf-8')
      if not (Dir in current_dir): #Handle the case where TCC did not report all the  directories. Which is clearly a bug
         my_logger.warn("Had to add a directory into the tree that was not listed: " + Dir.encode('utf-8') + " Within " + Directory.encode('utf-8'))
         current_dir[Dir]={}
         current_dir[Dir]["."]=0
      current_dir=current_dir[Dir]
#   pprint (current_dir)
   current_dir[New_Dir]={}
   current_dir[New_Dir]["."]=Length


def Add_File(Tree,File_Details):

   Dirs=File_Details[5].split('/')
   New_Dir=Dirs[len(Dirs)-1]
#   print "New Dir: " + New_Dir
   current_dir=Tree
   for Dir in Dirs[:-1]:
#      print  "Dir: " + Dir
      current_dir=current_dir[Dir]
   if New_Dir!="":
      current_dir[New_Dir][File_Details[6]]=[File_Details[1],File_Details[2],File_Details[3],File_Details[4],File_Details[8]]
      #Ignore all the files in the root


def Load_TSD_FastDir(Tree,FastDir):

   Tree={}
   Fast_Dir_Size=12 # BEGIN + END + /c/r * 2
   Number_Dirs=0
   Number_Files=0
   Files_Size=0

   my_logger.debug('In TSC_FastDir')
   Lines=0

   Line = FastDir.readline().rstrip()

#   print Line
   if Line != "BEGIN":
      my_logger.critical('Fast Dir did not start with a BEGIN')
      return None

   Files=[]
   for Line in FastDir:
      Line=Line.rstrip()
      Line = unicode(Line,encoding='utf-8')
      if Line == "END":
         continue

#      print Line
      Line_Details=Parse_Fast_Dir(Line)

      if Line_Details == None: #Parsing the line failed so we will just ignore it this time
         continue
#      print Line_Details

      Fast_Dir_Size+=Line_Details[8]


      if Line_Details[0]:
         # We have a folder, so we need to add it to the tree. Since the fastdir is sorted by path name then we know that everything in the path has already been added
         # Line_Details[5] is the directory, without the / at the front or end. The root is blank
         Add_Dir(Tree,Line_Details[5],Line_Details[8])
         Number_Dirs+=1
      else:
         Add_File(Tree,Line_Details)
         Number_Files+=1
         Files_Size+=Line_Details[4]
#      if Last_Dir != Line_Details[5]


      Lines+=1
#      if Lines==1:

   return (Tree,Number_Dirs,Number_Files,Files_Size,Fast_Dir_Size)

def isMachine(Tree):
#   pprint (Tree)
#   print "Machine Control Data" in Tree
   return "Machine Control Data" in Tree

def isSCS900(Tree):
   return "Trimble SCS900 Data" in Tree


def process_WorkGroup(Tree,Workgroup,GCS900,SCS900):
   Machines=0
   SCS900s=0
   for dir in sorted(Tree):
#      print dir
      if dir==".":
         continue
      if isMachine(Tree[dir]):
         my_logger.debug (dir + " Is Machine")
         Sync_Size=FastDir_Sync_Size(Tree[dir]["Machine Control Data"])
         File_Size=FileSize(Tree[dir]["Machine Control Data"])
         Number_Of_Designs=NumberMachineDesigns(Tree[dir]["Machine Control Data"])
         if "Production-Data (Archived)" in Tree[dir]["Machine Control Data"] :
            my_logger.debug (dir + " Has Production Data")
            Production_Sync_Size=FastDir_Sync_Size(Tree[dir]["Machine Control Data"]["Production-Data (Archived)"])
         else:
            my_logger.debug (dir + " Does not have Production Data")
            Production_Sync_Size=0
         Number_Of_Files=NumberOfFiles(Tree[dir]["Machine Control Data"])

         my_logger.debug("GCS900 Sync_Size: " + Workgroup + "/"+ dir + " :: " + humanbytes(Sync_Size))
         my_logger.debug("GCS900 File_Size: " + Workgroup + "/"+ dir + " :: " + humanbytes(File_Size))
         my_logger.debug("GCS900 Designs: " + dir + " :: " + str(Number_Of_Designs))
         my_logger.debug("GCS900 Files: " + dir + " :: " + str(Number_Of_Files))
         GCS900.append([ dir,Workgroup,Sync_Size,File_Size,Number_Of_Designs,Number_Of_Files,Production_Sync_Size])

         Machines+=1
      elif isSCS900(Tree[dir]):
         my_logger.debug (dir + " Is SCS900")
         Sync_Size=FastDir_Sync_Size(Tree[dir]["Trimble SCS900 Data"])
         if "Trimble GeoData" in Tree[dir]:
            Sync_Size+=FastDir_Sync_Size(Tree[dir]["Trimble GeoData"])

         File_Size=FileSize(Tree[dir]["Trimble SCS900 Data"])
         Number_Of_Files=NumberOfFiles(Tree[dir]["Trimble SCS900 Data"])
         if "Trimble GeoData" in Tree[dir]:
            File_Size+=FileSize(Tree[dir]["Trimble GeoData"])
            Number_Of_Files+=NumberOfFiles(Tree[dir]["Trimble GeoData"])


         my_logger.debug("SCS900 Sync_Size: " + Workgroup + "/"+ dir + " :: " + humanbytes(Sync_Size))
         my_logger.debug("SCS900 File_Size: " + Workgroup + "/"+ dir + " :: " + humanbytes(File_Size))
         my_logger.debug("SCS900 Number Of Files: " + Workgroup + "/"+ dir + " :: " + str(Number_Of_Files))
         SCS900.append([ dir,Workgroup , Sync_Size,File_Size,Number_Of_Files])



         SCS900s+=1
   return (Machines,SCS900s)

def FastDir_Sync_Size(Tree):
   Size=0
   for fileordir in Tree:
#      print "File: " + fileordir
#      print type(Tree[fileordir])
      if type(Tree[fileordir]) is dict:
         Size+=FastDir_Sync_Size(Tree[fileordir])
      elif type(Tree[fileordir]) is list:
         Size+=Tree[fileordir][4]
      elif type(Tree[fileordir]) is int: #We get this for the length of the . directory items
         Size+=Tree[fileordir]
      else:
         raise ValueError('Unknown Element type in Sync_Size:')

   return Size

def FileSize(Tree):
   Size=0
   for fileordir in Tree:
#      print "File: " + fileordir
#      print type(Tree[fileordir])
      if type(Tree[fileordir]) is dict:
         Size+=FileSize(Tree[fileordir])
      elif type(Tree[fileordir]) is list:
         Size+=Tree[fileordir][3]
      elif type(Tree[fileordir]) is int: #We get this for the length of the . directory items
         pass; # Directories don't have file size for the downloads
      else:
         raise ValueError('Unknown Element type in Sync_Size:')

   return Size

def NumberOfFiles(Tree):
   Files=0
   for fileordir in Tree:
#      print "File: " + fileordir
#      print type(Tree[fileordir])
      if type(Tree[fileordir]) is dict:
         Files+=NumberOfFiles(Tree[fileordir])
      elif type(Tree[fileordir]) is list:
         Files+=1
   return Files


def NumberMachineDesigns(Tree):
   Designs=0
   for fileordir in Tree:
#      print "File: " + fileordir
#      print type(Tree[fileordir])
      if type(Tree[fileordir]) is dict:
         if fileordir[0]!= "." and fileordir != "Production-Data (Archived)":
            Designs+=1
   return(Designs)

def Process_TSD(Tree):
   Number_Machines=0
   Number_SCS900s=0
   Number_Workgroups=0
   GCS900=[]
   SCS900=[]
   for dir in sorted(Tree):
#      print dir
      if dir==".":
         continue
      if isMachine(Tree[dir]):
         my_logger.debug (dir + " Is Machine")
         Sync_Size=FastDir_Sync_Size(Tree[dir]["Machine Control Data"])
         if "Production-Data (Archived)" in Tree[dir]["Machine Control Data"] :
            my_logger.debug (dir + " Has Production Data")
            Production_Sync_Size=FastDir_Sync_Size(Tree[dir]["Machine Control Data"]["Production-Data (Archived)"])
         else:
            my_logger.debug (dir + " Does not have Production Data")
            Production_Sync_Size=0
         File_Size=FileSize(Tree[dir]["Machine Control Data"])
         Number_Of_Designs=NumberMachineDesigns(Tree[dir]["Machine Control Data"])
         Number_Of_Files=NumberOfFiles(Tree[dir]["Machine Control Data"])
         GCS900.append([dir,"",Sync_Size,File_Size,Number_Of_Designs,Number_Of_Files,Production_Sync_Size])
         my_logger.debug("GCS900 Sync_Size: " + dir + " :: " + humanbytes(Sync_Size))
         my_logger.debug("GCS900 File_Size: " + dir + " :: " + humanbytes(File_Size))
         my_logger.debug("GCS900 Designs: " + dir + " :: " + str(Number_Of_Designs))
         my_logger.debug("GCS900 Files: " + dir + " :: " + str(Number_Of_Files))
         Number_Machines+=1
      elif isSCS900(Tree[dir]):
         my_logger.debug (dir + " Is SCS900")
         Number_SCS900s+=1
         Sync_Size=FastDir_Sync_Size(Tree[dir]["Trimble SCS900 Data"])
         if "Trimble GeoData" in Tree[dir]:
            Sync_Size+=FastDir_Sync_Size(Tree[dir]["Trimble GeoData"])

         File_Size=FileSize(Tree[dir]["Trimble SCS900 Data"])
         Number_Of_Files=NumberOfFiles(Tree[dir]["Trimble SCS900 Data"])

         if "Trimble GeoData" in Tree[dir]:
            File_Size+=FileSize(Tree[dir]["Trimble GeoData"])
            Number_Of_Files+=NumberOfFiles(Tree[dir]["Trimble GeoData"])

         my_logger.debug("SCS900 Sync_Size: " + dir + " :: " + humanbytes(Sync_Size))
         my_logger.debug("SCS900 File_Size: " + dir + " :: " + humanbytes(File_Size))
         my_logger.debug("SCS900 Files: " + dir + " :: " + str(Number_Of_Files))
         SCS900.append([dir,"",Sync_Size,File_Size,Number_Of_Files])
      else:
         my_logger.debug ("Checking Workgroup: " + dir)
         (Machines,SCS900s)=process_WorkGroup(Tree[dir],dir,GCS900,SCS900)
         Number_Machines+=Machines
         Number_SCS900s+=SCS900s
         if Machines+SCS900s != 0:
            Number_Workgroups+=1

   return(Number_Machines,Number_SCS900s,Number_Workgroups,GCS900,SCS900)

def output_machines(HTML_File,Org,GCS900s):

   HTML_Unit.output_table_header(HTML_File,Org+"-GCS900","GCS900 Machines for "+ Org,["Machine","Workgroup","Sync Size (KiB)","Total File Size (MiB)","Designs","Number of Files","Production Data<br/>Sync Size (Kib)","Prod %","Production Data<br/>Month MiB"],100)
   for Machine in GCS900s:
      Display_Machine=list(Machine) # Make a copy not a reference
#      print Machine
# Machine, Workgroup, Sync Size, File Size, Number of Designs, Prod Sync Size, Number Of Files
#      Display_Machine[2]=humanbytes(Machine[2])
#      Display_Machine[3]=humanbytes(Machine[3])
      Display_Machine[2]="{0:.1f}".format(Machine[2]/1024)
      Display_Machine[3]="{0:.1f}".format(Machine[3]/1024/1024)
      Display_Machine[6]="{0:.1f}".format(Machine[6]/1024)
#      print Machine[5]
#      print Machine[2]
#      print Machine[5]/Machine[2]
      Display_Machine.append("{0:.1f}".format((Machine[6]/Machine[2]) * 100))
      Display_Machine.append("{0:.1f}".format((Machine[6]*Syncs_Per_Month)/1024/1024))

      HTML_Unit.output_table_row(HTML_File,Display_Machine)
   HTML_Unit.output_table_footer(HTML_File)

def output_SCS900(HTML_File,Org,SCS900s):

   HTML_Unit.output_table_header(HTML_File,Org+"-SCS900","SCS900 devices for "+ Org,["Machine","Workgroup","Sync Size (KiB)","Total File Size (MiB)","Number of Files"],75)
   for SCS in SCS900s:
      Display_SCS=list(SCS) # Make a copy not a reference
      Display_SCS[2]="{0:.1f}".format(SCS[2]/1024)
      Display_SCS[3]="{0:.1f}".format(SCS[3]/1024/1024)
      HTML_Unit.output_table_row(HTML_File,Display_SCS)
   HTML_Unit.output_table_footer(HTML_File)




if __name__ == '__main__':
   my_logger.info('TSC_Process Test')

   f = open('FastDir.txt', 'ra')
#   lines=f.read()
#   print lines
   Tree={}
   (Tree,Number_Dirs,Number_Files,Files_Size,Fast_Dir_Size)=Load_TSD_FastDir(Tree,f)
   my_logger.info('Number Directories: ' + str (Number_Dirs))
   my_logger.info('Number Files: ' + str (Number_Files))
   my_logger.info('File Size: ' + humanbytes(Files_Size))
   my_logger.info('Fast Dir Size: ' + humanbytes (Fast_Dir_Size))

   (Number_Machines,Number_SCS900s,Number_Workgroups,GCS900s,SCS900s)=Process_TSD(Tree)
   my_logger.info('Number Machines: ' + str (Number_Machines))
   my_logger.info('Number SCS900: ' + str (Number_SCS900s))
   my_logger.info('Number Workgroups: ' + str (Number_Workgroups))
#   pprint (Tree)


   HTML_Unit.output_html_header(sys.stdout,"Sync Details for Trimble HH")
   output_machines(sys.stdout,'TrimbleHH',GCS900s)
   sys.stdout.write("<p/>")
   output_SCS900(sys.stdout,'TrimbleHH',SCS900s)
   HTML_Unit.output_html_footer(sys.stdout,["Trimblehh-GCS900"])
