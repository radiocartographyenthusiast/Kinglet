""" requires:
    -python3
    -gpsd-py3
	-aircrack-ng suite
	-geopy
    -flask
 """
""" Todo:
	-blinkenlighten for pi
    -settings/config
    -flask
 """
 
#import block
import sys
import gpsd
import os
import time
import subprocess
import datetime
import threading
from geopy import distance, location
from flask import render_template
from flask import Flask
from os import environ
import configparser
import argparse
import waitress
import re
import tempfile
import contextlib
import shutil
from distutils.dir_util import copy_tree
import toml
import fs


#global var block
global mgrthread
global flaskthread
global airoproc
global telemthread
global mySettings
global kingletLinkActive

class MySettings:
    global PowerOn
    global SavedDataFilename
    global HomeWifiName
    global HomeWifiKey
    global TriggerDistance
    global HomeLat
    global HomeLon
    global useAirodump
    global WaitForLockBool
    global iface
    global iface2
    global noFalcon
    global dumpFolder
    global usezramfs
    def __init__(self):
        self.HomeLat = 0
        self.HomeLon = 0
        self.WaitForLockBool = True
        self.useAirodump = False
        self.noFalcon = False
        self.SavedDataFilename = "settings.deez"
        self.PowerOn = True
        self.iface = "wlan0"
        self.iface2 = "nil"
        self.dumpFolder = os.getcwd() + "/logs"
        self.usezramfs = False
        self.TriggerDistance = 10
        self.HomeWifiName = "dummy_ssid"
        if os.path.exists(self.SavedDataFilename):
            print("settings file found")
            lcfg = toml.load(self.SavedDataFilename) #loading
            print("settings loaded to mem")

            self.HomeLat = float(lcfg['kinglet']['hlat'])
            print("settings hLat " + str(self.HomeLat))

            self.HomeLon = float(lcfg['kinglet']['hlon'])
            print("settings hLon " + str(self.HomeLon))
            try:
                self.HomeWifiName = lcfg['kinglet']['homewifiname']
                print("settings hWN " + self.HomeWifiName)
            except:
                print("settings hWN not found")
                self.HomeWifiName = "dummy_ssid"
            try:
                self.HomeWifiKey = lcfg['kinglet']['homewifikey']
                print("settings hWK " + self.HomeWifiKey)
            except:
                print("settings hWN not found")
                self.HomeWifiKey = ""
            try:
                self.iface = lcfg['kinglet']['iface']
                print("settings iface " + self.iface)
            except:
                print("settings iface not found")
                self.iface = "wlan0"
            try:
                self.iface2 = lcfg['kinglet']['iface2']
                print("settings iface2 " + self.iface2)
            except:
                print("settings iface2 not found")
                self.iface2 = "nil"


            self.TriggerDistance = int(lcfg['kinglet']['triggerdistance'])
            print("settings tD " + str(self.TriggerDistance))

class GPSButton:
    global gstatus
    global gcolor
    def __init__(self):
        try:
            packet = gpsd.get_current()
            if packet.mode >= 2:
                self.gstatus = "🔒"
                self.gcolor = "Green"
            else:
                self.gstatus = "🔓"
                self.gcolor = "Red"
        except:
            self.gstatus = "None"
            self.gcolor = "Crimson"
            
class MyStatuses:
    global mgrthreadstatus
    global gpsdstatus
    global kstatus
    global flaskthreadstatus
    global telemthreadstatus
    def __init__(self):
        if telemthread.is_alive():
            self.telemthreadstatus = "✔"
        else:
            self.telemthreadstatus = "❌"
        if mgrthread:
            if mgrthread.is_alive():
                self.mgrthreadstatus = "✔"
            else:
                self.mgrthreadstatus = "❌"
        else:
            self.mgrthreadstatus = "❌"        
        if flaskthread.is_alive():
            self.flaskthreadstatus = "✔"
        else:
            flaskthreadstatus = "❌"
        if airoproc:
            if airoproc.poll() == None:
                self.kstatus = "✔"
        else:
            self.kstatus = "❌"
        try:
            p = subprocess.Popen(["pidof", "gpsd"], stdout=subprocess.PIPE)
            out, err = p.communicate()
            out2 = str(out).replace('\n', '')
            print(out2)
            print(str(len(out2)))
            if len(out2) > 3:
                self.gpsdstatus = "✔"
            else:
                self.gpsdstatus = "❌"
        except:
            self.gpsdstatus = "❌"

