#!/usr/bin/env python

from __future__ import with_statement
from __future__ import division
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
from odfile import ODFileManager, ODFile, Chunk

class OneDriveFUSE(LoggingMixIn, Operations):
    def __init__(self, logfile=None):
        self.onedrive_api = OneDriveAPI()
        self.logfile = logfile
        self.files = ODFileManager()
        self.getFileEntry('/',True)
        self.crtchunk = -10
        self.chunk = {'chunk' :Chunk(0,0,-1), 'data': ''}

    def getFileEntry(self, path, isRoot = False):
        print path
        meta = self.onedrive_api.getMeta(path, isRoot)
        if not meta:    #couldnt find entry
            return -1   
        else:
            children = []
            
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
            
            file = ODFile(meta['id'], meta['name'], path, type,meta['size'], children)
            print meta['size']
            self.files.files.append(file)
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
        self.printChunks(file)
        if len(file.chunks) != numchunks:
            print 'Error, Incorrect Number of Chunks. Expected = ' + str(numchunks) + 'Got = ' + str(len(file.chunks))
            raise FuseOSError(EIO)

    def printChunks(self, file):
        for c in file.chunks:
            print'Num = ' + str(c.num) + '. Offset = ' + str(c.offset) + '. Size = ' + str(c.size)

    def preRead(self, file, offset):
        crtchunknum = file.getChunkNumber(self.crtchunk, offset)

        if crtchunknum == -1:
            print "Error, Could not find chunk"
            raise FuseOSError(EIO)
        else:
            if crtchunknum != self.crtchunk:
                if crtchunknum < len(file.chunks):
                    chunk = file.chunks[crtchunknum]
                    startbyte = chunk.offset
                    endbyte = chunk.offset+chunk.size-1
                    self.chunk['chunk'] = chunk
                    self.chunk['data'] = self.onedrive_api.download(file.path, startbyte, endbyte)
                    self.crtchunk = crtchunknum
                    if len(self.chunk['data']) != chunk.size:
                        print "Error, Data size is incorrect"
                        raise FuseOSError(EIO)
                else:
                    print "Error, Accessing out of bounds chunk"
                    raise FuseOSError(EIO)
                #if crtchunknum == self.crtchunk+1:
                #    self.crtchunk += 1
                #    self.chunk = file.chunks[self.crtchunk]
                
    def readData(self, file, offset, size, chunknum):
        print "Offset = " + str(offset) + ' .Size = ' + str(size)
        chunk = self.chunk['chunk']
        if chunknum != chunk.num:
            print "Error, Reading wrong chunk"
            raise FuseOSError(EIO)

        data = ""
        counter = 1
        while counter > 0 :
            counter = 0
            if self.chunk['chunk'].num != self.crtchunk:
                print "Error, Reading wrong chunk"
                raise FuseOSError(EIO)
            if chunknum == len(file.chunks)-1:  #last chunk
                temp = file.size - offset
                if temp == 0:
                    return ""
                elif temp <= size:
                    size = temp
            print 'Chunk num = ' + str(chunk.num)   
            if int(chunk.offset) <= int(offset):
                if int(offset)+int(size) > int(chunk.offset)+int(chunk.size):
                    print 'Case 1'
                    data += self.chunk['data'][int(offset)-int(chunk.offset):]
                    if self.crtchunk+1 < len(file.chunks):
                        self.crtchunk += 1
                        chunk = file.chunks[self.crtchunk]
                        startbyte = chunk.offset
                        endbyte = chunk.offset+chunk.size-1
                        self.chunk['chunk'] = chunk
                        self.chunk['data'] = self.onedrive_api.download(file.path, startbyte, endbyte)
                        if len(self.chunk['data']) != chunk.size:
                            print "Error, Data size is incorrect"
                            raise FuseOSError(EIO)
                        counter = 1
                else:
                    print 'Case 2'
                    data += self.chunk['data'][int(offset)-int(chunk.offset):int(offset)-int(chunk.offset)+int(size)]
            else:
                if int(offset)+int(size) > int(chunk.offset)+int(chunk.size):
                    print 'Case 3'
                    data += self.chunk['data']
                    if self.crtchunk+1 < len(file.chunks):
                        self.crtchunk += 1
                        chunk = file.chunks[self.crtchunk]
                        startbyte = chunk.offset
                        endbyte = chunk.offset+chunk.size-1
                        self.chunk['chunk'] = chunk
                        self.chunk['data'] = self.onedrive_api.download(file.path, startbyte, endbyte)
                        if len(self.chunk['data']) != chunk.size:
                            print "Error, Data size is incorrect"
                            raise FuseOSError(EIO)
                        counter = 1
                else:
                    print 'Case 4'
                    data += self.chunk['data'][:int(offset)+int(size)-int(chunk.offset)]

#            chunknum +=1 
#            print str(chunknum)
#            if chunknum < len(file.chunks):
#                chunk = file.chunks[chunknum]
#            else:
#                if len(data) != int(size):
#                    print "Error, Last Chunk Incorrect data size read, Expected = " + str(size) + '. Got = ' + str(len(data))
#                   raise FuseOSError(EIO)
#                else:
#                    return data
        if len(data) != int(size):
             print "Error, Incorrect data size read, Expected = " + str(size) + '. Got = ' + str(len(data))
             raise FuseOSError(EIO)
        else:
            return data


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
        logging.debug("getattr: " + path)
        file = self.files.findFileByPath(path)
        
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

    def mkdir(self, path, mode):
        print "mkdir: " + path

    def open(self, path, flags):
        
        file = self.files.findFileByPath(path)
        if file == -1:
            file = self.getFileEntry(path)
            if file == -1:
                print "ERROR, Couldnot get file"
                raise FuseOSError(EIO)
        if file.type == 'file':
            self.createChunks(file)

        return 0

    def flush(self, path, fh):
         print "flush: " + path

    def fsync(self, path, datasync, fh):
         print "fsync: " + path

    def release(self, path, fh):
         print "release: " + path

    def read(self, path, size, offset, fh):
        file = self.files.findFileByPath(path)
        if file == -1:
            file = self.getFileEntry(path)
            if file == -1:
                print "ERROR, Couldnot get file"
                raise FuseOSError(EIO)
        self.preRead(file, offset)
        data = self.readData(file,offset, size, self.crtchunk)
        return data
	
    def readdir(self, path, fh):
        listing = ['.', '..']
        file = self.files.findFileByPath(path)
        if file == -1:
            raise FuseOSError(EIO)
        else:
            for child in file.children:
                listing.append(child)
        return listing

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
