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

#global var block
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
    global noFalcon
    global dumpFolder
    def __init__(self):
        self.WaitForLockBool = True
        self.useAirodump = False
        self.noFalcon = False
        self.SavedDataFilename = "settings.deez"
        self.PowerOn = True
        self.iface = "wlan0"
        self.dumpFolder = os.getcwd() + "/logs"
        if os.path.exists(self.SavedDataFilename):                                                  #loading
            savedsettings = configparser.ConfigParser(self.SavedDataFilename)            #loading         
            try:
                savedsettings.read(self.SavedDataFilename)
                options = savedsettings.options("airotool")
                for option in options:
                    try:
                        if option =='hLat':
                            self.HomeLat = cfgParser.get(section, option)
                        elif option == 'hLon':
                            self.HomeLon = cfgParser.get(section, option)
                        elif option == 'homeWifiName':
                            self.HomeWifiName = cfgParser.get(section, option)
                        elif option == 'homeWifiKey':
                            self.HomeWifiKey=cfgParser.get(section, option)
                        elif option == 'triggerDistance':
                            self.TriggerDistance=cfgParser.get(section, option)
                    except:
                        print("exception on %s!" % option)
            except:
                print("ERROR: Unable to read config file: ", self.SavedDataFilename)

class GPSButton:
    global gstatus
    global gcolor
    def __init__(self):
        try:
            packet = gpsd.get_current()
            if packet.mode >= 2:
                self.gstatus = "Locked"
                self.gcolor = "Green"
            else:
                self.gstatus = "Unlocked"
                self.gcolor = "Red"
        except:
            self.gstatus = "None"
            self.gcolor = "Crimson"

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
def getklogcnt():
    iklogcnt = 0
    wdir = mySettings.dumpFolder
    for path in os.listdir(wdir):
        if os.path.isfile(os.path.join(wdir, path)):
            if"kismet" in path:
                iklogcnt += 1
    return iklogcnt
def getcsvcnt():
    icsvcnt = 0
    wdir = mySettings.dumpFolder
    for path in os.listdir(wdir):
        if os.path.isfile(os.path.join(wdir, path)):
            if ".csv" in path:
                icsvcnt += 1
    return icsvcnt
    
