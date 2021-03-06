#!/usr/bin/env python

from __future__ import with_statement
from __future__ import division
import concurrent.futures
from errno import EACCES, ENOENT, EIO, EPERM
from threading import Lock,Thread
from stat import S_IFDIR, S_IFREG
from sys import argv, exit, stderr
import Queue
import logging
import os
import argparse
import tempfile
import time
import json
import hashlib
import urllib3
import re
import math
from fuse import FUSE, FuseOSError, Operations, LoggingMixIn, fuse_get_context
from onedriveapi import OneDriveAPI
from onedrivefilemanager import FileManager, File, Chunk
from Queue import Queue

class OneDriveFUSE(LoggingMixIn, Operations):
    def __init__(self, logfile=None):
        self.onedrive_api = OneDriveAPI()
        logging.basicConfig(filename=self.onedrive_api.logFile, filemode='w', level=logging.WARNING)
        logging.warning("Testing")
        self.logfile = logfile
        self.fileManager = FileManager()
        self.getFileEntry('/',True)
        self.writeLock = Lock()
                 
    def getFileEntry(self, path, isRoot = False):
        print path
        meta = self.onedrive_api.getMeta(path, isRoot)
        if not meta:    #couldnt find entry
            return -1   
        else:
            children = []
            print meta['children']
            for child in meta['children']:
                children.append(child['name'].encode('ascii', 'ignore'))
            if 'folder' in meta:
                type = 'folder'
            elif 'file' in meta:
                type = 'file'
            else:
                print 'ERROR, Unknown filetype'
                raise FuseOSError(EIO)

            if isRoot:
                path = '/'
            else:
                tempPath = re.sub(r'/drive/root:','' ,meta['parentReference']['path'])
                path = tempPath + '/' + meta['name']
            
            #file = ODFile(meta['id'], meta['name'], path, type,meta['size'], children)
            file = File(path, type, meta['size'], children)
            print meta['size']
            self.fileManager.addFile(file)
            return file
      
    def createChunks(self, file):
        filesize = file.size
        chunksize = self.onedrive_api.chunksize
        numchunks = int(math.ceil(filesize/chunksize))
        if len(file.chunks) == numchunks:
            return #Already has obtained the chunks before
        else:
            count = 0
            offset = 0
            while count < numchunks:
                if offset + chunksize-1 > filesize:  #In the Last chunk
                    csize = file.size - offset
                    file.chunks.append(Chunk(csize, offset, count))
                    offset += csize
                else:
                    file.chunks.append(Chunk(chunksize, offset, count))
                    offset += chunksize
                count += 1
        #self.printChunks(file)
        if len(file.chunks) != numchunks:
            e = 'Error, Incorrect Number of Chunks. Expected = ' + str(numchunks) + 'Got = ' + str(len(file.chunks))
            logging.warning(e)
            raise FuseOSError(EIO)

    def printChunks(self, file):
        for c in file.chunks:
            print'Num = ' + str(c.num) + '. Offset = ' + str(c.offset) + '. Size = ' + str(c.size)

    def downloadChunk(self, file, chunknum, background_callback):
        if chunknum < len(file.chunks):
            chunk = file.chunks[chunknum]
            startbyte = chunk.cloudOffSet
            endbyte = chunk.cloudOffSet+chunk.size-1
            #self.chunk['chunk'] = chunk
            self.onedrive_api.download(file.cloudPath, startbyte, endbyte, background_callback=background_callback)
 
    def writeToFile(self, sess, resp, data):
        logging.warning("IN WRITE TO FILE")
        #PUT A CHECK HERE THAT IF THE CHUNK IS ALREADY AVAILABEL DONT OVERWRITE.
        #CSE WHERE TWO CALLS MADE. AVOID
        try:
            self.writeLock.acquire()
            file = data['file']
            chunkNum = data['chunkNum']
            temp = resp.content
            logging.warning("CHUNK NUM:" + str(chunkNum))
            if len(temp) != file.chunks[chunkNum].size:
                logging.warning("Wrong size of data recieved")
            else:    
                logging.warning("Downloaded chunk size = " + str(len(temp)))
                #Put lock here
                f = open(file.tempFilePath, 'a+b')
                f.seek(0, 2)
                file.chunks[chunkNum].localOffSet = f.tell()
                logging.warning("localOffset = " + str(file.chunks[chunkNum].localOffSet))
                f.write(temp)
                f.seek(0,2)
                logging.warning("EndOffSet = " + str(f.tell()))
                file.chunks[chunkNum].isAvailable = True
            logging.warning("RELEASING LOCK")
            # if chunkNum + 10 < len(file.chunks): #download next chunk needed
            #     callBackData = {'chunkNum': chunkNum+10, 'file': file}
            #     self.downloadChunk(file, chunkNum+10, background_callback=lambda sess, resp, callBackData=callBackData: self.writeToFile(sess, resp, callBackData))                                      
            self.writeLock.release()
            logging.warning(file.chunks[chunkNum].isAvailable)
            logging.warning("EXITING WRITE TO FILE")
        except Exception as e :
            self.writeLock.release()
            logging.warning(e)
            return str(e)

    def getData(self, file, chunkNum, readOffset, readSize):
        try:
            data = ""
            temp = ""
            chunk = file.chunks[chunkNum]
            cloudOffset = int(chunk.cloudOffSet)
            chunkSize = int(chunk.size)
            offset = int(readOffset)
            size = int(readSize)
            f = open(file.tempFilePath, 'a+b')        #Understand pyhton write read params to fix this
            while cloudOffset < (offset + size):
                if chunk.isAvailable:
                    #logging.warning("CHUNK AVAILABLE")
                    #f.seek(0,2)
                    #logging("AVAILABLE OFFSET " + str(f.tell()))
                    f.seek(chunk.localOffSet)
                    temp = f.read(chunkSize)
                    logging.warning("Chunk is available. Size = " + str(len(temp)))
                else:
                    #IMP DOWNLOAD PART CHANGE
                    tempChunk = chunk
                    tempNum = tempChunk.num
                    counter = 0
                    while counter < 10:    
                        logging.warning(tempNum)              
                        callBackData = {'chunkNum': tempNum, 'file': file}
                        self.downloadChunk(file, tempChunk.num, background_callback=lambda sess, resp, callBackData=callBackData: self.writeToFile(sess, resp, callBackData))              
                        tempNum += 1
                        if tempNum < len(file.chunks):
                            tempChunk = file.chunks[tempNum]
                        else:
                            break
                        counter += 1
                    logging.warning("Downloaded chunk size = " + str(len(temp)))
                    counter = 0
                    while counter < 15:
                        time.sleep(2)
                        logging.warning(file.chunks[chunkNum].isAvailable)
                        if file.chunks[chunkNum].isAvailable:
                            f.seek(chunk.localOffSet)
                            temp = f.read(chunkSize)
                            logging.warning("Chunk is available. Size = " + str(len(temp)))
                            break
                        counter += 1
                        logging.warning("waiting :" + str(counter))
                logging.warning("cloudOffset: "  + str(cloudOffset))
                logging.warning("offset: "  + str(offset))

                if cloudOffset >= offset and (cloudOffset+chunkSize) <= (offset+size):
                    logging.warning("Case 1")
                    data += temp
                elif cloudOffset <= offset and (cloudOffset+chunkSize) > (offset+size):
                   logging.warning("Case 2")
                   data += temp[offset-cloudOffset:(offset-cloudOffset)+size]
                elif cloudOffset <= offset and (cloudOffset+chunkSize) <= (offset+size):
                    logging.warning("case 3")
                    data += temp[offset-cloudOffset:]
                else:
                    logging.warning("Case 4")
                    data += temp[:offset+size-cloudOffset]

                if chunkNum+1 < len(file.chunks):
                    chunk = file.chunks[chunkNum+1]
                    cloudOffset = int(chunk.cloudOffSet)
                    chunkSize = int(chunk.size)
                else:               
                    if len(data) != int(size):
                        logging.warning("Expected size: " + str(size) + ". Returned data size " + str(len(data)))
                        #ADD LOGIC HERE TO HANDLE LAST CHUNK WHEN EXTRA DATA IS ASKED FOR
                        return data
                    else:
                        return data
                chunkNum += 1

            if len(data) != int(size):
                logging.warning("Expected size: " + str(size) + ". Returned data size " + str(len(data)))           
                #ADD LOGIC HERE TO HANDLE LAST CHUNK WHEN EXTRA DATA IS ASKED FOR
                return data
            else:
                return data
        except Exception as e :
            logging.warning(e)
            return str(e)

    def readHelper(self, file, offset, size):
        #Hack to create temp file
        #REMOVE
        if file.tempFilePath == "":
            self.createChunks(file)
            f = tempfile.NamedTemporaryFile(delete=False)
            file.tempFilePath = f.name
        counter = 0
        while counter < len(file.chunks):
            chunk = file.chunks[counter]
            cloudOffSet = int(chunk.cloudOffSet)
            chunkSize = int(chunk.size)
            offset = int(offset)
            size = int(size)
            #logging.warning(len(file.chunks))
            #logging.warning("In Chunk " + str(counter) + " with offset : " + str(cloudOffSet) + ". LocalPath = " + file.tempFilePath)
            if (cloudOffSet <= offset) and ((cloudOffSet + chunkSize) > offset):    #found chunk between which startoffset lies
                return self.getData(file, counter, offset, size)                
            counter += 1
        return ""


    def getParts(self, path):
        return 0
    
    def getBufferParts(self):
        return 0

    def chmod(self, path, mode):
        return 0

    def chown(self, path, uid, gid):
        return 0

    def statfs(self, path):
        return dict(f_bsize=512, f_frsize=512)

    def getattr(self, path, fh=None):
        try:
            logging.debug("getattr: " + path)
            file = self.fileManager.findFileByPath(path)
        
            if file == -1:
                file = self.getFileEntry(path)
           
            if file == -1: #for now empty, some other action such as mkdir or create will be called 
                st = dict(st_mode=(S_IFREG | 0644))
                return st

            if path == '/':
                st = dict(st_mode=(S_IFDIR | 0755), st_nlink=2)
                st['st_ctime'] = st['st_atime'] = st['st_mtime'] = time.time()
            else:
                if file.type  == 'file':
                    logging.debug('file size = ' + str(int(file.size)))
                    st = dict(st_mode=(S_IFREG | 0644), st_size=int(file.size))
                else:
                    st = dict(st_mode=(S_IFDIR | 0755), st_nlink=2)
                    st['st_ctime'] = st['st_atime'] = st['st_mtime'] = time.time()
                    #later change these and add them as attributes of file class
                    #st['st_ctime'] = st['st_atime'] = objects[name]['ctime']
                    #st['st_mtime'] = objects[name]['mtime']

            st['st_uid'] = os.getuid()
            st['st_gid'] = os.getgid()
            return st
        except Exception as e :
            logging.warning("Exception in getattr : " + str(e))

    def mkdir(self, path, mode):
        print "mkdir: " + path

    def open(self, path, flags):
        file = self.fileManager.findFileByPath(path)
        if file == -1:
            file = self.getFileEntry(path)
            if file == -1:
                print "ERROR, Couldnot get file"
                raise FuseOSError(EIO)
        return 0

    def flush(self, path, fh):
         print "flush: " + path

    def fsync(self, path, datasync, fh):
         print "fsync: " + path

    def release(self, path, fh):
         print "release: " + path

    def read(self, path, size, offset, fh):
        try:
            file = self.fileManager.findFileByPath(path)
            if file == -1:
               file = self.getFileEntry(path)
               if file == -1:
                   print "ERROR, Couldnot get file"
                   raise FuseOSError(EIO)
            data = self.readHelper(file, offset, size)
            if len(data) != size:
                logging.warning("ERRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRROR")
            return data
        except Exception as e :
            logging.warning("Exception in read: " + str(e))
	
    def readdir(self, path, fh):
        try:
            listing = ['.', '..']
            file = self.fileManager.findFileByPath(path)
            if file == -1:
                raise FuseOSError(EIO)
            else:
                for child in file.children:
                    listing.append(child)
            return listing
        except Exception as e :
            logging.warning("Exception in readdir : " + str(e))

    def rename(self, old, new):
        print "renaming: " + old + " to " + new

    def create(self, path, mode):
        return 0

    def truncate(self, path, length, fh=None):
        print "truncate: " + path

    def unlink(self, path):
        print "unlink: " + path

    def rmdir(self, path):
        params = {'meta': {}}
        params['meta'][0] = {'action': 'remove', 'path': path}

    def write(self, path, data, offset, fh):
	    return 0

    # Disable unused operations:
    access = None
    getxattr = None
    listxattr = None
    opendir = None
    releasedir = None

