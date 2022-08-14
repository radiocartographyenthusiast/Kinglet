#!/usr/bin/python3
#
# Copyright 2022
#
# This is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3, or (at your option)
# any later version.
#
# This software is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this software; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street,
# Boston, MA 02110-1301, USA.

"""
Reqs: 
-python-dateutil
-gps3
"""

import os
import sys
from datetime import datetime
import json
import re

import argparse
import configparser
# import subprocess
import sqlite3

from socket import *
from time import sleep
from threading import Thread, Lock
from dateutil import parser
from socketserver import ThreadingMixIn

from wirelessengine import WirelessEngine
from sparrowgps import GPSEngine, GPSEngineStatic,  GPSStatus,  SparrowGPS

from sparrowrpi import SparrowRPi
from sparrowcommon import gzipCompress

runningcfg = None
recordThread = None
iface2 = None

# ------------------  Config Settings  ------------------------------
class AConfigSettings():
    global recordInterface
    global recordRunning
    global cancelStart
    global dumpLoc
    def __init__(self):
        self.cancelStart = False
        self.recordInterface="wlan0mon"
        self.recordRunning = False
        self.dumpLoc = ""


try:
    from manuf import manuf
    hasOUILookup = True
except:
    hasOUILookup = False

# ------   Global setup ------------
gpsEngine = None
curTime = datetime.now()
lockList = {}
noFalcon = False

# ------   Global functions ------------
def stringtobool(instr):
    if (instr == 'True' or instr == 'true'):
        return True
    else:
        return False
def TwoDigits(instr):
    # Fill in a leading zero for single-digit numbers
    while len(instr) < 2:
        instr = '0' + instr

    return instr
def startRecord(interface, dumpLoc):
    global recordThread

    if recordThread:
        return

    if len(interface) > 0:
        interfaces = WirelessEngine.getInterfaces()

        if interface in interfaces:
            recordThread = AutoAgentScanThread(interface, dumpLoc)
            recordThread.start()
        else:
            print('ERROR: Record was requested on ' + interface + ' but that interface was not found.')
    else:
        recordThread = None
def stopRecord():
    global recordThread

    if recordThread:
        recordThread.signalStop = True
        print('Waiting for record thread to terminate...')

        i=0
        maxCycles = 2 /0.2
        while (recordThread.threadRunning) and (i<maxCycles):
            sleep(0.2)
            i += 1


# ------   OUI lookup functions ------------
def getOUIDB():
    ouidb = None

    if hasOUILookup:
        if  os.path.isfile('manuf'):
            # We have the file but let's not update it every time we run the app.
            # every 90 days should be plenty
            last_modified_date = datetime.datetime.fromtimestamp(os.path.getmtime('manuf'))
            now = datetime.datetime.now()
            age = now - last_modified_date

            if age.days > 90:
                updateflag = True
            else:
                updateflag = False
        else:
            # We don't have the file, let's get it
            updateflag = True

        try:
            ouidb = manuf.MacParser(update=updateflag)
        except:
            ouidb = None
    else:
        ouidb = None

    return ouidb

# ------------------  File  ------------------------------
class FileSystemFile(object):
    def __init__(self):
        self.filename = ""
        self.size = 0
        self.timestamp = None

    def __str__(self):
        retVal = self.filename

        return retVal

    def toJsondict(self):
        jsondict = {}
        jsondict['filename'] = self.filename
        jsondict['size'] = self.size
        jsondict['timestamp'] = str(self.timestamp)

        return jsondict

    def fromJsondict(self, jsondict):
        self.filename = jsondict['filename']
        self.size = jsondict['size']

        if jsondict['timestamp'] == 'None':
            self.timestamp = None
        else:
            self.timestamp = parser.parse(jsondict['timestamp'])
