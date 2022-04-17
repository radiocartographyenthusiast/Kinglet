# RasPi WiFi Mapping / Amateur Radiocartography Tool
Developed on Raspberry Pi Zero W, intended for all Raspberry Pi and \*nix machines <br>
0.03 <b>Yeast <i>Rising</i></b> <br>
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
<h3>Requirements:</h3> <br>
-Python 3 <br>
-GPSd <br>
-aircrack-ng suite <br>
-geopy <br>
-gpsd-py3 <br>
-if no suitable external adapter and running raspbian, you may need something else to allow your in-built wireless adapter to be put into monitor mode <br>
 <br>
 ![image](https://user-images.githubusercontent.com/103610974/163699554-3409b2bd-729f-469d-932b-c55bb0752cc9.png)
 
<h3>Instructions:</h3> <br>
After all requirements are met, once GPSd is running and your GPS is plugged in, run rce.py <br>
On this first run it'll generate a settings file (settings.deez) with its "Home Coordinates" <br>
When reaching more than 20 feet or so from this point, monitor mode will automatically be enabled and airodump will be start <br>
Upon returning to within 20 feet or so from this point, monitor mode will automatically be disabled and airodump will be terminated <br>
Currently, after the initial settings file has been generated, it is recommended to add your WiFi SSID as a new line to the bottom of the file <br>
 <br>
If you've never run airodump-ng before, don't worry, it will drop logs in the same folder as this script <br>
If you have, make sure you know where it's dumping <br>
 <br>
<h3>Solo ISO Now Available!</h3> <br>
Use Balena Etcher to flash the image to your micro sd card <br>
<b>Default password included</b> since they wanted to change things<br>
Default username:password is <b>rad</b>:<b>io</b> <br>
If you have Apple's Bonjour Services, you can find it on the network at airotool.local for ssh and sftp access <br>
rce.py would run automatically on startup, but init.d, systemd, and rc.local didn't really want to work for me. Probably because python script, but I think I might know a way around it <br>
If your pi is in the same family as the Pi Zero (First Gen), then this image should work for you <br>
Modified MOTD now included <br>
RNDIS Gadget IP default to 192.168.137.2 from 10.0.0.2 to be more friendly to Windows and its Internet Connection Sharing habits <br>
Make sure to add your own wpa_supplicant.conf to the root of the boot partition: <br>

``` python
country=US
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1

network={
    ssid="NETWORK-NAME"
    psk="NETWORK-PASSWORD"
}
```
<br>
<h3>Credits:</h3> <br>
-evilsocket <br>
-ghostop14 <br>
-yanewby > https://forums.raspberrypi.com/viewtopic.php?t=23440 <br>