class MyTelemetryLogger(threading.Thread):
    global cpu_usage
    global mem_usage
    global brd_temp
    global telem_file_name
    global disk_percent
    def get_cpu_usage(self):
        cpup = str(round(float(os.popen('''grep 'cpu ' /proc/stat | awk '{usage=($2+$4)*100/($2+$4+$5)} END {print usage }' ''').readline()),2))
        return cpup+"%"
    def get_mem_usage(self):
        with open('/proc/meminfo') as fp:
            for line in fp:
                line = line.strip()
                if line.startswith("MemTotal:"):
                    kb_mem_total = int(line.split()[1])
                if line.startswith("MemFree:"):
                    kb_mem_free = int(line.split()[1])
                if line.startswith("Buffers:"):
                    kb_main_buffers = int(line.split()[1])
                if line.startswith("Cached:"):
                    kb_main_cached = int(line.split()[1])
            kb_mem_used = kb_mem_total - kb_mem_free - kb_main_cached - kb_main_buffers
            mpct = str(round(float(kb_mem_used / kb_mem_total), 2))
            return mpct + "%"
        return 0
    def get_brd_temp(self):
        with open('/sys/class/thermal/thermal_zone0/temp', 'rt') as fp:
            temp = int(fp.read().strip())
        c = int(temp / 1000)
        return (c * (9 / 5)) + 32
    def get_disk_percent(self):
        pcmd = "df -Pk"
        pcmd = pcmd.split(' ')
        p = subprocess.Popen(pcmd, stdout=subprocess.PIPE, shell=True)
        out, err = p.communicate()
        out = str(out)
        i = out.index("%")
        out = out[i+1:i+90]
        i = out.index("%")
        return str(out)[i-3:i+1]
    def __init__(self, mySettings):
        super(MyTelemetryLogger, self).__init__()
        self.cpu_usage = str(self.get_cpu_usage())
        self.mem_usage = str(self.get_mem_usage())
        self.brd_temp = str(self.get_brd_temp())
        self.disk_percent = str(self.get_disk_percent())
        now = datetime.datetime.now()
        snYear = str(now.year)
        snMonth = str(now.month)
        snDay = str(now.day)
        snHour = str(now.hour)
        snMin = str(now.minute)
        snSec = str(now.second)
        self.telem_file_name = mySettings.dumpFolder + "/session-" + snYear + "-" + snMonth + "-" + snDay + "_" + snHour + "_" + snMin + "_" + snSec + ".sessionlog"
        try:
            outputFile = open(self.telem_file_name, 'a')
            outputFile.write("[TIMESTAMP], CPU%, RAM%, TEMP, DISK%\n")
            outputFile.close()
        except:
            mylogger("Error writing to system telemetry log [INIT]")
    def run(self):
        while mySettings.PowerOn:
            try:
                outputFile = open(self.telem_file_name, 'a')
                xds = datetime.datetime.now()
                self.cpu_usage = self.get_cpu_usage()
                self.mem_usage = self.get_mem_usage()
                self.brd_temp = str(self.get_brd_temp())[0:5]+"F"
                self.disk_percent = str(self.get_disk_percent())
                try:
                    if kingletLinkActive:
                        netsSeen = airoproc.seenpastsec
                    else:
                        netsSeen = 0
                except:
                    netsSeen = -1
                outdata = "[" + xds.strftime("%X") + "], " + self.cpu_usage + ", " + self.mem_usage+ ", " + self.brd_temp + ", " + self.disk_percent + ",\n"
                outputFile.write(outdata)
                outputFile.close()
            except Exception as e:
                mylogger("Error writing to system telemetry log: " + str(e.__class__))
            time.sleep(3)
        print("myLogger.mySettings.PowerOn = False now") 

