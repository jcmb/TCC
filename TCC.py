
import logging
import requests
import urllib.parse
from pprint import pprint
from datetime import datetime

logging.basicConfig(level=logging.WARNING)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)


class TCC:
    def __init__(self,USER,ORG,PASSWD,Verbose=0):
        self.USER = USER
        self.ORG = ORG
        self.PASSWD = PASSWD
        self.TCC_API = "https://"+ORG+".myconnectedsite.com/tcc/"
        self.login_cookies=None
        self.Logged_In=False
        self.Verbose=Verbose
        self.logger=logging.getLogger("TCC (" + USER + "." + ORG+")")
        self.ORG_DETAILS={}

        if Verbose==0:
            self.logger.setLevel(logging.WARNING)
        elif Verbose==1:
            self.logger.setLevel(logging.INFO)
        elif Verbose==2:
            self.logger.setLevel(logging.DEBUG)
        else:
            self.logger.setLevel(logging.DEBUG)
            logging.getLogger("requests").setLevel(logging.DEBUG)
            logging.getLogger("urllib3").setLevel(logging.DEBUG)


    def Login(self,Application_Type="JCMBsoft_Python_Library"):
        self.Logged_In=False

        try:
            r=requests.get(self.TCC_API + "login?username={}&orgname={}&password={}&applicationkey={}".format(self.USER,self.ORG,self.PASSWD,Application_Type),timeout=300)
#            pprint(r.json())
            if r.status_code != 200:
                self.logger.error("Could not login TCC")
            else:
                self.logger.debug("Logged into TCC")
                self.Logged_In=True
                self.login_cookies=r.cookies
                self.accountid=r.json()["accountid"]
        except KeyboardInterrupt:
            raise
        except:
            self.logger.error("Could not connect to TCC")
        return (self.Logged_In)


    def Logoff(self):
        self.Logged_In=False

        r=requests.get(self.TCC_API + "logoff",cookies=self.login_cookies,timeout=300)
        if r.status_code != 200:
            self.logger.error("Could not logout of  TCC")
        else:
            self.logger.debug("Logged out of TCC")
            self.Logged_In=False
            self.login_cookies=r.cookies

    def Logout(self):
        self.logger.warning("Logout of TCC called, should use Logoff")
        self.Logoff()


    def GetFileSpaces(self,filter="myorg"):
        if not self.Logged_In:
            raise ("Not Logged into TCC in Get File Spaces")

        r=requests.get(self.TCC_API + "GetFileSpaces?filter="+filter,cookies=self.login_cookies,timeout=300)
        if r.status_code != 200:
            self.logger.error("Could not get filespaces from TCC")
            return (None)
        else:
            self.logger.debug("Got filespaces from TCC")
            return (r.json())


    def GetFileSpaceStatistics(self,filespaceid):
        if not self.Logged_In:
            raise ("Not Logged into TCC in Get File Spaces")

        r=requests.get(self.TCC_API + "GetFileSpaceStatistics?filespaceid="+filespaceid,cookies=self.login_cookies,timeout=300)
        self.logger.debug(self.TCC_API + "GetFileSpaceStatistics?filespaceid="+filespaceid)
        if r.status_code != 200:
            self.logger.error("Could not get FileSpaceStatistics from TCC")
            return (None)
        else:
            self.logger.debug("Got FileSpaceStatistics from TCC")
            return (r.json())

    def GetOrganization(self,orgid):
        if not self.Logged_In:
            raise ("Not Logged into TCC in Get Organization")

        r=requests.get(self.TCC_API + "GetOrganization?orgid="+orgid,cookies=self.login_cookies,timeout=300)
        if r.status_code != 200:
            self.logger.error("Could not GetOrganization from TCC")
            return (None)
        else:
            self.logger.debug("Got GetOrganization from TCC")
            return (r.json())

    def GetOrganizationTags(self,orgid):
        if not self.Logged_In:
            raise ("Not Logged into TCC in GetOrganizationTags")

        r=requests.get(self.TCC_API + "GetOrganizationTags?orgid="+orgid,cookies=self.login_cookies,timeout=300)
        if r.status_code != 200:
            self.logger.error("Could not GetOrganizationTags from TCC")
            return (None)
        else:
            self.logger.debug("Got GetOrganizationTags from TCC")
            return (r.json())

    def Find_TSD_ID(self,filespaces):
        if filespaces == None:
            return (None)
        filespace_ID=""
        TSD="Trimble Synchronizer Data".upper()
        for filespace in filespaces["filespaces"]:
        #   print filespace["title"]
          if filespace["title"].upper() == TSD:
             filespace_ID=filespace["fileSpaceId"]
             break

        if filespace_ID=="":
          self.logger.error("Could not find TSD file space")
          return(None)
        else:
          self.logger.debug("Got TSD filespace: " + filespace_ID)

        return(filespace_ID)



    def Find_PL_ID(self,filespaces):
        if filespaces == None:
            return (None)
        filespace_ID=""
        PL="Project Library".upper()