# ------------------  Agent auto scan thread  ------------------------------
class AutoAgentScanThread(Thread):
#    global eventick
    global curcnt
    global lastcnt
    global seenpastsec
    global dbcon
    def __init__(self, interface, dumpLoc):
        global lockList
        eventick = False
        super(AutoAgentScanThread, self).__init__()
        self.interface = interface
        self.signalStop = False
        self.scanDelay = 0.5  # seconds
        self.threadRunning = False
        self.discoveredNetworks = {}
        self.daemon = False

        try:
            self.hostname = os.uname()[1]
        except:
            self.hostname = 'unknown'

        if len(self.hostname) == 0:
            self.hostname = 'unknown'

        self.ouiLookupEngine = getOUIDB()

        if interface not in lockList.keys():
            lockList[interface] = Lock()

        saveloc = dumpLoc
        if  not os.path.exists(saveloc):
            os.makedirs(saveloc)

        now = datetime.now()

        self.filename = saveloc + '/wifi-+'
        
        dbcon = sqlite3.connect('kinglet.dbz')

        print('Capturing on ' + interface + ' and writing wifi to sqlite3')

    def run(self):
        
        global lockList
        print("agent thread running")
        self.threadRunning = True

        if self.interface not in lockList.keys():
            lockList[self.interface] = Lock()

        curLock = lockList[self.interface]

        lastState = -1

        while (not self.signalStop):
            # Scan all / normal mode
            if (curLock):
                #print("acquiring lock")
                curLock.acquire()
            retCode, errString, wirelessNetworks = WirelessEngine.scanForNetworks(self.interface)
            if (curLock):
                #print("releasing lock")
                curLock.release()
            #print("retCode: " + str(retCode) + "; errString: " + errString)
            if (retCode == 0):
                if gpsEngine.gpsValid():
                    gpsCoord = gpsEngine.lastCoord
                    print("GPS updated")
                else:
                    gpsCoord = GPSStatus()
                # self.statusBar().showMessage('Scan complete.  Found ' + str(len(wirelessNetworks)) + ' networks')
                self.curcnt = len(wirelessNetworks)
                if wirelessNetworks and (self.curcnt > 0) and (not self.signalStop):
                    for netKey in wirelessNetworks.keys():
                        curNet = wirelessNetworks[netKey]
                        #print("Seen " + str(curNet))
                        curNet.gps.copy(gpsCoord)
                        curNet.strongestgps.copy(gpsCoord)
                        curKey = curNet.getKey()
                        if curKey not in self.discoveredNetworks.keys():
                            self.discoveredNetworks[curKey] = curNet
                        else:
                            # Network exists, need to update it.
                            pastNet = self.discoveredNetworks[curKey]
                            # Need to save strongest gps and first seen.  Everything else can be updated.
                            # Carry forward firstSeen
                            curNet.firstSeen = pastNet.firstSeen # This is one field to carry forward
                            # Check strongest signal
                            if pastNet.strongestsignal > curNet.signal:
                                curNet.strongestsignal = pastNet.strongestsignal
                                curNet.strongestgps.latitude = pastNet.strongestgps.latitude
                                curNet.strongestgps.longitude = pastNet.strongestgps.longitude
                                curNet.strongestgps.altitude = pastNet.strongestgps.altitude
                                curNet.strongestgps.speed = pastNet.strongestgps.speed
                                curNet.strongestgps.isValid = pastNet.strongestgps.isValid
                            self.discoveredNetworks[curKey] = curNet
                    if not self.signalStop:
                        #print("Attempting to export network list")
                        self.exportNetworks()
#            if self.eventick:
#                self.seenpastsec = self.lastcnt + self.curcnt
#                self.eventick = False
#            else:
#                self.lastcnt = self.curcnt
#                self.eventick = True
            sleep(self.scanDelay)
        self.threadRunning = False
        print("agent thread exiting")
    def ouiLookup(self, macAddr):
        clientVendor = ""
        if hasOUILookup:
            try:
                if self.ouiLookupEngine:
                    clientVendor = self.ouiLookupEngine.get_manuf(macAddr)
            except:
                clientVendor = ""
        return clientVendor
    def exportNetworks(self):
        #self.outputFile.write('[timestamp],macAddr,vendor,SSID,Security,Privacy,Channel,Frequency,Signal Strength,Strongest Signal Strength,Bandwidth,Latitude,Longitude,\n')
        for netKey in self.discoveredNetworks.keys():
            curData = self.discoveredNetworks[netKey]
            vendor = self.ouiLookup(curData.macAddr)
            if curData.ssid == "":
                curData.ssid = "[nsi]"
            if vendor is None:
                vendor = '[unk]'
            cur = dbcon.cursor()
            cur.execute('insert into kingletItems values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', (
                str(datetime.now()),
                curData.macAddr,
                vendor,
                curData.ssid,
                curData.security,
                curData.privacy, 
                curData.getChannelString(),
                str(curData.frequency),
                str(curData.signal),
                str(curData.strongestsignal),
                str(curData.bandwidth),
                str(curData.gps.latitude),
                str(curData.gps.longitude) ) )
            con.commit()
            #add to sqlite3 kingletItems here
            
        #self.outputFile.close()