class MyDatabase():
    global exists
    global issetup
    global tmpTimeline #simple array of strings as follows, generated by reading lines from the log files
    #[[GUID](PK), [datetimestamp], macAddr, vendor, SSID, Security, Privacy, Channel, Frequency, Signal Strength, Strongest Signal Strength, Bandwidth, [Latitude, Longitude]]
    filename = os.getcwd() + "/kinglet.dbz"
    def __init__():
        if os.path.exists(filename):
            self.exists = True
            #next check if it's setup
        else:
            self.exists = False
            self.issetup = False
            #need to create and setup database
            #file backup table? centralized master timeline table?
        print("db unimplemented")
    def setupDatabase():
        print("db setup unimplemented")
    def loadDatabase():
        print("db loading unimplemented")
    def insertSingleEntryIntoCentralDb():
        #check if coord pair exists already in pointsTable, then add data to pointNetworks
        #[[Lat, Long](PK), Avg rssi, network count, entry count]
        
        #check if coord pair exists already in netsTable, then add data to latLonTable
        #[[GUID](PK), [datetimestamp], macAddr, vendor, SSID, Security, Privacy, Channel, Frequency, Signal Strength, Strongest Signal Strength, Bandwidth, [Latitude, Longitude]]
        
        print("db insertion unimplemented")
    def insertSingleEntryIntoNestedDb():
        print("db insertion unimplemented")
    def reconstructNestedDb():
        print("nested db reconstruction unimplemented")
    def calculateAverageRssi():
        print("rssi averaging unimplemented")
    def digestKingletLogs():
        #[[GUID](PK), [datetimestamp], macAddr, vendor, SSID, Security, Privacy, Channel, Frequency, Signal Strength, Strongest Signal Strength, Bandwidth, [Latitude, Longitude]]
        print("file digestion unimplemented")
    def digestFalconLogs():
        #double check what airodump's logs look like to put here for reference
        print("file digestion unimplemented")
    def generateKML():
        #generate KML file for heatmap
        print("KML generation unimplemented")

#defined functions
def startmoniface(inFace):
    os.system("sudo airmon-ng start "+ inFace)
    mylogger(inFace+"mon up")
def stopmoniface(inFace):
    os.system("sudo airmon-ng stop " + inFace)
    mylogger(inFace+"mon down")    
def mylogger(logd):
    xd = datetime.datetime.now()
    logfilename = "rce.log"
    logfile = open(logfilename, "a")
    logfile.write("[" + xd.strftime("%X") + "] | " + logd + "\r\n")
    logfile.close()
def synczfs():
    if mySettings.usezramfs:
        for m in fs.mounts:
            m.sync()
def shutdown():
    mySettings.PowerOn=False
    #sync and unmount zram if enabled
    synczfs()
    mgrthread.daemon = True
    os.system("sync")
    time.sleep(1)
    os.system("halt")
def hotRestart():
    mySettings.PowerOn=False
    synczfs()
    os.system("sync")
    time.sleep(1)
    os.system("sudo systemctl restart kinglet.service")
def coldRestart():
    mySettings.PowerOn=False
    #sync and unmount zram if enabled
    synczfs()
    mgrthread.daemon = True
    os.system("sync")
    time.sleep(1)
    os.system("sudo reboot")    