#management thread with nested loop
def initstartup(mySettings):
    mylogger("Manager Thread Loop spooled up")
    xds = datetime.datetime.now()
    mylogger("[ " + xds.strftime("%x") + " ] | [ Initialized ]");
    #var block initialization again because python
    mySettings.PowerOn = False
    MonitorEnabled = False
    SetHome = False
    HomeWifiKey = None
    #gps initialization
    while mySettings.WaitForLockBool:
        try:
            gpsd.connect()
            packet = gpsd.get_current()
            if packet.mode >= 2:
                mylogger("GPS locked")
                mySettings.WaitForLockBool = False
            else:
                mylogger("No lock")
                time.sleep(14)
            time.sleep(1)
        except:
            #mylogger("Exception Handling: GPS probably isn't active")
            #GPSd-py3 will tell us, no need
            time.sleep(5)

    
    #load home point if found, otherwise set SetHome to True                               #loading
    if os.path.exists(mySettings.SavedDataFilename):                                                  #loading
        SetHome = False
    else:
        SetHome = True
        mylogger("No home set; first run maybe?")
    
    #main loop
    mySettings.PowerOn = True
    airoproc = None
    while mySettings.PowerOn:
        try:
            packet = gpsd.get_current()
            CurrentLocation = location.Point(packet.lat, packet.lon)
            if packet.mode >= 2:
                #mylogger("GPS locked")
                #Check against geofence, then enable or disable monitor mode
                try:
                    if mySettings.HomeLat == None:
                        mylogger("HomeLat is None")
                        if SetHome:                                                            #saving
                            HomeLocation = CurrentLocation                                     #saving
                            #mylogger("savecfg unimplemented[1]")                              #saving
                            myCFG = configparser.ConfigParser()
                            myCFG['airotool'] = { 'hLat': mySettings.HomeLat,
                                                  'hLon': mySettings.HomeLon,
                                                  'homeWifiName': mySettings.HomeWifiName,
                                                  'homeWifiKey': mySettings.HomeWifiKey,
                                                  'triggerDistance': mySettings.TriggerDistance }
                            try:
                                with open(mySettings.SavedDataFilename, 'w') as configfile:
                                    myCFG.write(configfile)
                            except:
                                mylogger("error generating config")

                            mylogger(mySettings.SavedDataFilename + " created or updated")                #saving
                            SetHome = False                                                    #saving
                    else:
                        curdistance = distance.distance(CurrentLocation, location.Point(mySettings.HomeLat, mySettings.HomeLon)).feet
                        if curdistance > mySettings.TriggerDistance:                                             #DISTANCE IN FEET TO ACTIVATE AIRODUMP
                            #mylogger("Away from HomeLocation; " + str(packet.lat) + ", " + str(packet.lon) + "; Distance: " + str(curdistance) + "ft")
                            #we are away from the home
                            if MonitorEnabled == False:
                                #we aren't monitoring, we must be leaving
                                startmoniface()
                                MonitorEnabled = True
                                apcmd = None
                                if mySettings.useAirodump:
                                    apcmd = "sudo airodump-ng --gpsd -w " + mySettings.dumpFolder + " --manufacturer --wps --output-format kismet " + mySettings.iface + "mon"
                                else:
                                    apcmd = "sudo python3 " + os.getcwd() + "/sparrow-wifi/kinglet.py --interface " + mySettings.iface + "mon" + " --write " + mySettings.dumpFolder + " --nofalcon true"
                                apcmd = apcmd.split(' ')
                                try:
                                    airoproc = subprocess.Popen(apcmd)
                                    if mySettings.useAirodump:
                                        mylogger('airodump-ng launched')
                                    else:
                                        mylogger('kinglet.py launched')
                                except:
                                    mylogger('Error launching monitor app')
                            time.sleep(59)
                        else:
                            #mylogger("Near HomeLocation; " + str(packet.lat) + ", " + str(packet.lon) + "; Distance: " + str(curdistance) + "ft")
                            #we are near or at home
                            if MonitorEnabled:
                                #we are monitoring, we must be returning
                                #terminate airodump process
                                airoproc.terminate()
                                stopmoniface()
                                MonitorEnabled = False
                                #reconnect to home wifi
                                if mySettings.HomeWifiName != "dummy_ssid":
                                    os.system(f'''cmd /c "netsh wlan connect name = {mySettings.HomeWifiName}"''')
                            time.sleep(29)
                    time.sleep(1)
                except:
                    #Control + C was pressed
                    mySettings.PowerOn = False
                    mylogger("\nHasta la bon voyage")
                    print("\nHasta la bon voyage")
                    if MonitorEnabled:
                        #we are monitoring, we must be returning
                        #terminate airodump process
                        airoproc.terminate()
                        stopmoniface()
                        MonitorEnabled = False
            else:
                #mylogger("No lock")
                time.sleep(15)
        except:
            mylogger("GPSd might be pitching a fit again")
            time.sleep(15)

def initflask(mySettings):
    HOST = environ.get('SERVER_HOST', '0.0.0.0')
    try:
        PORT = int(environ.get('SERVER_PORT', '80'))
    except ValueError:
        PORT = 80
    mylogger("Proceeding to launch web ui")
    try:
        app.run(HOST, PORT)
    except:
        print("Error launching web ui; airotool will continue headlessly; try running the script with sudo")
        mylogger("Error launching web ui; airotool will continue headlessly; try running the script with sudo")


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
    try:
        packet = gpsd.get_current()
        CurrentLocation = location.Point(packet.lat, packet.lon)
        howfar = distance.distance(CurrentLocation, location.Point(mySettings.HomeLat, mySettings.HomeLon)).feet
        return render_template(
            'gps-status.html',
            title='Telemetry',
            year=datetime.datetime.now().year,
            GPSd_Status=myGPSButton.gstatus,
            GPSd_Color=myGPSButton.gcolor,
            GPS_lat = str(packet.lat),
            GPS_lon = str(packet.lon),
            GPS_mode = str(packet.mode),
            HomeLoc=location.Point(mySettings.HomeLat, mySettings.HomeLon),
            CurDist=howfar,
            CurLoc=CurrentLocation)
    except:
        return render_template(
            'gps-status.html',
            title='Telemetry',
            year=datetime.datetime.now().year,
            GPSd_Status="None",
            GPSd_Color="Crimson",
            GPS_lat = str(0.0),
            GPS_lon = str(0.0),
            GPS_mode = str(0),
            HomeLoc="null?",
            CurDist="unknown",
            CurLoc="Exceptional")

