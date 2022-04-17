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

#global var block
class MySettings:
    PowerOn = False
    HomeLocation = None
    SavedDataFilename = "settings.deez"
    HomeWifiName = None
    HomeLat = None
    HomeLon = None

#defined functions
def startmoniface():
    os.system("sudo ./monstart.sh")
    mylogger("mon0 up")
def stopmoniface():
    os.system("sudo ./monstop.sh")
    mylogger("mon0 down")    
def mylogger(logd):
    xd = datetime.datetime.now()
    logfilename = "rce.log"
    logfile = open(logfilename, "a")
    logfile.write("[" + xd.strftime("%X") + "] | " + logd + "\r\n")
    logfile.close()
def get_gps_status():
    try:
        packet = gpsd.get_current()
        if packet.mode >= 2:
            return "Locked"
        else:
            return "Unlocked"
    except:
        return "None"
def getklogcnt():
    iklogcnt = 0
    wdir = os.getcwd()
    for path in os.listdir(wdir):
        if os.path.isfile(os.path.join(wdir, path)):
            if"kismet" in path:
                iklogcnt += 1
    return iklogcnt

#management thread with nested loop
def initstartup():
    mylogger("Manager Thread Loop spooled up")
    xds = datetime.datetime.now()
    mylogger("[ " + xds.strftime("%x") + " ] | [ Initialized ]");
    #var block initialization again because python
    MySettings.PowerOn = False
    MonitorEnabled = False
    MySettings.HomeLocation = None
    SetHome = False
    HomeWifiKey = None
    #gps initialization
    WaitForLockBool = True
    while WaitForLockBool:
        try:
            gpsd.connect()
            packet = gpsd.get_current()
            if packet.mode >= 2:
                mylogger("GPS locked")
                WaitForLockBool = False
            else:
                mylogger("No lock")
                time.sleep(14)
            time.sleep(1)
        except:
            #mylogger("Exception Handling: GPS probably isn't active")
            #GPSd-py3 will tell us, no need
            time.sleep(5)

    
    #load home point if found, otherwise set SetHome to True                               #loading
    if os.path.exists(MySettings.SavedDataFilename):                                                  #loading
        loaded = open(MySettings.SavedDataFilename)                                                   #loading
        hlat = float(loaded.readline())                                                    #loading
        hlon = float(loaded.readline())                                                    #loading
        MySettings.HomeWifiName = loaded.readline()                                                   #loading
#        HomeWifiKey = loaded.readline()                                                    #loading
        #mylogger("Loaded data: " + loaded)                                                #loading
        mylogger("Loaded latitude: " + str(hlat) + ", " + "loaded longitude: " + str(hlon))#loading
        loaded.close()                                                                     #loading
        MySettings.HomeLocation = location.Point(hlat, hlon)                                          #loading
        MySettings.HomeLat = hlat
        MySettings.HomeLon = hlon
    else:
        SetHome = True
        mylogger("No home set; first run maybe?")
    
    #main loop
    MySettings.PowerOn = True
    airoproc = None
    while MySettings.PowerOn:
        try:
            packet = gpsd.get_current()
            CurrentLocation = location.Point(packet.lat, packet.lon)
            if packet.mode >= 2:
                #mylogger("GPS locked")
                #Check against geofence, then enable or disable monitor mode
                try:
                    if MySettings.HomeLocation == None:
                        mylogger("HomeLocation is None")
                        if SetHome:                                                            #saving
                            MySettings.HomeLocation = CurrentLocation                                     #saving
                            #mylogger("savecfg unimplemented[1]")                              #saving
                            mylogger(str(packet.lat) + ", " + str(packet.lon))                 #saving
                            #mylogger(HomeLocation)                                            #saving
                            #MySettings.PowerOn = False                                                   #saving
                            saving = open(MySettings.SavedDataFilename, 'w')                              #saving
                            saving.write(str(packet.lat) + "\r\n")                             #saving
                            saving.write(str(packet.lon) + "\r\n")                             #saving
                            saving.write("dummy_ssid")                                         #saving
                            saving.close()                                                     #saving
                            mylogger(MySettings.SavedDataFilename + " created or updated")                #saving
                            SetHome = False                                                    #saving
                    else:
                        curdistance = distance.distance(CurrentLocation, MySettings.HomeLocation).feet
                        if curdistance > 20:
                            mylogger("Away from HomeLocation; " + str(packet.lat) + ", " + str(packet.lon) + "; Distance: " + str(curdistance) + "ft")
                            #we are away from the home
                            if MonitorEnabled == False:
                                #we aren't monitoring, we must be leaving
                                startmoniface()
                                MonitorEnabled = True
                                #start airodump process
                                apcmd = "sudo airodump-ng --gpsd -w rce --manufacturer --wps --output-format kismet wlan0mon"
                                apcmd = apcmd.split(' ')
                                airoproc = subprocess.Popen(apcmd, stdout=subprocess.PIPE)
                            time.sleep(4)
                        else:
                            mylogger("Near HomeLocation; " + str(packet.lat) + ", " + str(packet.lon) + "; Distance: " + str(curdistance) + "ft")
                            #we are near or at home
                            if MonitorEnabled:
                                #we are monitoring, we must be returning
                                #terminate airodump process
                                airoproc.terminate()
                                stopmoniface()
                                MonitorEnabled = False
                                #reconnect to home wifi
                                if MySettings.HomeWifiName != "dummy_ssid":
                                    os.system(f'''cmd /c "netsh wlan connect name = {MySettings.HomeWifiName}"''')
                            time.sleep(4)
                    time.sleep(1)
                except:
                    #Control + C was pressed
                    MySettings.PowerOn = False
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
                time.sleep(1)
        except:
            mylogger("GPSd might be pitching a fit again")
            time.sleep(5)