def initflask(mySettings):
    HOST = environ.get('SERVER_HOST', '0.0.0.0')
    try:
        PORT = int(environ.get('SERVER_PORT', '80'))
    except ValueError:
        PORT = 80
    mylogger("Proceeding to launch web ui")
    try:
        waitress.serve(app, host=HOST, port=PORT)
    except:
        print("Error launching web ui; kinglet will continue headlessly; try running the script with sudo")
        mylogger("Error launching web ui; kinglet will continue headlessly; try running the script with sudo")

#management thread with nested loop
def initstartup(mySettings):
    mylogger("Manager Thread Loop spooled up")
    xds = datetime.datetime.now()
    mylogger("[ " + xds.strftime("%x") + " ] | [ Initialized ]");
    #var block initialization again because python
    MonitorEnabled = False
    HomeWifiKey = None
    #gps initialization
    while mySettings.WaitForLockBool:
        try:
            gpsd.connect()
            packet = gpsd.get_current()
            if packet.mode >= 2:
                mylogger("GPS locked [1]")
                mySettings.WaitForLockBool = False
            else:
                mylogger("No lock")
                time.sleep(14)
            time.sleep(1)
        except Exception as e:
                mylogger("[Exception]" + str(e.__class__))
                print("[Exception]" + str(e.__class__))
            #mylogger("Exception Handling: GPS probably isn't active")
            #GPSd-py3 will tell us, no need
        time.sleep(5)

    
    #load home point if found, otherwise set SetHome to True                               #loading
    if os.path.exists(mySettings.SavedDataFilename):                                                  #loading
        SetHome = False
    else:
        SetHome = True
        mylogger("No home set; first run maybe?")
        print("No home set; first run maybe?")
    
    #main loop
    airoproc = None
    while mySettings.PowerOn:
#        try:
        packet = gpsd.get_current()
        if packet.mode >= 2:
            CurrentLocation = location.Point(packet.lat, packet.lon)
            #mylogger("GPS locked")
            #print("GPS locked [2]")