class kingletLink:
    global iface
    global iface2
    global dumpLoc
    def __init__():
        seenpastsec = 0
        iface = ""
        iface2 = ""
        dumpLoc = ""
    def run():
        runningcfg = AConfigSettings()
        runningcfg.dumpLoc = self.dumpLoc
        if len(args.interface) >= 4:
            runningcfg.recordInterface = self.iface
            startRecord(runningcfg.recordInterface, runningcfg.dumpLoc)
        if len(iface2) >= 4:
            iface2 = self.iface2
            from falconwifi import FalconWiFiRemoteAgent, WPAPSKCrack, WEPCrack
            hasFalcon = True
            falconWiFiRemoteAgent = FalconWiFiRemoteAgent()
            falconWiFiRemoteAgent.startCapture(iface2, runningcfg.dumpLoc)
    def terminate():
        stopRecord()
        for curKey in lockList.keys():
            curLock = lockList[curKey]
        try:
            curLock.release()
        except:
            pass
    def seenPastSec():
        return falconWiFiRemoteAgent.seenpastsec

# ----------------- Main -----------------------------
if __name__ == '__main__':
    argparser = argparse.ArgumentParser(description='Kinglet Sparrow-wifi agent')
    argparser.add_argument('--staticcoord', help="Use user-defined lat,long,altitude(m) rather than GPS.  Ex: 40.1,-75.3,150", default='', required=False)
    argparser.add_argument('--interface', help="Primary wireless interface", default='wlan0mon', required=False)
    argparser.add_argument('--delaystart', help="Wait <delaystart> seconds before initializing", default=0, required=False)
    argparser.add_argument('--nofalcon', help="Don't load Falcon plugin (Ex: python3 kinglet.py --nofalcon true)", default='', required=False)
    argparser.add_argument('--write', help="Folder to dump logs into (Ex: python3 kinglet.py --write /home/rad)", default='', required=False)
    argparser.add_argument('--iface2', help="Secondary Wireless interface, used by Falcon (Ex: python3 kinglet.py --iface2 wlan1)[Experimental]", default='', required=False)
    args = argparser.parse_args()

    if len(args.nofalcon) > 0:
        noFalcon = True
    if len(args.staticcoord) > 0:
        coord_array = args.staticcoord.split(",")
        if len(coord_array) < 3:
            print("ERROR: Provided static coordinates are not in the format latitude,longitude,altitude.")
            exit(1)
        usingStaticGPS = True
        gpsEngine = GPSEngineStatic(float(coord_array[0]), float(coord_array[1]), float(coord_array[2]))
    else:
        usingStaticGPS = False
        gpsEngine = GPSEngine()

    if os.geteuid() != 0:
        print("ERROR: You need to have root privileges to run this script.  Please try again, this time using 'sudo'. Exiting.\n")
        exit(2)

    # Code to add paths
    dirname, filename = os.path.split(os.path.abspath(__file__))

    if dirname not in sys.path:
        sys.path.insert(0, dirname)

    runningcfg = AConfigSettings()
    # Now start logic
    if len(args.write)>0:
        runningcfg.dumpLoc = args.write
    else:
        runningcfg.dumpLoc = os.getcwd() + "/logs"
    # Check the local GPS.
    if GPSEngine.GPSDRunning():
        gpsEngine.start()
        if usingStaticGPS:
            print('[' +curTime.strftime("%m/%d/%Y %H:%M:%S") + "] Using static lat/long/altitude(m): " + args.staticcoord)
        else:
            print('[' +curTime.strftime("%m/%d/%Y %H:%M:%S") + "] Local gpsd Found.  Providing GPS coordinates when synchronized.")
    else:
        print('[' +curTime.strftime("%m/%d/%Y %H:%M:%S") + "] No local gpsd running.  No GPS data will be provided.")
    if len(args.interface) > 0:
        runningcfg.recordInterface = args.interface
    startRecord(runningcfg.recordInterface, runningcfg.dumpLoc)

    # Check for Falcon offensive plugin
    pluginsdir = dirname+'/plugins'
    if  os.path.exists(pluginsdir):
        if pluginsdir not in sys.path:
            sys.path.insert(0,pluginsdir)
        if  os.path.isfile(pluginsdir + '/falconwifi.py'):
            if not noFalcon:
                from falconwifi import FalconWiFiRemoteAgent, WPAPSKCrack, WEPCrack
                hasFalcon = True
                falconWiFiRemoteAgent = FalconWiFiRemoteAgent()
                if len(args.iface2) > 0:
                    iface2 = args.iface2
                    falconWiFiRemoteAgent.startMonitoringInterface(iface2)
                    falconWiFiRemoteAgent.startCapture(iface2, runningcfg.dumpLoc)
                else:
                    print("Please specify iface2 for falcon to use")
                if not falconWiFiRemoteAgent.toolsInstalled():
                    print("ERROR: aircrack suite of tools does not appear to be installed.  Please install it.")
                    exit(4)
    
    # -------------- This is the shutdown process --------------
    #stopRecord()

    #for curKey in lockList.keys():
    #    curLock = lockList[curKey]
    #    try:
    #        curLock.release()
    #    except:
    #        pass

    # os._exit(0)
    #exit(0)
