#!/usr/bin/env python

import Queue
import logging
class ODFileManager:

    def __init__ (self):
	    self.files = []

    def findFileById(self, id):
	    for file in self.files:
	        if file.id == id:
		        return file
	    return -1

    def findFileByPath(self, path):
        for file in self.files:
            if file.path == path:
                return file
        return -1

class ODFile:

    def __init__ (self, id, name, path, type, size, children):
        self.id = id
        self.name = name
        self.path = path
        self.type = type
        self.size = size
        self.children = children
        self.chunks = []
    
    def getChunkNumber(self, guess, offset):
        numChunks = len(self.chunks)
        if numChunks <= 0:
            return -1
        else:
            if guess < numChunks and guess >= 0:
                chunk = self.chunks[guess]
                if int(chunk.offset) <= int(offset) and (int(chunk.offset) + int(chunk.size)) > int(offset):
                    return guess
                else:
                    if (guess+1) < numChunks:
                        chunk = self.chunks[guess+1]
                        if int(chunk.offset) <= int(offset) and (int(chunk.offset) + int(chunk.size)) > int(offset):
                            return guess+1
            counter = 0
            while counter < numChunks:
                chunk = self.chunks[counter]
                if int(chunk.offset) <= int(offset) and (int(chunk.offset) + int(chunk.size)) > int(offset):
                    return counter
                counter += 1
            return -1

class Chunk:

    def __init__ (self, size, offset, num, isAvailable = False):
        self.num = num
        self.size = size
        self.offset = offset
        self.isAvailable = isAvailable
        self.localoffset = 0

class CQueue:
	
    def __init__ (self, size):
	    self.q = Queue.Queue(size-1)
	    self.currentChunk = ""
	
    def get(self):
        logging.warning("Getting from queue")
        if self.q.empty():
	        print "Getting from Empty"
        else:
            self.currentChunk = self.q.get()

    def empty(self):
	    return self.q.empty()

    def put(self, data):
        logging.warning("Putting on queue")
        self.q.put(data)

    def clear(self):
        while not self.q.empty():
            try:
                self.q.get(False)
            except Queue.Empty:
                continue
	        self.q.task_done()