#                try:
            print(str(mySettings.HomeLat))
            if str(mySettings.HomeLat) == "0":
                print("HomeLat is 0")
                if SetHome:                                                            #saving
                    #print("about to set home")
                    HomeLocation = location.Point(packet.lat, packet.lon)
                    #print("about to save settings [1]")
                    #mylogger("savecfg unimplemented[1]")                              #saving
                    mySettings.HomeLat = packet.lat
                    #print("about to save settings [2]")
                    mySettings.HomeLon = packet.lon
                    #print("about to save settings [3]")
                    myCFG = configparser.ConfigParser()
                    myCFG['kinglet'] = { 'hLat': mySettings.HomeLat,
                                         'hLon': mySettings.HomeLon,
                                         'triggerDistance': mySettings.TriggerDistance }
                    #print("about to save settings [4]")
                    try:
                        with open(mySettings.SavedDataFilename, 'w') as configfile:
                            myCFG.write(configfile)
                    except:
                        mylogger("error generating config")
                        print("error generating config")

                    mylogger(mySettings.SavedDataFilename + " created or updated")                #saving
                    print(mySettings.SavedDataFilename + " created or updated")                #saving
                    SetHome = False                          #saving
                else:
                    print("SetHome is False; HomeLat is 0; " + str(HomeLocation))
            else:
                #print("HomeLat not 0; "  + str(mySettings.HomeLat))
                curdistance = distance.distance(CurrentLocation, location.Point(mySettings.HomeLat, mySettings.HomeLon)).feet
                if curdistance > mySettings.TriggerDistance:                                             #DISTANCE IN FEET TO ACTIVATE AIRODUMP
                    #mylogger("Away from HomeLocation; " + str(packet.lat) + ", " + str(packet.lon) + "; Distance: " + str(curdistance) + "ft")
                    #we are away from the home
                    if MonitorEnabled == False:
                        #we aren't monitoring, we must be leaving
                        print("Starting monitor mode on " + mySettings.iface)
                        startmoniface(mySettings.iface)
                        MonitorEnabled = True
                        if mySettings.useAirodump:
                            apcmd = "sudo airodump-ng --gpsd -w " + mySettings.dumpFolder + " --manufacturer --wps --output-format kismet " + mySettings.iface + "mon"
                            mylogger("[os] " + apcmd)
                            apcmd = apcmd.split(' ')
                            airoproc = subprocess.Popen(apcmd)
                            mylogger("[os] launched")
                        else:
                            if len(mySettings.iface2) > 3:
                                #recommend raspi onboard wifi as first interface and external as second
                                #iw dev scan hasn't worked on my external yet
                                startmoniface(mySettings.iface2)
                                #airoproc = kingletLink()
                                #kingletLink.iface = mySettings.iface
                                #kingletLink.iface2 = mySettings.iface2
                                #kingletLink.dumpLoc = mySettings.dumpFolder
                                apcmd = "sudo python3 " + os.getcwd() + "/sparrow-wifi/kinglet.py --interface " + mySettings.iface + "mon" + " --iface2 " + mySettings.iface2 + "mon"
                                mylogger("[os] " + apcmd)
                                apcmd = apcmd.split(' ')
                                airoproc = subprocess.Popen(apcmd)
                                airoproc.run()
                                mylogger("[os] launched")
                            else:
                                #airoproc = kingletLink()
                                #kingletLink.iface = mySettings.iface
                                #kingletLink.dumpLoc = mySettings.dumpFolder
                                apcmd = "sudo python3 " + os.getcwd() + "/sparrow-wifi/kinglet.py --interface " + mySettings.iface + "mon" + " --nofalcon true"
                                mylogger("[os] " + apcmd)
                                apcmd = apcmd.split(' ')
                                airoproc = subprocess.Popen(apcmd)
                                airoproc.run()
                                mylogger("[os] launched")
                            #kingletLinkActive = True
                        
                        #print(apcmd)
                        
                        if mySettings.useAirodump:
                            mylogger('airodump-ng launched')
                        else:
                            mylogger('kinglet.py launched')

                    time.sleep(59)
                else:
                    #mylogger("Near HomeLocation; " + str(packet.lat) + ", " + str(packet.lon) + "; Distance: " + str(curdistance) + "ft")
                    #we are near or at home
                    if MonitorEnabled:
                        #we are monitoring, we must be returning
                        #terminate airodump process
                        airoproc.terminate()
                        stopmoniface(mySettings.iface)
                        if len(mySettings.iface2) > 3:
                            stopmoniface(mySettings.iface2)
                        MonitorEnabled = False
                        #kingletLinkActive = False
                        #reconnect to home wifi
                        if mySettings.HomeWifiName != "dummy_ssid":
                            os.system(f'''cmd /c "netsh wlan connect name = {mySettings.HomeWifiName}"''')
                    time.sleep(29)
            time.sleep(1)
        else:
            #mylogger("No lock")
            time.sleep(15)
#        except:
#            mylogger("GPSd might be pitching a fit again")
#            time.sleep(15)

app = Flask(__name__)
from flask import request

@app.route('/')
@app.route('/home')
@app.route('/index')
def home():
    """Renders the home page."""
    myGPSButton = GPSButton()
    myStatuses = MyStatuses()
    
    if str(mySettings.HomeLat) == "0":
        retx = "38.9150327"
        rety = "-77.0117685"
        retz = "12"
    else:
        retx = str(mySettings.HomeLat)
        rety = str(mySettings.HomeLon)
        retz = "18"
    return render_template(
        'index.html',
        title='Radiomaps Я Us',
        year=datetime.datetime.now().year,
        GPSd_Status=myGPSButton.gstatus,
        GPSd_Color=myGPSButton.gcolor,
        telemstat=myStatuses.telemthreadstatus,
        mgrstat=myStatuses.mgrthreadstatus,
        flaskstat=myStatuses.flaskthreadstatus,
        kingletstat=myStatuses.kstatus,
        gpsdstat=myStatuses.gpsdstatus,
        retx=retx,
        rety=rety,
        retz=retz)
