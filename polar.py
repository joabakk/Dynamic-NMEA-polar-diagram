import pynmea2  #for parsing NMEA
import re       #for regex
import serial   #serial communication
import time     
import MySQLdb  
import RPi.GPIO as GPIO
import polar    #private library with special functions
import operator
import math
import json
import random   #for testing
import subprocess   #for sending commands to shell
from decimal import *

#variables

windspeedplus = 0.1
windspeedminus = 0.1
winddirplus = 0.5
winddirminus = 0.5

vmgtime = winddirtime = windspeedtime = boatspeedtime = rottime = curdir = curcardir = curspeed = curtime = tba = tra = 0

txtime = 0
test = 0  #used to test stuff later
addtest = 0 #used to switch test for adding to db on/off

s_tack = 3      #starboard tack is either 0 (port) or 1 (starboard). 3 is "not set"
performance = 0 #per cent performance

GPIO.setmode(GPIO.BCM)
GPIO.setup(21, GPIO.IN, pull_up_down = GPIO.PUD_DOWN) #used to identify if hat is on or not...

#functions

def degrees_to_cardinal(d): #convert degrees direction to cardinal direction
    '''
    note: this is highly approximate...
    '''
    dirs = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
            "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    ix = int((d + 11.25)/22.5)
    return dirs[ix % 16]

def checksum(nmeadata): #to make checksum for made nmea sentences
    calc_cksum = reduce(operator.xor, (ord(s) for s in nmeadata), 0)
    return calc_cksum

