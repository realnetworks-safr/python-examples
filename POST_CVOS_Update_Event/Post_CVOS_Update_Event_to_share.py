#!/usr/bin/python

import sys
import time
import json
import logging
import requests
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler
import os
import base64
from PIL import Image, ImageEnhance
import io
import uuid

# args
if len(sys.argv) <= 1:        
        print('')
        print ('Please check image path has been informed properly')
        sys.exit(1)

#If specific personId given
if (len(sys.argv) > 1):	
        image_path = sys.argv[1]
        


# configure logging
logFile = './post_image.log'

# read arguments
logger = logging.getLogger('Rotating Log')
logFormatter = logging.Formatter('%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s] %(message)s')
# configure file logging
fileHandler = TimedRotatingFileHandler(logFile, when='d', interval=1, backupCount=14)
fileHandler.setFormatter(logFormatter)
logger.addHandler(fileHandler)
# configure console logging
consoleHandler = logging.StreamHandler()
consoleHandler.setFormatter(logFormatter)
logger.addHandler(consoleHandler)

# set logging level
logger.setLevel(logging.INFO)
# uncomment to enable debug
#logger.setLevel(logging.DEBUG)
logger.info('')


#default setup
startTime = int(time.time() * 1000)
#print(startTime)
endTime = int((time.time() + 3 ) * 1000)
user_id = 'XXXXX'
password = 'XXXXX'
header_auth = "{0}:{1}".format(user_id, password)
eventId = str(uuid.uuid4())
#print(eventId)
#base_url = 'http://192.168.43.107:18080{0}'
base_url = 'https://covi.real.com{0}'
url= base_url.format("/people?insert=false&update=false&merge=false")
url= url + "&detect-age=true&detect-gender=true&detect-sentiment=true"
url= url + "&X-RPC-FACES-DETECT-THRESHOLD=0&X-RPC-MIN-SIZE=120"
#Create event
url= url + "&event=any&site=PY&source=py_script&start-time=" + str(startTime) + "&end-time=" + str(endTime) + "&context=media&event-id=" + eventId
headers = {'Content-Type': 'application/octet-stream',
           'X-RPC-AUTHORIZATION' : header_auth,
           'Authorization' : 'main'}
#CVOS URL
#url_cvos=http://192.168.43.107:18086/obj/
base_url_cvos= 'https://cvos.real.com/obj/'
url_cvos = base_url_cvos + base64.b64encode(eventId.encode("utf-8")).decode("utf-8") + "/face"
#Event server URL
#url_event=http://192.168.43.107:18082/events?sinceTime=0&eventId=
base_url_event= 'https://cv-event.real.com/'
url_get = base_url_event + "events?sinceTime=0&eventId=" + eventId

#JPEG name
image_filename = os.path.basename(image_path)
upload_file=open(image_filename, 'rb')

#Get request
response = requests.post(url=url, headers=headers, data=upload_file)
result = json.loads(response.text)

#FR + Crop function
def fr(image_filename):
        if response.ok:
                face = result['identifiedFaces'][0]
                if "age" in str(face):
                        age = int(face["attributes"]["age"]["age"])
                else:
                        age = "none"
                if "gender" in str(face):
                        gender = face["attributes"]["gender"]["gender"]
                        gender_confidence = face["attributes"]["gender"]["confidence"]
                else:
                        gender= "none"
                        gender_confidence= "none"
                event = {
                        "age" : age,
                        "gender" : gender,
                        "gender_confidence" : gender_confidence,
                        "endTime" : endTime,
                        "startTime" : startTime,                        
                        }

                        
                        
                #determine face coordinates
                paddingFactor = 0.25
                upload_file = Image.open(image_filename)
                upload_fileWidth = upload_file.size[0]
                upload_fileHeight = upload_file.size[1]
                offsetX = face["offsetX"]
                offsetY = face["offsetY"]
                faceWidth = face["attributes"]["dimension"]["width"]
                faceHeight = face["attributes"]["dimension"]["height"]
                faceWidthPadding = faceWidth * paddingFactor
                faceHeightPadding = faceHeight * paddingFactor
                #bounding box
                faceLeft = upload_fileWidth * offsetX - faceWidthPadding
                faceUpper = upload_fileHeight * offsetY - faceWidthPadding
                faceRight = faceLeft + faceWidth + faceWidthPadding * 2
                faceLower = faceUpper + faceHeight + faceWidthPadding * 2
                #cut out face from image
                faceImage = upload_file.crop((faceLeft, faceUpper, faceRight, faceLower))
                faceImage.save('crop.jpg', format='PNG')
                faceImageBytes = io.BytesIO()
                faceImage.save(faceImageBytes, format='PNG')
                cvos(faceImageBytes,url_cvos)
                cevent(event,url_get)
                print('Age: ' + str(age))
                print('Gender: ' + str(gender) + '  Confidence: ' + str(gender_confidence))
                logger.info('OK ' + 'Image: ' + str(image_path) + ' status: ' + str(response.status_code) + ' message: ' + str(response.text) + ' url. called: ' + str(url))

        else:
                logger.info('[NOK] ' + 'Image: ' + str(image_path) + ' status: ' + str(response.status_code)+ ' message: ' + str(response.text) + ' url. called: ' + str(url))


#Function to send image to a third party system
def cvos(faceImageBytes,url_cvos):
        #make the request 
        response = requests.post(url=url_cvos, headers=headers, data=faceImageBytes.getvalue())
        #print(response.status_code)

#Function to send event details to a third party system
def cevent(event,url_get):    
        headers = {"Authorization": 'main', "X-RPC-AUTHORIZATION": header_auth, "Content-Type": "application/json"}
        #get event personId
        #print(url_get)
        getresponse = requests.get(url_get, headers=headers)
        #print(getresponse.status_code)
        if getresponse.ok:
            result = json.loads(getresponse.text)
            #print(result)
            if "events" in result:
                arrEvts = result["events"]
                for item in arrEvts:
                    personid = item["personId"]
                    url = base_url_event + "person/" + personid
                    #print(url)
        #make the request to update Events
                    response = requests.put(url=url, headers=headers, data=json.dumps(event))
          
        

fr(image_filename)