#        pprint(filespaces)
        for filespace in filespaces["filespaces"]:
        #   print filespace["title"]
          if filespace["title"].upper() == PL:
             filespace_ID=filespace["fileSpaceId"]
             break

        if filespace_ID=="":
          self.logger.error("Could not find PL file space")
          return(None)
        else:
          self.logger.debug("Got PL filespace: " + filespace_ID)

        return(filespace_ID)


    def FileSpace_ID_generator(self,fileSpaces,searchItem):
        filespace_ID=""
        searchItem=searchItem.upper()
        for filespace in fileSpaces["filespaces"]:
#          print (filespace["title"])
          if filespace["title"].upper() == searchItem:
             filespaceID=filespace["fileSpaceId"]
             orgShortname=filespace["orgShortname"]
             yield (filespaceID,orgShortname)


    def Find_PL_IDs(self,filespaces):
        if filespaces == None:
            return (None)
        filespace_ID=""
        PL="Project Library".upper()
#        pprint(filespaces)
        for filespace in filespaces["filespaces"]:
        #   print filespace["title"]
          if filespace["title"].upper() == PL:
             filespace_ID=filespace["fileSpaceId"]
             break

        if filespace_ID=="":
          self.logger.error("Could not find PL file space")
          return(None)
        else:
          self.logger.debug("Got PL filespace: " + filespace_ID)

        return(filespace_ID)




    def Dir(self,filespace_ID,filemasklist="",recursive=True,path=""):

#        print("In Dir")
        try:
            if filemasklist != "":
    #           print(self.TCC_API + "Dir?recursive=" + str(recursive) + "&path=/" + path + "&filterfolders=true&filespaceId="+filespace_ID+"&filemasklist="+filemasklist)
               r=requests.get(self.TCC_API + "Dir?recursive=" + str(recursive) + "&path=/" + path + "&filterfolders=true&filespaceId="+filespace_ID+"&filemasklist="+filemasklist,cookies=self.login_cookies,timeout=300)
            else:
    #           print(self.TCC_API + "Dir?recursive=" + str(recursive) + "&path=/" + path + "&filterfolders=true&filespaceId="+filespace_ID)
               r=requests.get(self.TCC_API + "Dir?recursive=" + str(recursive) + "&path=/" + path + "&filterfolders=true&filespaceId="+filespace_ID,cookies=self.login_cookies,timeout=300)

            if r.status_code != 200:
               self.logger.error("Failed to get Dir: " + path + " Error Code ("+str(r.status_code)+")")
    #           pprint(r.json())
               return(None)
            else:
               return(r.json())
        except KeyboardInterrupt:
            raise
        except:
               return(None)


    def Download(self,filespace_ID,TCC_File,Local_FileName):
        chunk_size=1024*60

        if not self.Logged_In:
            raise ("Not Logged into TCC in Download")

        self.logger.debug("About to download: " + TCC_File + " to " + Local_FileName)

        try:
            r=requests.get(self.TCC_API +"files?filespaceid=" + filespace_ID + '&path=/'+urllib.parse.quote(TCC_File,'()'),stream=True,cookies=self.login_cookies,timeout=300)
        except KeyboardInterrupt:
            raise
        except:
            return(False)

        OK=None
        if r.status_code == 200:
           OK=True
           with open(Local_FileName, 'wb') as fd:
               try:
                   for chunk in r.iter_content(chunk_size):
                       fd.write(chunk)
               except KeyboardInterrupt:
                   raise
               except:
                   pass
           self.logger.debug("Downloaded: " + TCC_File + " to " + Local_FileName)
        else:
           OK=False
           self.logger.warning("Failed to download: " + TCC_File + " to " + Local_FileName)
        return (OK)



    def ticket(self):
        if not self.Logged_In:
            raise ("Not Logged into TCC in ticket")
        return(self.login_cookies["ticket"])

    def GetDevices(self,orgid=""):
        if orgid == "":
           r=requests.get(self.TCC_API + "GetDevices",cookies=self.login_cookies,timeout=300)
        else:
           r=requests.get(self.TCC_API + "GetDevices?orgid="+orgid,cookies=self.login_cookies,timeout=300)
        return(r.json())

    def GetLoginAccounts(self,orgid=""):
        if orgid == "":
           r=requests.get(self.TCC_API + "GetLoginAccounts",cookies=self.login_cookies,timeout=300)
        else:
           r=requests.get(self.TCC_API + "GetLoginAccounts?orgid="+orgid,cookies=self.login_cookies,timeout=300)
        return(r.json())

    def GetLoginAccount(self):
        r=requests.get(self.TCC_API + "GetLoginAccount?loginaccountid="+self.accountid,cookies=self.login_cookies,timeout=300)
        return(r.json())



    def GetOrganizationDashboard(self,orgtypefilter="",licensefilter="",orgtagfilter="",organizationProfiles="",membershipDetails="",deviceDetails="",groupDetails=""):
        self.logger.debug("About to Get Org Dashboard: " +self.TCC_API + "GetOrganizationDashboard?membershipDetails="+membershipDetails+"&deviceDetails="+deviceDetails+"&organizationProfiles="+organizationProfiles)
        r=requests.get(self.TCC_API + "GetOrganizationDashboard?membershipDetails="+membershipDetails+"&deviceDetails="+deviceDetails+"&organizationProfiles="+organizationProfiles,cookies=self.login_cookies,timeout=300)
        self.ORG_DETAILS=r.json()
        return(self.ORG_DETAILS)

    def UpdateDateTime(self,filespaceid,path,createTime=None,modifyTime=None):
        if createTime==None and modifyTime==None :
