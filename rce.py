""" requires:
    -python3
    -gpsd-py3
	-aircrack-ng suite
	-geofencing YTD
 """
""" Todo:
	-blinkenlighten for pi
	-airodump manager
	-geofencing
 """
 
#import block
import gpsd
import os
import time
import subprocess
from geopy import distance, location

#global var block
PowerOn = False
WaitForLockBool = False
MonitorEnabled = False
HomeLocation = None
SetHome = False

#definitions
def startmoniface():
    os.system("sudo ./monstart.sh")
    MonitorEnabled = True
    print("mon0 up")
    #tested, works
def stopmoniface():
    os.system("sudo ./monstop.sh")
    MonitorEnabled = False
    print("mon0 down")
    #yet to be implemented, should work    
def gpsinit():
    WaitForLockBool = True
    while WaitForLockBool:
        try:
            gpsd.connect()
            packet = gpsd.get_current()
            if packet.mode >= 2:
                print("GPS locked")
                WaitForLockBool = False
            else:
                print("No lock")
            time.sleep(1)
        except:
            #print("Exception Handling: GPS probably isn't active")
            #GPSd-py3 will tell us, no need
            time.sleep(1)
            
def loadcfg():
    print("loadcfg unimplemented")
    #load home point if found, otherwise set SetHome to True
def savecfg():
    print("savecfg unimplemented")
    #save home point
    
    
def mainloop():
    PowerOn = True
    while PowerOn:
        packet = gpsd.get_current()
        CurrentLocation = location.point(packet.lat, packet.lon)
        if packet.mode >= 2:
            #print("GPS locked")
            #Check against geofence, then enable or disable monitor mode
            if HomeLocation == None:
                if SetHome:
                    HomeLocation = CurrentLocation
            else:
                curdistance = distance.distance(CurrentLocation, HomeLocation).feet
                if curdistance > 20:
                #we are away from the home
                    if MonitorEnabled == False:
                    #we aren't monitoring, we must be leaving
                        monstart()
                else:
                #we are near the home
                    if MonitorEnabled:
                    #we are monitoring, we must be returning
                        monstop()
                time.sleep(1)
        else:
            #print("No lock")
            time.sleep(1)

def initstartup():
    gpsinit()
    loadcfg()
    #mainloop()

#main
if __name__ == '__main__':
    initstartup()