@app.route('/gps-status')
def gps_status():
    """Renders the about page."""
    myGPSButton = GPSButton()
    myStatuses = MyStatuses()
    try:
        packet = gpsd.get_current()
        CurrentLocation = location.Point(packet.lat, packet.lon)
        if mySettings.HomeLat != 0:
            howfar = distance.distance(CurrentLocation, location.Point(mySettings.HomeLat, mySettings.HomeLon)).feet
            gshLoc = location.Point(mySettings.HomeLat, mySettings.HomeLon)
        else:
            howfar = 0
            gshLoc = "Uninitialized"
        return render_template(
            'gps-status.html',
            title='Telemetry',
            year=datetime.datetime.now().year,
            GPSd_Status=myGPSButton.gstatus,
            GPSd_Color=myGPSButton.gcolor,
            GPS_lat = str(packet.lat),
            GPS_lon = str(packet.lon),
            GPS_mode = str(packet.mode),
            HomeLoc=gshLoc,
            CurDist=howfar,
            CurLoc=CurrentLocation,
            telemstat=myStatuses.telemthreadstatus,
            mgrstat=myStatuses.mgrthreadstatus,
            flaskstat=myStatuses.flaskthreadstatus,
            kingletstat=myStatuses.kstatus,
            gpsdstat=myStatuses.gpsdstatus)
    except:
        return render_template(
            'gps-status.html',
            title='Telemetry',
            year=datetime.datetime.now().year,
            GPSd_Status=myGPSButton.gstatus,
            GPSd_Color=myGPSButton.gcolor,
            GPS_lat = str(0.0),
            GPS_lon = str(0.0),
            GPS_mode = str(0),
            HomeLoc="Uninitialized",
            CurDist="unknown",
            CurLoc="Exceptional",
            telemstat=myStatuses.telemthreadstatus,
            mgrstat=myStatuses.mgrthreadstatus,
            flaskstat=myStatuses.flaskthreadstatus,
            kingletstat=myStatuses.kstatus,
            gpsdstat=myStatuses.gpsdstatus)
