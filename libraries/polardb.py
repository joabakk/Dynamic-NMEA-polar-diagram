import pynmea2 
import re
import serial
import time
import MySQLdb
import RPi.GPIO as GPIO

#variables

windspeedplus = 0.1
windspeedminus = 0.1
winddirplus = 0.1
winddirminus = 0.1

def polaradd( nmeatime, windspeed, winddir, boatspeed, rateofturn, vmg, stack ):

    # Open database connection
    db = MySQLdb.connect(host="localhost",user="kplex",passwd="kplex",db="polar" )
    cursor = db.cursor()

    add_tmp = ("INSERT INTO polar "
            "(nmea_time, wind_speed, wind_dir, boat_speed, rate_of_turn, boat_speed_parallell, Starboard ) "
            "VALUES ('%s','%s','%s','%s','%s','%s','%s' )" % (nmeatime, windspeed, winddir, boatspeed, rateofturn, vmg, stack))

    try:
        # Execute the SQL command
        cursor.execute(add_tmp)
        # Commit your changes in the database
        db.commit()
        success = "data added"
    except:
        # Rollback in case there is any error
        db.rollback()
        success = "no data added"

    # disconnect from server
    db.close()
    return success

def polarcheck( wind_speed, wind_dir, boat_speed ):

    # Open database connection
    db = MySQLdb.connect(host="localhost",user="kplex",passwd="kplex",db="polar" )
    cursor = db.cursor()
    sql = ("""SELECT MAX(boat_speed) AS polarbs FROM `polar` WHERE `wind_speed` > %s AND `wind_speed` < %s AND `wind_dir` > %s AND `wind_dir` < %s""" % ((wind_speed - windspeedminus), (wind_speed + windspeedplus), (wind_dir - winddirminus), (wind_dir + winddirplus)))
    #print sql
   
    try:
       # Execute the SQL command
        cursor.execute(sql)
        # Find number of rows in a list of lists.
        row = cursor.fetchone()
        polarbs = row[0]
        if polarbs >= boat_speed:
            pbs = polarbs
        else:
            pbs = 0
        
        #success = cursor.rowcount
        #TODO: return polar boat speed instead of count
    except:
        # In case there is any error
        pbs = "error"

    # disconnect from server
    db.close()
    return pbs

def findtbs( wind_speed, wind_dir, boat_speed ):
     # Open database connection
    db = MySQLdb.connect(host="localhost",user="kplex",passwd="kplex",db="polar")
    cursor = db.cursor()
    if wind_dir > 90:
        sql = ("""SELECT `boat_speed`, `wind_dir` FROM `polar` WHERE boat_speed_parallell = (SELECT MIN(`boat_speed_parallell`) as tbs) AND `wind_speed` > %f AND `wind_speed` < %f AND `boat_speed` >= %f ORDER BY `boat_speed_parallell` DESC""" % ((wind_speed - windspeedminus), float(wind_speed + windspeedplus), float(boat_speed)))
    elif wind_dir < 90:
        sql = ("""SELECT `boat_speed`, `wind_dir` FROM `polar` WHERE boat_speed_parallell = (SELECT MAX(`boat_speed_parallell`) as tbs) AND `wind_speed` > %f AND `wind_speed` < %f AND `boat_speed` >= %f ORDER BY `boat_speed_parallell` DESC""" % ((wind_speed - windspeedminus), float(wind_speed + windspeedplus), float(boat_speed)))
    else:
        pass
    #print sql

    try:
       # Execute the SQL command
        cursor.execute(sql)
        # Find number of rows in a list of lists.
        #success = targetbs
        #success = cursor.rowcount
        row = cursor.fetchone()
        success = row
        #print "check ok"
    except:
        # In case there is any error
        success = "error"

    # disconnect from server
    db.close()
    return success

def checksum(sentence):
    # Initializing our first XOR value
    calc_cksum = 0
    
    # For each char in chksumdata, XOR against the previous 
    # XOR'd char.  The final XOR of the last char will be our 
    # checksum to verify against the checksum we sliced off 
    # the NMEA sentence
    
    for c in sentence:
        # XOR'ing value of csum against the next char in line
        # and storing the new XOR value in csum
        calc_cksum ^= ord(c)
    calc_cksum = hex(calc_cksum)[2:]
    calc_cksum = calc_cksum.zfill(2)
    
    return calc_cksum
    
