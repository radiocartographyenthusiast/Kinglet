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
 <br>
Credits: <br>
-evilsocket <br>
-ghostop14 <br>
