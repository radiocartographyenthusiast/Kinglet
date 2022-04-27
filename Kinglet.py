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
        self.iface2 = ""
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
            try:
                self.HomeWifiKey = lcfg['kinglet']['homewifikey']
                print("settings hWK " + self.HomeWifiKey)
            except:
                print("settings hWN not found")
            try:
                self.iface = lcfg['kinglet']['iface']
                print("settings iface " + self.iface)
            except:
                print("settings iface not found")
            try:
                self.iface2 = lcfg['kinglet']['iface2']
                print("settings iface2 " + self.iface)
            except:
                print("settings iface2 not found")


            self.TriggerDistance = lcfg['kinglet']['triggerdistance']
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
                outdata = "[" + xds.strftime("%X") + "], " + self.cpu_usage + ", " + self.mem_usage+ ", " + self.brd_temp + ", " + self.disk_percent + ",\n"
                outputFile.write(outdata)
                outputFile.close()
            except Exception as e:
                mylogger("Error writing to system telemetry log: " + str(e.__class__))
            time.sleep(3)
        print("myLogger.mySettings.PowerOn = False now") 

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
                        else:
                            if len(mySettings.iface2) > 0:
                                #recommend raspi onboard wifi as first interface and external as second
                                #iw dev scan hasn't worked on my external yet
                                startmoniface(mySettings.iface2)
                                apcmd = "sudo python3 " + os.getcwd() + "/sparrow-wifi/kinglet.py --interface " + mySettings.iface + "mon" + " --write " + mySettings.dumpFolder + " --iface2 " + mySettings.iface2
                            else:
                                apcmd = "sudo python3 " + os.getcwd() + "/sparrow-wifi/kinglet.py --interface " + mySettings.iface + "mon" + " --write " + mySettings.dumpFolder + " --nofalcon true"
                        apcmd = apcmd.split(' ')
                        #print(apcmd)
                        airoproc = subprocess.Popen(apcmd)
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
                        if len(mySettings.iface2) > 0:
                            stopmoniface(mySettings.iface2)
                        MonitorEnabled = False
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
    return render_template(
        'index.html',
        title='Home Page',
        year=datetime.datetime.now().year,
        GPSd_Status=myGPSButton.gstatus,
        GPSd_Color=myGPSButton.gcolor
    )
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
    try:
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
            print("Unimplemented: Change Settings\n")
            for fargs in request.form:
                print("farg: " + str(fargs) + "\n")
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
    except Exception as e:
        mylogger("[Exception][GPS--1]" + str(e.__class__))
        print("[Exception][GPS--1]" + str(e.__class__))
        #it's throwing an exception somewhere around this scope when run on startup and trying to access the settings page, so we're doing this jank
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
            GPSd_Status="❌",
            GPSd_Color="Crimson",
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
    airoproc = None
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