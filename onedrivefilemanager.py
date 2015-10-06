#!/usr/bin/env python

import Queue
import logging

class File:
    def __init__(self, cloudPath, type, size):
        self.cloudPath = cloudPath
        self.type = type
        self.size = size
        self.chunks = []
        self.tempFile = "" #temporary file path

    def getChunkNumber(self, guess, offset):
        numChunks = len(self.chunks)
        if numChunks <= 0 :
            return -1
        else:
            if guess < numChunks:
                chunk = self.chunks[guess]
                if int(chunk.cloudOffSet) <= int(offset) and (int(chunk.cloudOffSet) + int(chunk.size)) > int(offset):
                    return guess
                else:
                    if (guess+1) < numChunks:
                        chunk = self.chunks[guess+1]
                        if int(chunk.cloudOffSet) <= int(offset) and (int(chunk.cloudOffSet) + int(chunk.size)) > int(offset):
                            return guess+1
        counter = 0
        while counter < numChunks:
            chunk = self.chunks[counter]
            if int(chunk.cloudOffSet) <= int(offset) and (int(chunk.cloudOffSet) + int(chunk.size)) > int(offset):
                return counter
            counter += 1
        return -1


class FileManager:
    def __init__(self):
        self.files = [] #Store an array of File objects

    def findFileByPath(self, path):
        for file in self.files:
            if file.cloudPath == path:
                return file
        return -1

    def addFile(self, file):
        if self.findFileByPath(file.cloudPath) == -1:
            self.files.append(file)
        else:
            #Error, file exists
            return -1


class Chunk:
    def __init__(self, size, cloudOffSet, num, isAvailable = False):
        self.num = num
        self.size = size
        self.cloudOffSet = cloudOffSet
        self.isAvailable = isAvailable
        self.localOffSet = -1           #Not in local storage initially
