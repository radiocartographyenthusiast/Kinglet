Not sure if I want to go elastic or sql, as this is going to be a mess of nested tables <br>
I'm considering a table for coords, and each coord pair gets a table of the wifi data logged at that point <br>
# RasPi WiFi Mapping / Amateur Radiocartography Tool
![Image](https://github.com/radiocartographyenthusiast/Kinglet/blob/main/kinglet-ssh.png?raw=true) <br>
Developed on Raspberry Pi Zero W, intended for all Raspberry Pi and \*nix machines <br>
0.15 <b>Pre-DB</b> <br>
 <br>
Your choice between Airodump and Sparrow-Wifi for main monitor source <br>
Support for a secondary wireless interface, used by Falcon/Airodump in conjunction with Sparrow-WiFi <br>
<br>
My goal is to generate heatmaps of reception for home and local networks. What I have in mind is thorough but could result in lots of junk data, though, or at least a bulk to digest by something beefier than a Pi0. <br>
 <br>
⚠ Reconnect to home wifi upon return is still being tested ⚠ <br>
⚠ Map to be implemented later ⚠ <br>
⚠ Database features to be implemented later ⚠ <br>
✔ Managing of airodump-ng or Sparrow-WiFi: Kinglet process based on location <br>
✔ Start/stop monitor mode automatically <br>
✔ Stat logger to track RAM usage, CPU usage, temperature, and disk usage <br>
✔ Flask web server, with Waitress <br>
✔ Pwnagotchi's "zramfs" to prolong the life of the storage device <br>
✔ Supports up to 2 monitor mode wireless devices at once <br>
 <br>
<h3>Main Requirements:</h3> <br>
-Sys: Python 3 <br>
-Sys: GPSd <br>
-Sys: aircrack-ng suite <br>
-Python: geopy <br>
-Python: gpsd-py3 //I know, I'm silly using 2 GPSd libs at once<br>
-Python: python-dateutil <br>
-Python: gps3 //I know, I'm silly using 2 GPSd libs at once<br>
-Python: toml <br>
-Github: Sparrow-WiFi and Falcon <br>
 <br>
<h3>Manual Instructions:</h3> <br>
After all requirements are met, once GPSd is running and your GPS is plugged in, run Kinglet.py (Or just run it and go outside to touch grass) <br>
On this first run it'll generate a settings file (settings.deez) with its "Home Coordinates" once the software recognizes that the GPS is locked <br>
When reaching more than 20 feet or so from this point, monitor mode will automatically be enabled and airodump will be start <br>
Upon returning to within 20 feet or so from this point, monitor mode will automatically be disabled and airodump will be terminated <br>
To use airodump-ng instead of Sparrow-WiFi, launch with the argument `--airodump true` <br>
More options available by using the `--help` argument <br>
 <br>
<h3>Solo ISO Now Available! [Instructions]</h3> <br>
Use Balena Etcher to flash the image to your micro sd card <br>
Make sure to add your own wpa_supplicant.conf to the root of the boot partition to connect to your own wifi automatically: <br>
After first boot, you may need to use `sudo raspi-config` to expand the file systen <br?
<b>Default password included</b> since they wanted to change things<br>
Default username:password is <b>rad</b>:<b>io</b> <br>
Default root password is <b>toor</b> <br>
If you have Apple's Bonjour Services, you can find it on the network at kinglet.local for access <br>
If your pi is in the same family as the Pi Zero (First Gen), then this image will work for you <br>
RNDIS Gadget IP default set to 192.168.137.2 from 10.0.0.2, to be more friendly to Windows and its Internet Connection Sharing habits <br>
The image is built on top of a kali slim image I generated using their kali-arm build scripts <br>

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
<h3>Credits and Special Mentions:</h3> <br>
-evilsocket > Pwnagotchi <br>
-ghostop14 > Sparrow-WiFi <br>
-yanewby > https://forums.raspberrypi.com/viewtopic.php?t=23440 <br>
-re4son
<h6>Required Disclosure as per GNU GPL v3:</h6>
$REPO/sparrow-wifi/kinglet.py is directly derived from sparrowwifiagent.py <br>
$REPO/fs/__init__.py came from Pwnagotchi <br>
