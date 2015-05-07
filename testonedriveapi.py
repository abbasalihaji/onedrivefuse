from onedriveapi import OneDriveAPI
from odfile import ODFile
api = OneDriveAPI()
root = api.getMeta(-1, True) #getting the root element
print root
#for child in root['children']:
#    print 'Getting Child'
#    print api.getMeta(child['id'], False, False)

#print api.getMeta('9E2B723769ACD40C!5195')

