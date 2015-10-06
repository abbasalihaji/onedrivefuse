import unittest
from onedrivefilemanager import File, FileManager, Chunk

class FileTest(unittest.TestCase):

    def setUp(self):
        self.file = File('/test.mkv', 'file', 1024)
        counter = 0
        crtOffset = 0
        crtChunkNum = 0
        while crtOffset < self.file.size:
            chunk = Chunk(64, crtOffset, counter)
            self.file.chunks.append(chunk)
            counter += 1
            crtOffset += 64
   
    def testGetChunkNumberNoChunks(self):
        file = File('/', 'file', 1024)
        self.failUnlessEqual(-1, file.getChunkNumber(5, 0))

    def testGetChunkNumberMiddleCorrectGuess(self):
        chunkNum = self.file.getChunkNumber(1, 65)
        self.failUnlessEqual(chunkNum, 1)
    
    def testGetChunkNumberMiddleWrongGuess(self):
        chunkNum = self.file.getChunkNumber(2, 65)
        self.failUnlessEqual(chunkNum, 1)

    def testGetChunkNumberZeroCorrectGuess(self):
        chunkNum = self.file.getChunkNumber(0, 0)
        self.failUnlessEqual(chunkNum, 0)

    def testGetChunkNumberZeroWrongGuess(self):
        chunkNum = self.file.getChunkNumber(-1, 0)
        self.failUnlessEqual(chunkNum, 0)

    def testGetChunkNumberEndCorrectGuess(self):
        chunkNum = self.file.getChunkNumber(15, 1023)
        self.failUnlessEqual(chunkNum, 15)

    def testGetChunkNumberEndWrongGuess(self):
        chunkNum = self.file.getChunkNumber(55000, 1023)
        self.failUnlessEqual(chunkNum, 15)

    def testGetChunkNumbereBoundry1(self):
        chunkNum = self.file.getChunkNumber(14, 896)
        self.failUnlessEqual(chunkNum, 14)

    def testGetChunkNumberBoundry2(self):
        chunkNum = self.file.getChunkNumber(0, 63)
        self.failUnlessEqual(chunkNum, 0)

    def testGetChunkNumberOutOfBounds1(self):
        chunkNum = self.file.getChunkNumber(5, -1)
        self.failUnlessEqual(chunkNum, -1)

    def testGetChunkNumberOutOfBounds2(self):
        chunkNum = self.file.getChunkNumber(15, 1024)
        self.failUnlessEqual(chunkNum, -1)

class FileManagerTest(unittest.TestCase):
    
    def setUp(self):
        self.fileManager = FileManager()
        file = File('/test.mkv', 'file', 1024)
        self.failIfEqual(self.fileManager.addFile(file), -1)

    def testRepeatAdd(self):
        print(len(self.fileManager.files))
        file = File('/test.mkv', 'file', 1024)
        self.failUnlessEqual(self.fileManager.addFile(file), -1)

    def testFindCorrectPath(self):
        path = '/test.mkv'
        self.failIfEqual(self.fileManager.findFileByPath(path), -1)

    def testFindWrongPath(self):
        path = '/'
        self.failUnlessEqual(self.fileManager.findFileByPath(path), -1)


if __name__ == '__main__':
    unittest.main()