@app.route('/settings', methods=['GET', 'POST'])
def settingspage():
    myGPSButton = GPSButton()
    fcnt = getklogcnt()
    ccnt = getcsvcnt()
    retmsg = None
    if request.method == 'POST':
        if request.form.get("inputDumpFolder"):
            newDumpLoc = request.form.get("inputDumpFolder")
        if request.form.get("inputHomeLat"):
            mySettings.HomeLat = request.form.get("inputHomeLat")
        if request.form.get("inputHomeLon"):
            mySettings.HomeLon = request.form.get("inputHomeLon")
        if request.form.get("inputHomeSid"):
            mySettings.HomeWifiName = request.form.get("inputHomeSid")
        if request.form.get("inputHomeKey"):
            mySettings.HomeWifiKey = request.form.get("inputHomeKey")
        if request.form.get("inputTrigDist"):
            mySettings.TriggerDistance = request.form.get("inputTrigDist")
        #save settings
        if mySettings:
            newHomeLocation = location.Point(mySettings.HomeLat, mySettings.HomeLon)
            myCFG = configparser.ConfigParser()
            myCFG['airotool'] = { 'hLat': mySettings.HomeLat,
                                  'hLon': mySettings.HomeLon,
                                  'homeWifiName': mySettings.HomeWifiName,
                                  'homeWifiKey': mySettings.HomeWifiKey,
                                  'triggerDistance': mySettings.TriggerDistance }
            try:
                with open(mySettings.SavedDataFilename, 'w') as configfile:
                    myCFG.write(configfile)
                retmsg = "Settings updated successfully"
                mylogger(retmsg)
            except:
                retmsg = "Error updating settings"
                mylogger(retmsg)
        #render whole page since I don't know how to do simpler; I guess modals are what I'm really wanting?
        return render_template(
            'settings.html',
            title='Settings',
            year=datetime.datetime.now().year,
            GPSd_Status=myGPSButton.gstatus,
            GPSd_Color=myGPSButton.gcolor,
            dumpfolder=dumpFolder,
            klogcnt=fcnt,
            csvcnt=ccnt,
            totcnt=fcnt+ccnt,
            HomeLoc=location.Point(mySettings.HomeLat, mySettings.HomeLon),
            HomeSSID=mySettings.HomeWifiName,
            HomeKey=mySettings.HomeWifiKey,
            HomeLati=mySettings.HomeLat,
            HomeLong=mySettings.HomeLon,
            triggerDistance=mySettings.TriggerDistance,
            message=retmsg)
    elif request.method == "GET":
        try:
            retloc = location.Point(mySettings.HomeLat, mySettings.HomeLon)
            return render_template(
                'settings.html',
                title='Settings',
                year=datetime.datetime.now().year,
                GPSd_Status=myGPSButton.gstatus,
                GPSd_Color=myGPSButton.gcolor,
                dumpfolder=mySettings.dumpFolder,
                klogcnt=fcnt,
                csvcnt=ccnt,
                totcnt=fcnt+ccnt,
                HomeLoc=retloc,
                HomeSSID=mySettings.HomeWifiName,
                HomeKey=mySettings.HomeWifiKey,
                HomeLati=mySettings.HomeLat,
                HomeLong=mySettings.HomeLon,
                triggerDistance=mySettings.TriggerDistance)
        except:
            return render_template(
                'settings.html',
                title='Settings - Uninitialized',
                year=datetime.datetime.now().year,
                GPSd_Status=myGPSButton.gstatus,
                GPSd_Color=myGPSButton.gcolor,
                dumpfolder=mySettings.dumpFolder,
                klogcnt=fcnt,
                csvcnt=ccnt,
                totcnt=fcnt+ccnt,
                HomeLoc="Uninitialized",
                HomeSSID="Uninitialized",
                HomeKey="Uninitialized",
                HomeLati="Uninitialized",
                HomeLong="Uninitialized",
                triggerDistance="Uninitialized")

#main
if __name__ == '__main__':
    mySettings = MySettings()
    argparser = argparse.ArgumentParser(description='')
    argparser.add_argument('--airodump', help="Use airodump-ng instead of Sparrow-WiFi (Ex: python3 Kinglet.py --airodump true)", default='', required=False)
    argparser.add_argument('--iface', help="Monitor mode interface to use (Ex: python3 Kinglet.py --iface mon1)", default='', required=False)
    argparser.add_argument('--nofalcon', help="Don't load Falcon plugin (Ex: python3 Kinglet.py --nofalcon true)", default='', required=False)
    args = argparser.parse_args()
    #initstartup()
    if len(args.nofalcon) > 0:
        mySettings.noFalcon = True
    if args.airodump == 'true':
        mySettings.useAirodump = True
    if len(args.iface) > 0:
        mySettings.iface = args.iface
    mgrthread = threading.Thread(name="manager", target=initstartup, args=[mySettings])
    mgrthread.start()
    flaskthread = threading.Thread(name="flask", target=initflask, args=[mySettings], daemon=True)
    flaskthread.start()
#    print(str(PowerOn))
#    while(PowerOn):
#        inp = input()
#        if inp == "q":
#            PowerOn = False