def read_serial(filename):  #main function
    global vmgtime, mintime, windspeedtime, boatspeedtime, rottime, performance, rpm, vmg, tbs, tra, winddir, boatspeed, curdir, curcardir, curspeed, curtime, lat, lon
    com = None
    while 1:

        if com is None:
          try:
            #com = serial.Serial(filename, timeout=5.0) #if pty
	        com = open(filename) #if logfile
          except serial.SerialException:
            print('could not connect to %s, restarting' % filename)
            command = ['service', 'kplex', 'restart'];
            subprocess.call(command, shell=False)
            time.sleep(5.0)
            continue

        data = com.readline()
        line=data
        tags = line.split('\\') 
        
        """looks like \s:log*71\ or \c:1387191186*0E\ 
        or \s:kplex,c:1387191537*0F\ combined?? print tags"""
    
        line = tags[-1]#last item in list is nmea sentence
        NMEAtag = tags[1] #first item is NMEA tags (combined)
        NMEAtagParts = NMEAtag.split(',')
        #NMEAsource = NMEAtagParts[0][2:]
        NMEAtime = NMEAtagParts[1][2:-3] #NMEA time from tag
        try:
            reader = pynmea2.NMEAStreamReader()
            for msg in reader.next(line):
                try:
                    #print msg.sentence_type
                    #print(msg)
                    msg = pynmea2.parse(line)
                    #print repr(msg)
                    if msg.sentence_type == 'ROT':
                        rateofturn = msg.rate_of_turn
                        if rateofturn != '':
                            rottime = NMEAtime
                            #print "ROT: ", rateofturn
                    elif msg.sentence_type == 'RPM':
                        rpm = msg.speed
                        #print "RPM: ", rpm
                    elif msg.sentence_type == 'VDR':
                        curdir = msg.deg_t
                        curspeed = msg.current
                        curcardir = degrees_to_cardinal(curdir)#cardinal directions (N, SW, NNE)
                        curtime = NMEAtime
                        print "current ",curspeed," Knots from ",curcardir
                    elif msg.sentence_type == 'HDM':
                        mag_heading = msg.heading
                        #print "heading M: ", mag_heading
                    elif msg.sentence_type == 'HDT':
                        true_heading = msg.heading
                        #print "heading T: ", true_heading
                    elif msg.sentence_type == 'VPW':
						vmg = msg.speed_kn
						vmgtime = NMEAtime
						if vmg is None:
							vmg = 0
						#print "vmg ", vmg
                    elif msg.sentence_type == 'MWV':
                        if msg.reference == 'R':
                                winddir = msg.wind_angle
                                if winddir != '':
                                    winddirtime = NMEAtime
                                    #print "Wind angle rel: ", winddir
                                    if msg.wind_speed_units == 'M':
                                        windspeed = msg.wind_speed
                                        if windspeed != '':
                                            windspeedtime = NMEAtime
                    elif msg.sentence_type == 'VHW':
                        boatspeed =  float(msg.water_speed_knots)
                        #print "all ok here"
                        if boatspeed != '':
                            boatspeedtime = NMEAtime
                            #print "boat speed ", boatspeed
                        else:
                            boatspeed = 0
                            boatspeedtime = NMEAtime
                    elif msg.sentence_type == 'VWR':
                        winddir = msg.deg_r
                        if winddir != '':
                            winddirtime = NMEAtime
                            windtack = msg.l_r
                            windspeed = msg.wind_speed_ms
                            if windspeed != '':
                                windspeedtime = NMEAtime
                    elif msg.sentence_type == 'GGA':
                        lat = float(msg.lat)
                        lon = float(msg.lon)
                        #print "gps ok", lat, " ", lon
                    else:
                        pass
                    
                    if test == 1:
                        mintime = 1
                        timediff = 1
                        vmgtime = winddirtime = windspeedtime = boatspeedtime = rottime = NMEAtime = 10
                
                    #print "times", int(vmgtime), int(winddirtime), int(windspeedtime), int(boatspeedtime), int(rottime)
                    mintime = min(int(vmgtime), int(winddirtime), int(windspeedtime), int(boatspeedtime))#, int(rottime))
                    maxtime = max(int(vmgtime), int(winddirtime), int(windspeedtime), int(boatspeedtime))#, int(rottime))
                    timediff = (maxtime - mintime)
                    #print "timediff", timediff
                    if test == 1:
                        mintime = 1
                        timediff = 1
                        vmgtime = winddirtime = windspeedtime = boatspeedtime = rottime = NMEAtime
                        windspeed = 9.8
                        winddir = random.randint(44,170)
                        boatspeed = float('%d.%d' % (random.randint(0,1),random.randint(0,99)))
                        rateofturn = 0
                        windrad=math.radians(winddir)
                        #bspex=int(boatspeed)
                        vmg = "{:.2f}".format(boatspeed*math.cos(windrad))
                        tack = random.randint(0,1)
                        lat = 59.0234
                        lon = 10.0283
                        
                        if tack == 1:
                            windtack = "l"
                        else:
                            windtack = "r"
                        
                    if mintime != 0 and timediff < 2:
                        #less than two seconds between all sentences updates)
                        pbs = polar.polarcheck( windspeed, winddir, boatspeed);
                        #print "polar boat speed: ",pbs
                        #vmgtime = winddirtime = windspeedtime = boatspeedtime = rottime = 0 
                        with open('/var/www/current','w') as f:
                            try:
                                if pbs != 0:
                                    performance = int(100*float(boatspeed)/float(pbs))
                                    #print "performance calc"
                                else:
                                    performance = 0
                                    #print "performance 0"
                                #curtime = int(time.time())#test
                                current = dict(windspeed=windspeed, winddir=winddir ,boatspeed=boatspeed, pbs=float(pbs), tbs=tbs, tra=tra,  performance=performance, curcardir=curcardir, curspeed=curspeed, curtime=int(curtime), latitude=lat, longitude=lon)
                                print "current written to dict", current
                            except:  
                                current = dict(windspeed=windspeed, winddir=winddir ,boatspeed=boatspeed, pbs=pbs, tbs=tbs, tra=tra, curcardir=curcardir, curspeed=curspeed, curtime=int(curtime), latitude=lat, longitude=lon)
                                print "current no performance written to dict", current
                            jsoncurrent=json.dumps(current)
                            print jsoncurrent
                            f.write(jsoncurrent + '\n')
                            print "written to file"
                        if boatspeed > pbs and boatspeed != '0.00' and (GPIO.input(21)) == 0:# and addtest != 1:#CHECK IF ENGINE OFF
                            #print "no items better, adding"
                            if windtack == "l":
                                s_tack = 0
                            else:
                                s_tack = 1
                            #print NMEAtime, ', ', windspeed, ', ', winddir, ', ', boatspeed, ', ', rateofturn, ', ', vmg, 'startboard tack? ', s_tack
                            result = polar.polaradd( NMEAtime, windspeed, winddir, boatspeed, rateofturn, vmg, s_tack )
                            #print "result from sql injection: ", result
                        elif pbs != "error":
                            #print "not better than already logged"
                            pass
                        else:#error in sql query
                            pass
                    elif mintime != 0 and (max(int(winddirtime), int(windspeedtime), int(boatspeedtime), int(rottime)) - min(int(winddirtime), int(windspeedtime), int(boatspeedtime), int(rottime)) < 2):
                        try:
                            windrad=math.radians(winddir)
                            vmg = boatspeed * math.cos(windrad)
                        except:
                            pass
                        pbs = polar.polarcheck( windspeed, winddir, boatspeed);
                        #print "polar boat speed: ",pbs
                        #vmgtime = winddirtime = windspeedtime = boatspeedtime = rottime = 0 
                        
                        if boatspeed > pbs and boatspeed != '0.00' and(GPIO.input(21)) == 0:# and addtest != 1:#CHECK IF ENGINE OFF
                            #print "no items better, adding"
                            #print NMEAtime, windspeed, winddir, boatspeed, rateofturn, vmg, windtack
                            result = polar.polaradd( NMEAtime, windspeed, winddir, boatspeed, rateofturn, vmg, windtack )
                            #print "result from sql injection: ", result
                        elif pbs != "error":
                            #print "not better than alredy logged"
                            pass
                        else:
                            #error in sql query
                            pass
                    else:
                        #print "keep calm, carry on"
                        pass
                        
                    if test == 1:
                        txtime = int(NMEAtime) - 1
                        
                    if txtime < NMEAtime:
                            txtime = NMEAtime
                            tbs, tra = polar.findtbs( windspeed, winddir, boatspeed );
                            #print "target boat speed: ", tbs
                            #print "polar boat speed: ", pbs
                            #print "target relative angle: ", tra
                            #print "target speed:",tbs
                            #print "target angle: ", tra
                        
                            tbsmsg = "PSILTBS,{0:1.1f},N" .format(tbs)
                            ck = polar.checksum(tbsmsg)
                            NMEAfullsentence = "$"+str(tbsmsg)+"*"+str(ck)
                            NMEAfullsentence = NMEAfullsentence+'\r\n'
                            com.write(NMEAfullsentence)
                            
                            cfdmsg = "PSILCD1,{0:1.1f},{1:1.1f}" .format(pbs, tra)
                            ck = polar.checksum(cfdmsg)
                            NMEAfullsentence = "$"+str(cfdmsg)+"*"+str(ck)
                            NMEAfullsentence = NMEAfullsentence + '\r\n'
                            com.write(NMEAfullsentence)
                            
                except:
                    #print "exception 2"
                    continue
		    pass#raise 
		    #continue         
        except:
            #print "exception 1"
            continue
	    pass#raise
	    #continue

#filename="/dev/pty23"
filename="/home/pi/kplexlogs/nmeaf.log"
while 1:
    try:
        read_serial(filename)
    except:
        time.sleep(0.2)