@app.route('/settings', methods=['GET', 'POST'])
def settingspage():
    fcnt = 0
    try:
        wdir = mySettings.dumpFolder
        for path in os.listdir(wdir):
            if os.path.isfile(os.path.join(wdir, path)):
                if "kismet" in path:
                    fcnt += 1
    except:
        fcnt = 0
    ccnt = 0
    try:
        wdir = mySettings.dumpFolder
        for path in os.listdir(wdir):
            if os.path.isfile(os.path.join(wdir, path)):
                if ".csv" in path:
                    ccnt += 1
    except:
        ccnt = 0
    myGPSButton = GPSButton()
    if request.method == 'POST':
        #print("Unimplemented: Change Settings\n")
        newConfig = "[kinglet]\n"
        print("Making new config")
        retdl = mySettings.dumpFolder
        if request.form.get('inputHomeLat'):
            print("new home lat")
            mySettings.HomeLat = float(request.form.get('inputHomeLat')) #update if new, otherwise write current
            newConfig += 'hlat = ' + request.form.get('inputHomeLat') + '\n'

        if request.form.get('inputHomeLon'):
            print("new home lon")
            mySettings.HomeLon = float(request.form.get('inputHomeLon')) #update if new, otherwise write current
            newConfig += 'hlon = ' + request.form.get('inputHomeLon') + '\n'
        
        if request.form.get('inputHomeSid'):
            mySettings.HomeWifiName = request.form.get('inputHomeSid') #update if new, otherwise write current
            newConfig += 'homewifiname = ' + request.form.get('inputHomeSid') + '\n'
        try:
            if request.form.get('inputHomeKey'):
                mySettings.HomeWifiKey = request.form.get('inputHomeKey') #update if new, otherwise write current
                newConfig += 'homewifikey = ' + request.form.get('inputHomeKey') + '\n'
                retwfk = request.form.get('inputHomeKey')
            else:
                retwfk = "?"
        except:
            print("hwk err")
            retwfk = "err"
        if request.form.get('inputTrigDist'):
            mySettings.TriggerDistance = int(request.form.get('inputTrigDist')) #update if new, otherwise write current
            newConfig += 'triggerdistance = ' + request.form.get('inputTrigDist') + '\n'
        
        if request.form.get('inputiFace'):
            mySettings.iface = request.form.get('inputiFace') #update if new, otherwise write current
            newConfig += 'iface = ' + request.form.get('inputiFace') + '\n'
        
        if request.form.get('inputiFace2'):
            mySettings.iface2 = request.form.get('inputiFace2') #update if new, otherwise write current
            newConfig += 'iface2 = ' + request.form.get('inputiFace2') + '\n'
        
        retloc = "Testing"#str(location.Point(mySettings.HomeLat, mySettings.HomeLon))
        try:
            savedcfg = open(mySettings.SavedDataFilename, 'w')
            savedcfg.write(newConfig)
            savedcfg.close()
        except:
            mylogger("error generating config [web]")
            print("error generating config [web]")
        return render_template(
                'settings.html',
                title='Settings',
                year=datetime.datetime.now().year,
                GPSd_Status=myGPSButton.gstatus,
                GPSd_Color=myGPSButton.gcolor,
                dumpfolder=retdl,
                klogcnt=str(fcnt),
                csvcnt=str(ccnt),
                totcnt=str(fcnt+ccnt),
                HomeLoc=retloc,
                HomeSSID=mySettings.HomeWifiName,
                HomeKey=retwfk,
                HomeLati=str(mySettings.HomeLat),
                HomeLong=str(mySettings.HomeLon),
                triggerDistance=str(mySettings.TriggerDistance),
                message = "Settings updated successfully!")
    elif request.method == "GET":
        try:
            print("Getting settings page")
            if str(mySettings.HomeLat) == "0":
                retloc = "Uninitialized"
                retla = "Uninitialized"
                retlo = "Uninitialized"
                retwfn = "Uninitialized"
                retwfk = "Uninitialized"
                retd = "Uninitialized"
                retdl = "Uninitialized"
                print("Uninit settings")
            else:
                retloc = str(location.Point(mySettings.HomeLat, mySettings.HomeLon))
                #print("retloc")
                retla = str(mySettings.HomeLat)
                #print("retla")
                retlo = str(mySettings.HomeLon)
                #print("retlo")
                try:
                    retwfn = mySettings.HomeWifiName
                except:
                    retwfn = ""
                #print("retwfn")
                try:
                    retwfk = mySettings.HomeWifiKey
                except:
                    retwfk = ""
                #print("retwfk")
                try:
                    retd = mySettings.triggerDistance
                except:
                    retd = 10
                #print("retd")
                retdl = mySettings.dumpFolder
                #print("retdl")
            return render_template(
                'settings.html',
                title='Settings',
                year=datetime.datetime.now().year,
                GPSd_Status=myGPSButton.gstatus,
                GPSd_Color=myGPSButton.gcolor,
                dumpfolder=retdl,
                klogcnt=str(fcnt),
                csvcnt=str(ccnt),
                totcnt=str(fcnt+ccnt),
                HomeLoc=retloc,
                HomeSSID=retwfn,
                HomeKey=retwfk,
                HomeLati=retla,
                HomeLong=retlo,
                triggerDistance=retd, 
                iFace = mySettings.iface,
                iFace2 = mySettings.iface2)
        except Exception as e:
            mylogger("[Exception][GPS--2]" + str(e.__class__))
            print("[Exception][GPS--2]" + str(e.__class__))
            retloc = "Uninitialized"
            retla = "Uninitialized"
            retlo = "Uninitialized"
            retwfn = "Uninitialized"
            retwfk = "Uninitialized"
            retd = "Uninitialized"
            retdl = "Uninitialized"
            return render_template(
                'settings.html',
                title='Settings',
                year=datetime.datetime.now().year,
                GPSd_Status=myGPSButton.gstatus,
                GPSd_Color=myGPSButton.gcolor,
                dumpfolder=retdl,
                klogcnt=str(fcnt),
                csvcnt=str(ccnt),
                totcnt=str(fcnt+ccnt),
                HomeLoc=retloc,
                HomeSSID=retwfn,
                HomeKey=retwfk,
                HomeLati=retla,
                HomeLong=retlo,
                triggerDistance=retd)

