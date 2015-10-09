#!/usr/bin/env python
import sys
from onedriveapi import OneDriveAPI
from onedrivefuse import OneDriveFUSE
import os
import time


t = time.time()
script = sys.argv
#id = '9E2B723769ACD40C!5200'
#path = '/Shows/2.Broke.Girls.Season.1/2.Broke.Girls.S01E23.mkv'
#print path
onedriveapi = OneDriveAPI()
onedrivefuse = OneDriveFUSE()

def read(path, offset, size, data):
    d = onedrivefuse.read(path, size, offset, None)
    if len(d) != size:
        print 'Error. Testing,  Incorrect data received'
    for i in range(offset, offset+size):
        data[i] = d[i-offset]

path = "/Report.docx"
f = open('/home/Report1.docx', 'r+')
onedrivefuse.open(path, None)
size = 2062574
chunksize = 262144
data = []
for i in range(size):
    data.append('')

count = 0
read(path, 0, 131072, data)
count += 131072
read(path, 131072, 131072, data)
count += 131072
read(path, 1179649, 100001, data)
count += 100001
read(path, 262144, 262144, data)
count += 262144
read(path, 1048576, 131073, data)
count += 131073
read(path, 1279650, 655359, data)
count += 655359
read(path, 1935009, 127565, data)
count += 127565
read(path, 524288, 524288, data)
count += 524288



if count != size:
    print 'Error, Testing Not reading enough data'

f.write(bytearray(data))
print "Total time = " + str(time.time() - t) + " s."
print 'End Of Tests'
