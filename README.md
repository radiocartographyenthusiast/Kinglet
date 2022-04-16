# RasPi WiFi Mapping / Amateur Radiocartography Tool
Developed on Raspberry Pi Zero W, intended for all Raspberry Pi and \*nix machines <br>
0.02 Yeast Rising <br>
 <br>
airodump-ng and GPSd have been found to play nicely with each other, but how can usage be made easier? <br>
Perhaps if we wrapped some Python around everything to launch/terminate airodump instances, kind of <br>
like Sparrow-Wifi or Falcon, we can have a smarter system by geofencing with geopy <br>
 <br>
⚠ Reconnect to home wifi upon return is still being tested ⚠ <br>
✔ Managing of airodump-ng process based on location <br>
✔ Start/stop monitor mode automatically; can currently be changed by editing monstart.sh <br>
❌ Tweak not included to put raspi0w in-built wifi into monitor mode <br>
 <br>
Requirements: <br>
-Python 3 <br>
-GPSd <br>
-aircrack-ng suite <br>
-geopy <br>
-gpsd-py3 <br>
-if no suitable external adapter and running raspbian, you may need something else to allow your in-built wireless adapter to be put into monitor mode <br>
 <br>
Instructions: <br>
After all requirements are met, once GPSd is running and your GPS is plugged in, run rce.py <br>
On this first run it'll generate a settings file (settings.deez) with its "Home Coordinates" <br>
When reaching more than 20 feet or so from this point, monitor mode will automatically be enabled and airodump will be start <br>
Upon returning to within 20 feet or so from this point, monitor mode will automatically be disabled and airodump will be terminated <br>
Currently, after the initial settings file has been generated, it is recommended to add your WiFi SSID as a new line to the bottom of the file <br>
 <br>
If you've never run airodump-ng before, don't worry, it will drop logs in the same folder as this script <br>
If you have, make sure you know where it's dumping <br>
 <br>
Credits: <br>
-evilsocket <br>
-ghostop14 <br>
-yanewby > https://forums.raspberrypi.com/viewtopic.php?t=23440 <br>

