#!/usr/bin/env python
import sys
from onedriveapi import OneDriveAPI
import os
import time
import math
import Queue
import threading
from requests_futures.sessions import FuturesSession


script = sys.argv
#id = '9E2B723769ACD40C!5200'
#path = '/2.Broke.Girls.S01E23E24.mkv'

class testDownload():

    def __init__(self):
        self.path = "/Pictures.rar"
        self.onedriveapi = OneDriveAPI()

        self.meta = self.onedriveapi.getMeta(self.path)
        self.buffer = 10
        self.q = Queue.Queue(self.buffer)
        self.file = open("/home/abbasali/Documents/onedrivefuse/Pictures.rar", 'w+')
        self.size = self.meta['size']
               
        self.chunksize = 1048576 * 5
        self.numChunks = math.ceil(self.size/float(self.chunksize))

        self.session = FuturesSession(max_workers=10)

    def WriteToFile(self, sess, resp ,data):
        ftime = time.time()-data['time']
        #print("Time to get from server : " + str(ftime))
        #print (str(((self.chunksize)/(1024*1024))*8/(ftime))  + ' Mbps')
        self.file.seek(0,2)
        self.file.write(resp.content)
        self.file.seek(0,2)
        print str(len(resp.content))

    def test(self):
        try:
            if not self.meta:
                print 'couldnt find path'
            else:
                start = 0
                end = 0
                counter = 0

                while counter < self.numChunks:
                    if start + self.chunksize > self.size:
                        end += self.size - start
                    else:
                        end += int(self.chunksize)
                    self.onedriveapi.download1(self.path, start, end-1, background_callback=lambda sess, resp: self.WriteToFile(sess, resp, {'time': time.time()}))
                    #self.session.get(data['url'], headers=data['headers'], allow_redirects=True, background_callback=lambda sess, resp: self.WriteToFile(sess, resp, {'time': time.time()}))
                    start = end
                    counter += 1

                counter = 0
                while counter < 15:
                    time.sleep(1)
                    print("counter = " + str(counter))
                    counter += 1
        except Exception as e :
            #pass
            print str(e)
test = testDownload()
test.test()

# from requests_futures.sessions import FuturesSession
# session = FuturesSession(max_workers=30)

# path = "/Pictures.rar"
# onedriveapi = OneDriveAPI()

# meta = onedriveapi.getMeta(path)
# file = open("/home/abbasali/Documents/onedrivefuse/Pictures.rar", 'w+')
# size = meta['size']
 

# def bg_cb(sess, resp, test):
#     # parse the json storing the result on the response object
#     print test
#     print len(resp.content)


# chunksize = 1048576 * 5
# numChunks = math.ceil(size/float(chunksize))

# if not meta:
#     print 'couldnt find path'
# else:
#     start = 0
#     end = 0
#     counter = 0

#     while counter < numChunks:
#         if start + chunksize > size:
#             end += size - start
#         else:
#             end += int(chunksize)
#         data = onedriveapi.download1(path, start, end-1)
#         session.get(data['url'], headers=data['headers'], allow_redirects=True, background_callback=lambda sess, resp: bg_cb(sess, resp, {''}))
#         start = end
#         counter += 1