#main
if __name__ == '__main__':
    #u-blox7/VK172 config commands
    #os.system("echo -e -n \"\\xB5\\x62\\x06\\x08\\x06\\x00\\xF4\\x01\\x01\\x00\\x01\\x00\" > /dev/ttyACM0") #cfg-rate 2Hz
    #os.system("echo -e -n \"\\xB5\\x62\\x06\\x24\\x24\\x00\\xFF\\xFF\\x03\\x03\\x00\\x00\\x00\\x00\\x10\\x27\\x00\\x00\\x05\\x00\\xFA\\x00\\xFA\\x00\\x64\\x00\\x2C\\x01\\x00\\x3C\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\" > /dev/ttyACM0") #cfg-nav pedestrian
    
    dirname, filename = os.path.split(os.path.abspath(__file__))
    if dirname not in sys.path:
        sys.path.insert(0, dirname)
    sparrowdir = dirname+'/sparrow-wifi'    
    if sparrowdir not in sys.path:
            sys.path.insert(0,sparrowdir)
    from kinglet import kingletLink
    
    airoproc = None
    kingletLinkActive = False
    mySettings = MySettings()
    mySettings.PowerOn = True
    argparser = argparse.ArgumentParser(description='')
    argparser.add_argument('--airodump', help="Use airodump-ng instead of Sparrow-WiFi (Ex: python3 Kinglet.py --airodump true)", default='', required=False)
    argparser.add_argument('--iface', help="Wireless interface to use (Ex: python3 Kinglet.py --iface wlan0)", default='', required=False)
    argparser.add_argument('--iface2', help="Secondary Wireless interface to use (Ex: python3 Kinglet.py --iface2 wlan1)[Experimental Falcon Support (Basically just runs airodump-ng on the second interface)]", default='', required=False)
    argparser.add_argument('--nofalcon', help="Don't load Falcon plugin (Ex: python3 Kinglet.py --nofalcon true)", default='', required=False)
    argparser.add_argument('--usezram', help="Use zram fs to prolong microsd (Ex: python3 Kinglet.py --usezram true)[Experimental]", default='', required=False)
    args = argparser.parse_args()
    telemthread = MyTelemetryLogger(mySettings)
    telemthread.start()
    #initstartup()
    if len(args.nofalcon) > 0:
        mySettings.noFalcon = True
    if args.airodump == 'true':
        mySettings.useAirodump = True
    if len(args.iface) > 0:
        mySettings.iface = args.iface
    if len(args.iface2) > 0:
        mySettings.iface2 = args.iface2
    if args.usezram:
        mySettings.usezramfs = True
        fs.setup_mounts(mySettings.dumpFolder)
        
    mgrthread = threading.Thread(target=initstartup, args=[mySettings])
    mgrthread.start()
#    mgrthread = None
    flaskthread = threading.Thread(target=initflask, args=[mySettings])
    flaskthread.start()
#    initflask(mySettings)
#    print(str(PowerOn))
#    initstartup(mySettings)
#    while(PowerOn):
#        inp = input()
#        if inp == "q":
#            PowerOn = False
