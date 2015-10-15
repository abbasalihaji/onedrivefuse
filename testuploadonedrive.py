#!/usr/bin/env python
import sys
from onedriveapi import OneDriveAPI
import os
import time
import math
import Queue
import threading
from requests_futures.sessions import FuturesSession


script = sys.argv[0]
uploadpath = sys.argv[2]
localpath = sys.argv[1]

print localpath
print uploadpath
#id = '9E2B723769ACD40C!5200'
#path = '/2.Broke.Girls.S01E23E24.mkv'

class testUpload():

    def __init__(self, localPath, cloudPath):
        self.path = cloudPath
        self.onedriveapi = OneDriveAPI()
        self.file = open(localpath, 'r')
        self.file.seek(0,2)
        self.fileSize = self.file.tell()

        self.chunksize = 1048576 * 10
        self.numChunks = math.ceil(self.fileSize/float(self.chunksize))
        print self.numChunks
        self.session = FuturesSession(max_workers=10)

    def uploadFinished(self, sess, resp):
        print 'uPloadFinished'
        print resp.content

    def test(self):
        try: 
            session = self.onedriveapi.createUploadSession(self.path)
            
            url = session['uploadUrl']
            start = 0
            end = 0
            counter = 0
            while counter < self.numChunks:
                if start + self.chunksize > self.fileSize:
                        end += self.fileSize - start
                else:
                    end += int(self.chunksize)
                size = end - start
                self.file.seek(start)
                data = self.file.read(size)
                #response = self.onedriveapi.upload(url, start, end - 1, size, self.fileSize, data)
                #print response
                start = end
                counter += 1             

        except Exception as e :
            #pass
            print str(e)
test = testUpload(localpath, uploadpath)
test.test()
