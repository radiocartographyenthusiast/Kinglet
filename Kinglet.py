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


#global var block
global mgrthread
global flaskthread
global airoproc
global telemthread

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
    global usezramfs
    def __init__(self):
        self.WaitForLockBool = True
        self.useAirodump = False
        self.noFalcon = False
        self.SavedDataFilename = "settings.deez"
        self.PowerOn = True
        self.iface = "wlan0"
        self.dumpFolder = os.getcwd() + "/logs"
        self.usezramfs = False
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
        if mgrthread.is_alive():
            self.mgrthreadstatus = "✔"
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
    def _cpu_stat(self):
        """
        Returns the splitted first line of the /proc/stat file
        """
        with open('/proc/stat', 'rt') as fp:
            return list(map(int,fp.readline().split()[1:]))
    def get_cpu_usage(self):
        """
        Returns the current cpuload
        """
        parts0 = self._cpu_stat()
        time.sleep(0.1)
        parts1 = self._cpu_stat()
        parts_diff = [p1 - p0 for (p0, p1) in zip(parts0, parts1)]
        user, nice, sys, idle, iowait, irq, softirq, steal, _guest, _guest_nice = parts_diff
        idle_sum = idle + iowait
        non_idle_sum = user + nice + sys + irq + softirq + steal
        total = idle_sum + non_idle_sum
        return non_idle_sum / total
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
            return round(kb_mem_used / kb_mem_total, 1)
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
                self.cpu_usage = str(self.get_cpu_usage())[0:4]+"%"
                self.mem_usage = str(self.get_mem_usage())+"%"
                self.brd_temp = str(self.get_brd_temp())[0:5]+"F"
                self.disk_percent = str(self.get_disk_percent())
                outdata = "[" + xds.strftime("%X") + "], " + self.cpu_usage + ", " + self.mem_usage+ ", " + self.brd_temp + ", " + self.disk_percent + ",\n"
                outputFile.write(outdata)
                outputFile.close()
            except Exception as e:
                mylogger("Error writing to system telemetry log: " + str(e.__class__))
            time.sleep(1)
        print("myLogger.mySettings.PowerOn = False now") 

