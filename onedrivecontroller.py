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

class OneDriveController(LoggingMixIn, Operations):
    def __init__(self, logfile=None):
        self.onedrive_api = OneDriveAPI()
        self.logfile = logfile
        self.files = ODFileManager()
        self.getFileEntry(0,True)
        self.crtchunk = -10
        self.chunk = {}

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
                logging.error('ERROR, Unknown filetype')
                raise FuseOSError(EIO)

            if isRoot:
                path = '/'
            else:
                tempPath = re.sub(r'/drive/root:','' ,meta['parentReference']['path'])
                path = tempPath + '/' + meta['name']
            
            file = ODFile(meta['id'], meta['name'], path, type,meta['size'], children)
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
                if offset + chunksize > filesize:  #In the Last chunk
                    if offset != 0: #case where we only have 1 chunk
                        offset -= offset - chunksize
                    csize = file.size - offset
                    file.chunks.append(Chunk(csize, offset, count))
                    offset += csize
                else:
                    file.chunks.append(Chunk(chunksize, offset, count))
                    offset += chunksize
                count += 1
        
        if len(file.chunks) != numchunks:
            print 'Error, Incorrect Number of Chunks. Expected = ' + str(numchunks) + 'Got = ' + str(len(file.chunks))
            raise FuseOSError(EIO)

    def getChunk(self, file, chunknum):
        if chunknum < 0 or chunknum >= len(file.chunks):
            logging.error('Error. Incorrect chunknumber')
            raise FuseOSError(EIO)
        else:
            chunk = file.chunks[chunknum]
            data = self.onedrive_api.download(file.path, chunk.offset, chunk.offset+chunk.size-1)

            if len(data) != chunk.size:
                logging.error('Error. Incorrect Data size. Expected = '+ str(chunk.size) + ' .Got = ' + str(len(data)))
                raise FuseOSError(EIO)
        return {'chunk': chunk, 'data': data}
    
    def getBufferParts(self):
        return 0

    def preRead(self, file, offset):
        crtchunknum = file.getChunkNumber(self.crtchunk, offset)

        if crtchunknum == -1:
            logging.error('Error. Could not find chunk')
            raise FuseOSError(EIO)
        else:
            if crtchunknum != self.crtchunk:
                self.crtchunk = crtchunknum
                self.chunk = self.getChunk(file, crtchunknum)
    
    def readData(self, file, offset, size, chunknum):
        chunk = self.chunk['chunk']
        chunkoffset = int(chunk.offset)
        chunksize = int(chunk.size)
        offset = int(offset)
        size = int(size)
        data = ''
        print ' IN READ'    
        if offset > file.size:
            logging.error('Error. Offset is greater than file size')
            raise FuseOSError(EIO)
        
        if chunknum != chunk.num:
            logging.error('Error, Reading wrong chunk. Expected = ' + str(chunknum) + ' .Reading = ' + str(chunk.num))
            raise FuseOSError(EIO)
         
        while chunkoffset < offset+size:
            if chunk.num != self.crtchunk:
                logging.error('Error, Reading wrong chunk. Expected = ' +str(self.crtchunk) + ' .Reading = ' + str(chunk.num))
                raise FuseOSError(EIO)

            if chunknum == len(file.chunks)-1: #Last Chunk
                s = file.size - offset
                if s == 0:
                    return '' #Zero size
                elif s <= size:
                    size = s

            if chunkoffset <= offset and chunkoffset+chunksize > offset+size:
                data += self.chunk['data'][(offset-chunkoffset):(offset-chunkoffset+size)]
                break
            elif chunkoffset <= offset and chunkoffset+chunksize <= offset+size:
                data += self.chunk['data'][offset-chunkoffset:]
                chunknum += 1
                if chunknum < len(file.chunks):
                    self.preRead(file, file.chunks[chunknum].offset)
                    chunk = self.chunk['chunk']
                    chunkoffset = int(chunk.offset)
                    chunksize = int(chunk.size)
                else:
                    break
            else:
                data += self.chunk['data'][:offset+size-chunkoffset]
                break


        if len(data) != size:
            logging.error('Error, Incorrect Data size. Expected = ' + str(size) + ' .Got = ' + str(len(data)))
            raise FuseOSError(EIO)
        else:
            return data