def initflask():
    if os.path.exists(MySettings.SavedDataFilename):                                                  #loading
        loaded = open(MySettings.SavedDataFilename)                                                   #loading
        hlat = float(loaded.readline())                                                    #loading
        hlon = float(loaded.readline())                                                    #loading
        MySettings.HomeWifiName = loaded.readline()                                                   #loading
        loaded.close()                                                                     #loading
        MySettings.HomeLocation = location.Point(hlat, hlon)                                          #loading
        MySettings.HomeLat = hlat
        MySettings.HomeLon = hlon

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

@app.route('/')
@app.route('/home')
@app.route('/index')
def home():
    """Renders the home page."""
    gstatus = get_gps_status()
    if gstatus == "Locked":
        gcolor = "Green"
    else:
        gcolor = "Red"
    return render_template(
        'index.html',
        title='Home Page',
        year=datetime.datetime.now().year,
        GPSd_Status=gstatus,
        GPSd_Color=gcolor
    )

@app.route('/gps-status')
def gps_status():
    """Renders the about page."""
    gstatus = get_gps_status()
    if gstatus == "Locked":
        gcolor = "Green"
    else:
        gcolor = "Red"
    packet = gpsd.get_current()
    CurrentLocation = location.Point(packet.lat, packet.lon)
    howfar = distance.distance(CurrentLocation, MySettings.HomeLocation).feet
    return render_template(
        'gps-status.html',
        title='GPS Status',
        year=datetime.datetime.now().year,
        GPSd_Status=gstatus,
        GPSd_Color=gcolor,
        GPS_lat = str(packet.lat),
        GPS_lon = str(packet.lon),
        GPS_mode = str(packet.mode),
        HomeLoc=MySettings.HomeLocation,
        CurDist=howfar,
        CurLoc=CurrentLocation
    )

@app.route('/settings')
def settingspage():
    gstatus = get_gps_status()
    fcnt = getklogcnt()
    
    if gstatus == "Locked":
        gcolor = "Green"
    else:
        gcolor = "Red"
    return render_template(
        'settings.html',
        title='Settings Page',
        year=datetime.datetime.now().year,
        GPSd_Status=gstatus,
        GPSd_Color=gcolor,
        klogcnt=fcnt,
        HomeLoc=MySettings.HomeLocation,
        HomeSSID=MySettings.HomeWifiName,
        HomeLati=MySettings.HomeLat,
        HomeLong=MySettings.HomeLon
    )

#main
if __name__ == '__main__':
    #initstartup()
    mgrthread = threading.Thread(name="manager", target=initstartup)
    mgrthread.start()
    flaskthread = threading.Thread(name="flask", target=initflask, daemon=True)
    flaskthread.start()
#    print(str(PowerOn))
#    while(PowerOn):
#        inp = input()
#        if inp == "q":
#            PowerOn = False