class ExperimentalFS():
    mounts = list()

    @contextlib.contextmanager
    def ensure_write(filename, mode='w'):
        path = os.path.dirname(filename)
        fd, tmp = tempfile.mkstemp(dir=path)

        with os.fdopen(fd, mode) as f:
            yield f
            f.flush()
            os.fsync(f.fileno())

        os.replace(tmp, filename)
    def size_of(path):
        """
        Calculate the sum of all the files in path
        """
        total = 0
        for root, _, files in os.walk(path):
            for f in files:
                total += os.path.getsize(os.path.join(root, f))
        return total
    def is_mountpoint(path):
        """
        Checks if path is mountpoint
        """
        return os.system(f"mountpoint -q {path}") == 0
    def setup_mounts(config):
        """
        Sets up all the configured mountpoints
        """
        global mounts
        fs_cfg = config
        mylogger("[FS] Trying to setup mount %s (%s)", name, fs_cfg)
        size,unit = re.match(r"(\d+)([a-zA-Z]+)", "100M").groups()
        target = os.path.join('/run/pwnagotchi/disk/', fs_cfg)
        is_mounted = is_mountpoint(target)
        mylogger("[FS] %s is %s mounted", fs_cfg,
                      "already" if is_mounted else "not yet")
        m = MemoryFS(
            fs_cfg,
            target,
            size="100M",
            zram=True,
            zram_disk_size=f"{int(size)*2}{unit}",
            rsync=True)
        if not is_mounted:
            if not m.mount():
                mylogger(f"Error while mounting {m.mountpoint}")

            if not m.sync(to_ram=True):
                mylogger(f"Error while syncing to {m.mountpoint}")
                m.umount()

        interval = 60
        if interval:
            mylogger("[FS] Starting thread to sync %s (interval: %d)",
                        fs_cfg, interval)
            _thread.start_new_thread(m.daemonize, (interval,))
        else:
            mylogger("[FS] Not syncing %s, because interval is 0",
            fs_cfg)
        mounts.append(m)
    class MemoryFS:
        @staticmethod
        def zram_install():
            if not os.path.exists("/sys/class/zram-control"):
                mylogger("[FS] Installing zram")
                return os.system("modprobe zram") == 0
            return True
        @staticmethod
        def zram_dev():
            mylogger("[FS] Adding zram device")
            return open("/sys/class/zram-control/hot_add", "rt").read().strip("\n")
        def __init__(self, mount, disk, size="40M",
                     zram=True, zram_alg="lz4", zram_disk_size="100M",
                     zram_fs_type="ext4", rsync=True):
            self.mountpoint = mount
            self.disk = disk
            self.size = size
            self.zram = zram
            self.zram_alg = zram_alg
            self.zram_disk_size = zram_disk_size
            self.zram_fs_type = zram_fs_type
            self.zdev = None
            self.rsync = True
            self._setup()
        def _setup(self):
            if self.zram and MemoryFS.zram_install():
                # setup zram
                self.zdev = MemoryFS.zram_dev()
                open(f"/sys/block/zram{self.zdev}/comp_algorithm", "wt").write(self.zram_alg)
                open(f"/sys/block/zram{self.zdev}/disksize", "wt").write(self.zram_disk_size)
                open(f"/sys/block/zram{self.zdev}/mem_limit", "wt").write(self.size)
                mylogger("[FS] Creating fs (type: %s)", self.zram_fs_type)
                os.system(f"mke2fs -t {self.zram_fs_type} /dev/zram{self.zdev} >/dev/null 2>&1")
            # ensure mountpoints exist
            if not os.path.exists(self.disk):
                mylogger("[FS] Creating %s", self.disk)
                os.makedirs(self.disk)
            if not os.path.exists(self.mountpoint):
                mylogger("[FS] Creating %s", self.mountpoint)
                os.makedirs(self.mountpoint)
        def daemonize(self, interval=60):
            mylogger("[FS] Daemonized...")
            while True:
                self.sync()
                time.sleep(interval)
        def sync(self, to_ram=False):
            source, dest = (self.disk, self.mountpoint) if to_ram else (self.mountpoint, self.disk)
            needed, actually_free = size_of(source), shutil.disk_usage(dest)[2]
            if actually_free >= needed:
                mylogger("[FS] Syncing %s -> %s", source,dest)
                if self.rsync:
                    os.system(f"rsync -aXv --inplace --no-whole-file --delete-after {source}/ {dest}/ >/dev/null 2>&1")
                else:
                    copy_tree(source, dest, preserve_symlinks=True)
                os.system("sync")
                return True
            return False
        def mount(self):
            if os.system(f"mount --bind {self.mountpoint} {self.disk}"):
                return False
            if os.system(f"mount --make-private {self.disk}"):
                return False
            if self.zram and self.zdev is not None:
                if os.system(f"mount -t {self.zram_fs_type} -o nosuid,noexec,nodev,user=rad /dev/zram{self.zdev} {self.mountpoint}/"):
                    return False
            else:
                if os.system(f"mount -t tmpfs -o nosuid,noexec,nodev,mode=0755,size={self.size} rad {self.mountpoint}/"):
                    return False
            return True
        def umount(self):
            if os.system(f"umount -l {self.mountpoint}"):
                return False

            if os.system(f"umount -l {self.disk}"):
                return False
            return True

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
        waitress.serve(app, host=HOST, port=PORT)
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
    myStatuses = MyStatuses()
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
            CurLoc=CurrentLocation,
            
            mgrstat=myStatuses.mgrthreadstatus,
            flaskstat=myStatuses.flaskthreadstatus,
            kingletstat=myStatuses.kstatus,
            gpsdstat=myStatuses.gpsdstatus)
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
                if len(mySettings.HomeLat) > 0:
                    retloc = location.Point(mySettings.HomeLat, mySettings.HomeLon)
                    retla = mySettings.HomeLat
                    retlo = mySettings.HomeLon
                    retwfn = mySettings.HomeWifiName
                    retwfk = mySettings.HomeWifiKey
                    retd = mySettings.triggerDistance
                    retdl = mySettings.dumpFolder
                else:
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
                    klogcnt=fcnt,
                    csvcnt=ccnt,
                    totcnt=fcnt+ccnt,
                    HomeLoc=retloc,
                    HomeSSID=retwfn,
                    HomeKey=retwfk,
                    HomeLati=retla,
                    HomeLong=retlo,
                    triggerDistance=retd)
            except Exception as e:
                mylogger("[Exception]" + str(e.__class__))
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
                    klogcnt=fcnt,
                    csvcnt=ccnt,
                    totcnt=fcnt+ccnt,
                    HomeLoc=retloc,
                    HomeSSID=retwfn,
                    HomeKey=retwfk,
                    HomeLati=retla,
                    HomeLong=retlo,
                    triggerDistance=retd)
    except Exception as e:
        mylogger("[Exception]" + str(e.__class__))
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
            GPSd_Status=myGPSButton.gstatus,
            GPSd_Color=myGPSButton.gcolor,
            dumpfolder=retdl,
            klogcnt=fcnt,
            csvcnt=ccnt,
            totcnt=fcnt+ccnt,
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
    argparser.add_argument('--iface', help="Monitor mode interface to use (Ex: python3 Kinglet.py --iface mon1)", default='', required=False)
    argparser.add_argument('--nofalcon', help="Don't load Falcon plugin (Ex: python3 Kinglet.py --nofalcon true)", default='', required=False)
    argparser.add_argument('--usezram', help="Use zram fs to prolong microsd (Ex: python3 Kinglet.py --usezram true)", default='', required=False)
    args = argparser.parse_args()
    #initstartup()
    if len(args.nofalcon) > 0:
        mySettings.noFalcon = True
    if args.airodump == 'true':
        mySettings.useAirodump = True
    if len(args.iface) > 0:
        mySettings.iface = args.iface
    if args.usezram:
        mySettings.usezramfs = True
        ExperimentalFS.setup_mounts(mySettings.dumpFolder)
    telemthread = MyTelemetryLogger(mySettings)
    telemthread.start()
    mgrthread = threading.Thread(target=initstartup, args=[mySettings])
    mgrthread.start()
    flaskthread = threading.Thread(target=initflask, args=[mySettings], daemon=True)
    flaskthread.start()
#    initflask(mySettings)
#    print(str(PowerOn))
#    while(PowerOn):
#        inp = input()
#        if inp == "q":
#            PowerOn = False