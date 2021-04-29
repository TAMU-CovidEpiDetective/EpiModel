import pandas as pd
import mysql.connector as msql
from mysql.connector import Error

#host='coviddata.cphvsbfyrgxg.us-east-2.rds.amazonaws.com'
#port=int(3306)
#user='kriramz'
#password='Star3003!!!!'
#database='coviddata' / 'simDB', current one
#table = 'sim'
#to run: 'python update_db.py'

simData = pd.read_csv('us_simulation.csv')
print(simData.head())

import mysql.connector as msql
from mysql.connector import Error
try:
    conn = msql.connect(host='coviddata.cphvsbfyrgxg.us-east-2.rds.amazonaws.com', user='kriramz',  
                        password='Star3003!!!!')
    if conn.is_connected():
        cursor = conn.cursor()
        cursor.execute("CREATE DATABASE simDB")
        print("simDB database is created")
except Error as e:
    print("Error while connecting to MySQL", e)


try:
    conn = msql.connect(host='coviddata.cphvsbfyrgxg.us-east-2.rds.amazonaws.com', user='kriramz',  
                        password='Star3003!!!!')
    if conn.is_connected():
        cursor = conn.cursor()
        cursor.execute("use simDB;")
        print("You're connected to database!")
        cursor.execute('DROP TABLE IF EXISTS sim;') #delete older table
        print('Creating table....') #Creates table Below:
        cursor.execute("CREATE TABLE sim (Dates CHAR(11)NOT NULL, \
                        Infections FLOAT(14,5) NOT NULL, \
                        Hospitalizations FLOAT(12,5) NOT NULL, \
                        Deaths FLOAT(12,5) NOT NULL, \
                        Meant_rt FLOAT(11,10))")
        print("sim table is created....")
        for i,row in simData.iterrows():
            sql = "INSERT INTO simDB.sim VALUES (%s,%s,%s,%s,%s)"
            cursor.execute(sql, tuple(row))
            print("Record inserted")
            # the connection is not autocommitted by default, so we 
            # must commit to save our changes
            conn.commit()
except Error as e:
    print("Error while connecting to MySQL", e)
    
    
sql = "SELECT * FROM sim"
cursor.execute(sql)

# Fetch all the records
result = cursor.fetchall()
for i in result:
    print(i)
        
    
print("------------------------------------------------------------")
print("------------------------------------------------------------")
print("                 COMPLETED DB UPDATE")
print("------------------------------------------------------------")
print("------------------------------------------------------------")

