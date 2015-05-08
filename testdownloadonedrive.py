#!/usr/bin/env python
import sys
from onedriveapi import OneDriveAPI
from cachemanager import Chunk, File
import os
import time

script = sys.argv
#id = '9E2B723769ACD40C!5200'
id = '9E2B723769ACD40C!5175'
print id
onedriveapi = OneDriveAPI()

meta = onedriveapi.getMeta(id)

print meta 

if not meta:
    print 'couldnt find path'
else:

    size = meta['size']
    print 'size = ' + str(size)
    
    #print "Entering download"
    #onedriveapi.download(id, 0, 10)
    #print "Ending Downlado"
    
    chunksize = 1048576 * 60

    start = 0
    end = 0
    count = 1
    stime = time.time()
    start1 = 0 

    while (size/chunksize) >= 1:
        end += int(chunksize)
        #print "Entering download"
        onedriveapi.download(id, start, end-1)
        #print "Ending Downlado"
        start = end
        if (count%5) == 0:
            print (str(((end-start1)/(1024*1024))*8/(time.time()-stime))  + ' Mbps')
            start1 = end
            stime = time.time()
        count += 1
        size = size - chunksize


print "ENDING"