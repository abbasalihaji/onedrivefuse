#!/usr/bin/env python

from __future__ import with_statement

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

from fuse import FUSE, FuseOSError, Operations, LoggingMixIn, fuse_get_context
from onedriveapi import OneDriveAPI
from odfile import ODFileManager, ODFile

class OneDriveFUSE(LoggingMixIn, Operations):
    def __init__(self, logfile=None):
        self.onedrive_api = OneDriveAPI()
        self.logfile = logfile
        self.files = ODFileManager()
        self.getFileEntry(0,True)

    def getFileEntry(self, id, isRoot = False):
        meta = self.onedrive_api.getMeta(id, isRoot)
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
            self.files.files.append(file)
            return file

    def getParts(self, path):
        return 0
    
    def getBufferParts(self):
        return 0

    def preRead(self, file, offset):
        return 0
    
    def readData(self, file, offset, size, chunknum):
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
            print 'Could not find file'
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
        return 0

    def flush(self, path, fh):
         print "flush: " + path

    def fsync(self, path, datasync, fh):
         print "fsync: " + path

    def release(self, path, fh):
         print "release: " + path

    def read(self, path, size, offset, fh):
        return 0
	
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
    print args.__dict__
    fuse_args.update(options)

    logfile = None
    if fuse_args.get('debug', False) == True:
        # send to stderr same as where fuse lib sends debug messages
        logfile = stderr
 
    print fuse_args
    fuse = FUSE(OneDriveFUSE(logfile=logfile), mount_point, False, **fuse_args)

if __name__ == "__main__":
    main()
