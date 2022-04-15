""" requires:
    -python3
    -gpsd-py3
	-aircrack-ng suite
	-geopy
 """
""" Todo:
	-blinkenlighten for pi
	-airodump manager
    -settings/config
    -flask
 """
 
#import block
import gpsd
import os
import time
import subprocess
import datetime
from geopy import distance, location

#global var block
PowerOn = False
WaitForLockBool = False
MonitorEnabled = False
HomeLocation = None
SetHome = False
SavedDataFilename = "settings.deez"
HomeWifiName = None
HomeWifiKey = None

#definitions
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
    
def initstartup():
    xds = datetime.datetime.now()
    mylogger("[ " + xds.strftime("%x") + " ] | [ Initialized ]");
    #var block initialization again because python
    PowerOn = False
    MonitorEnabled = False
    HomeLocation = None
    SetHome = False
    SavedDataFilename = "settings.deez"
    HomeWifiName = None
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
    if os.path.exists(SavedDataFilename):                                                  #loading
        loaded = open(SavedDataFilename)                                                   #loading
        hlat = float(loaded.readline())                                                    #loading
        hlon = float(loaded.readline())                                                    #loading
        HomeWifiName = loaded.readline()                                                   #loading
#        HomeWifiKey = loaded.readline()                                                    #loading
        #mylogger("Loaded data: " + loaded)                                                #loading
        mylogger("Loaded latitude: " + str(hlat) + ", " + "loaded longitude: " + str(hlon))#loading
        loaded.close()                                                                     #loading
        HomeLocation = location.Point(hlat, hlon)                                          #loading
    else:
        SetHome = True
        mylogger("No home set; first run maybe?")
    
    #main loop
    PowerOn = True
    airoproc = None
    while PowerOn:
        try:
            packet = gpsd.get_current()
            CurrentLocation = location.Point(packet.lat, packet.lon)
            if packet.mode >= 2:
                #mylogger("GPS locked")
                #Check against geofence, then enable or disable monitor mode
                try:
                    if HomeLocation == None:
                        mylogger("HomeLocation is None")
                        if SetHome:                                                            #saving
                            HomeLocation = CurrentLocation                                     #saving
                            #mylogger("savecfg unimplemented[1]")                              #saving
                            mylogger(str(packet.lat) + ", " + str(packet.lon))                 #saving
                            #mylogger(HomeLocation)                                            #saving
                            #PowerOn = False                                                   #saving
                            saving = open(SavedDataFilename, 'w')                              #saving
                            saving.write(str(packet.lat) + "\r\n")                             #saving
                            saving.write(str(packet.lon) + "\r\n")                             #saving
                            saving.close()                                                     #saving
                            mylogger(SavedDataFilename + " created or updated")                #saving
                            SetHome = False                                                    #saving
                    else:
                        curdistance = distance.distance(CurrentLocation, HomeLocation).feet
                        if curdistance > 20:
                            mylogger("Away from HomeLocation; " + str(packet.lat) + ", " + str(packet.lon) + "; Distance: " + str(curdistance) + "ft")
                            #we are away from the home
                            if MonitorEnabled == False:
                                #stop flask if it's running
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
                                if HomeWifiName != None:
                                    os.system(f'''cmd /c "netsh wlan connect name = {HomeWifiName}"''')
                                #start flask
                            time.sleep(4)
                    time.sleep(1)
                except:
                    #Control + C was pressed
                    PowerOn = False
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


#main
if __name__ == '__main__':
    initstartup()
