# Dynamic-NMEA-polar-diagram
Python script to create mysql polar diagram from NMEA data on the fly

This requires 
 - a mysql database called polar with a table called polar with a user called 'kplex' and password 'kplex' with read and write access to that db.
 - kplex (https://github.com/stripydog/kplex) running with all NMEA streams sent to pty 'dev/pty023' and with timestamp tag enabled
 - a way to detect whether the engine is running or not (I use a digital pin on the rPi (pin 21) connected to the engine acc from the ignition (remember the voltage divider)
 - Highcharts installed (http://www.highcharts.com/)
 - Apache installed, and the contents of 'web' in your var/www or similar
 - Link python libraries to 'libraries' folder

This is very much work in progress. Although it is working for me, I am grateful for any help in firming up and making the code more effective.

<img src=https://cloud.githubusercontent.com/assets/2553029/10094739/d53bda3e-6363-11e5-84fd-321acd3a8cd1.jpeg>