def main():
    parser = argparse.ArgumentParser(
        description='Fuse filesystem for OneDrive')

    parser.add_argument(
        '-d', '--debug', default=False, action='store_true',
        help='turn on debug output (implies -f)')
    parser.add_argument(
        '-s', '--nothreads', default=False, action='store_true',
        help='disallow multi-threaded operation / run with only one thread')
    parser.add_argument(
        '-f', '--foreground', default=False, action='store_true',
        help='run in foreground')
    parser.add_argument(
        '-o', '--options', help='add extra fuse options (see "man fuse")')

    parser.add_argument(
        'mount_point', metavar='MNTDIR', help='directory to mount filesystem at')

    args = parser.parse_args(argv[1:])
    
    mount_point = args.__dict__.pop('mount_point')
    
    # parse options
    options_str = args.__dict__.pop('options')
    options = dict([(kv.split('=', 1)+[True])[:1] for kv in (options_str and options_str.split(',')) or []])

    fuse_args = args.__dict__.copy()
    fuse_args.update(options)

    logfile = None
    if fuse_args.get('debug', False) == True:
        # send to stderr same as where fuse lib sends debug messages
        logfile = stderr

    fuse = FUSE(OneDriveFUSE(logfile=logfile), mount_point, False, **fuse_args)

if __name__ == "__main__":
    main()
