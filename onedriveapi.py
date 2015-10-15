import requests
import json
import re
from odfile import ODFile
from fuse import FUSE, FuseOSError, Operations, LoggingMixIn, fuse_get_context
from requests_futures.sessions import FuturesSession

class OneDriveAPI:
    
    def __init__(self):
        self.mainurl = 'https://api.onedrive.com/v1.0'
        self.readConfig('./configfile')
        self.authorization = {'Authorization': 'Bearer ' + self.accesstoken }
        self.session = FuturesSession(max_workers=self.maxWorkers)
    
    
    def readConfig(self, path):
        f = open(path, 'r')
        
        for line in f:
            split = re.split(r'[=\n]', line)
            category = split[0]
            if category == 'accesstoken':
                self.accesstoken = split[1]
            elif category == 'refreshtoken':
                self.refreshtoken = split[1]
            elif category == 'clientid':
                self.clientid = split[1]
            elif category == 'clientsecret':
                self.clientsecret = split[1]
            elif category == 'code':
                self.code = split[1]
            elif category == 'redirect':
                self.redirect = split[1]
            elif category == 'chunksize':
                self.chunksize = int(split[1])
            elif category == 'maxWorkers':
                self.maxWorkers = int(split[1])
            elif category == 'logFile':
                self.logFile = split[1]

    def updateConfig(self, path, refreshtoken, accesstoken): #change this later for other paramters    
        f = open(path, 'r+')
        lines = []
        for line in f:
            lines.append(line)
        
        f.close()
        f = open(path, 'w')
        for line in lines:
             split = re.split(r'[=\n]', line)
             if split[0] == 'accesstoken':
                f.write(split[0]+'='+ accesstoken  +'\n')
             elif split[0] == 'refreshtoken':
                f.write(split[0]+'='+ refreshtoken  + '\n')
             else:
                f.write(line)
            
    def refreshToken(self):
        headers = {'content-type': 'application/x-www-form-urlencoded'}
        data = 'client_id='+self.clientid+'&redirect_uri='+self.redirect+'&client_secret='+self.clientsecret+'&refresh_token='+self.refreshtoken+'&grant_type=refresh_token'
        response = self.post('https://login.live.com/oauth20_token.srf', headers, data)
        r = json.loads(response)
        self.accesstoken = r['access_token']
        self.refreshtoken = r['refresh_token']
        self.authorization = {'Authorization': 'Bearer ' + self.accesstoken }
        self.updateConfig('./configfile', r['refresh_token'], r['access_token'])
        
    def getMeta(self, path, isRoot = False, getChildren = True):
        if isRoot:
            url =  '/drive/items/root'
        else:
            url = '/drive/root:' + path
        
        if getChildren:
            url = url + '?expand=children'
        
        headers = {}
        response = self.get(url, headers, True)
        return response
 
    def download(self, path, startbyte, endbyte, background_callback=None):
        url = '/drive/root:' + path  +  ':/content'
        headers = {'Range': 'bytes=' + str(startbyte) + '-' + str(endbyte)}
        #response = self.get(url, headers, False, True)
        headers.update(self.authorization)
        self.session.get(self.mainurl + url, headers=headers, allow_redirects=True, background_callback=background_callback) 

    def get(self, url, headers, decodeResponse = False, allowredirect = False):
        url = self.mainurl + url
        headers.update(self.authorization)
        print 'getting = ' + url
        response = requests.get(url, headers=headers, allow_redirects=allowredirect)
        print response.status_code
        print "getsucezz"
        r = json.loads(response.text)

        if 'error' in r:
            if r['error']['code'] == 'unauthenticated':
                self.refreshToken()
                headers.update(self.authorization)
                response = requests.get(url, headers=headers)
                r = json.loads(response.text)
                if 'error' in r:
                    print 'ERROR1 '
                    print r
            else:
                print 'ERROR2 '
                print r
        if decodeResponse:
            print "Decoding response"
            return r
        else:
            return response.text

    def post(self, url, headers, data):
        
        response = requests.post(url, headers=headers, data=data)

        r = json.loads(response.text)

        if 'error' in r:
            print 'ERROR3 '
            print r

        return response.text
