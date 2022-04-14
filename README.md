# RasPi WiFi Mapping / Amateur Radiocartography Tool
Developed on Raspberry Pi Zero W, intended for all Raspberry Pi <br>
0.000b Devising <br>
 <br>
airmon-ng and GPSd have been found to play nicely with each other, but how can usage be made easier? <br>
Perhaps if we wrapped some Python around everything to launch/terminate airmon instances, kind of <br>
like Sparrow-Wifi or Falcon, we can have a smarter system by either: <br>
-geofencing with the GPS [Ideal] <br>
-or-<br>
-Listening for home network all the time with a second wifi adapter [Boo] <br>
 <br>
Requirements: <br>
-Python <br>
-GPSd <br>
-aircrack-ng suite <br>