#            print datetime.utcnow()
#            print datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S.%f")
            createTime=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S.%f")
#            print modifyTime
            modifyTime=createTime
            self.logger.debug("UpdateDateTime, create and Modifytime not provided, set to now: {}".format(modifyTime))

        params={
          'filespaceid': filespaceid,
          'path': path,
          'createTime':createTime,
          'modifyTime':modifyTime
        }

        r=requests.get(self.TCC_API + "UpdateDateTime",cookies=self.login_cookies,params=params)

        return(r.json())


    def GetMountPoints(self,orgid,MountPointTypeFilter="",wantallpublic="",getinactive=""):
        if not self.Logged_In:
            raise ("Not Logged into TCC in Get Mountpoints")

        self.logger.debug("About to Get Org Mountpoints: " +self.TCC_API + "GetMountPoints?orgid="+orgid+"&MountPointTypeFilter="+MountPointTypeFilter+"&WantAllPublic="+wantallpublic+"&getinactive="+getinactive)
        r=requests.get(self.TCC_API + "GetMountPoints?orgid="+orgid+"&MountPointTypeFilter="+MountPointTypeFilter+"&WantAllPublic="+wantallpublic+"&getinactive="+getinactive,cookies=self.login_cookies,timeout=300)
        return(r.json())

    def GetMountPointConnectionList(self,mountpointid):
        if not self.Logged_In:
            raise ("Not Logged into TCC in GetMountPointConnectionList")

        self.logger.debug("About to GetMountPointConnectionList: " +self.TCC_API + "GetMountPointConnectionList?mountpointid="+mountpointid)
        r=requests.get(self.TCC_API + "GetMountPointConnectionList?mountpointid="+mountpointid,cookies=self.login_cookies,timeout=300)
        return(r.json())

    def GetMountPointDetails(self,mountpointid):
        if not self.Logged_In:
            raise ("Not Logged into TCC in GetMountPointDetails")

        self.logger.debug("About to GetMountPointDetails: " +self.TCC_API + "GetMountPointDetails?mountpointid="+mountpointid)
        r=requests.get(self.TCC_API + "GetMountPointDetails?mountpointid="+mountpointid,cookies=self.login_cookies,timeout=300)
        return(r.json())







