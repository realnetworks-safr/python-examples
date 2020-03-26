#!/usr/bin/python3

from datetime import datetime
import sys
import time
import logging
import os
import requests
import base64
import json
import shutil
import pathlib

logging.basicConfig(filename='app.log', filemode='w',level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logging.getLogger().addHandler(logging.StreamHandler())

user_id = 'rroslocal1' # CHANGE
passwd = 'testit1234' # CHANGE
directory = 'main' # CHANGE is using a different directory
source = 'batchImport'

ORIGINAL_PATH = 'images/' # CHANGE if path is different 
BACKUP_PATH = 'backup/'
ERROR_PATH = 'error/'

MOVE_FILES = True

SERVER_URL = 'http://10.40.34.180' # CHANGE the ip of the server
PEOPLE_URL = SERVER_URL + ':8080'
OBJECT_URL = SERVER_URL + ':8086/obj/{0}/face'
EVENT_URL = SERVER_URL + ':8082/event'

PEOPLE_URL = PEOPLE_URL+("/people?insert=true&update=false&merge=false")
PEOPLE_URL = PEOPLE_URL+"&min-size=80&largest-only=true&event=none" # only take largest face in image
PEOPLE_URL = PEOPLE_URL+"&site={0}&source={1}&start-time={2}&end-time={3}"

header_data = {}
header_json = {}

def createHeaders(user_id, password, directory):
    enconding = 'utf-8'
    encode_password =  base64.b64encode(bytes(password, enconding)).decode(enconding)
    header_auth = "{0}:{1}".format(user_id, encode_password)
    global header_data
    header_data =  {
        'Content-Type': 'application/octet-stream',
        'X-RPC-AUTHORIZATION' : header_auth,
        'X-RPC-DIRECTORY' : directory
    }
    global header_json
    header_json =  {
        'Content-Type': 'application/json',
        'X-RPC-AUTHORIZATION' : header_auth,
        'X-RPC-DIRECTORY' : directory
    }

def get_quality_params(personObj):
    response = {}
    attributes = personObj['attributes']
    if 'centerPoseQuality' in attributes.keys():
        response.update({'centerPoseQuality' : attributes['centerPoseQuality']})
    if 'sharpnessQuality' in attributes.keys():
        response.update({'sharpnessQuality' : attributes['sharpnessQuality']})
    if 'contrastQuality' in attributes.keys():
        response.update({'contrastQuality' : attributes['contrastQuality']})
    return response


def match(sess, upload_file,fileName,fullFileName):
    match = False
    epochT = int(round( time.time() * 1000) )
    post_url = PEOPLE_URL.format(fileName, source,epochT,epochT+1) # for seb - take filename as site

    with sess.post(post_url,  headers=header_data, data=upload_file) as response:
        if response.status_code == requests.codes.created:
            person = response.json()['identifiedFaces']
            if (len(person) < 1):
                logging.error('no face detected for {}'.format(upload_file.name))
            elif (len(person) > 1):
                logging.warning('more than one face detected for {}'.format(upload_file.name))
            elif 'personId' not in person[0].keys() and 'mediaId' in person[0].keys():
                logging.error('{} not registered. Face not detected. Check detected quality attributes: {}'.format(upload_file.name, get_quality_params(person[0])))
                match = True 
            elif 'personId' in person[0].keys() and 'newId' in person[0].keys() and person[0]['newId']==True:
                logging.info('Face detected for {}. registered. Person-Id {}'.format(upload_file.name, person[0]['personId']))
                match = True
            elif 'personId' in person[0].keys() and 'newId' not in person[0].keys():
                logging.info('New face detected for {}. Updated. Person-Id {}'.format(upload_file.name, person[0]['personId']))
                match = True
        else:
            logging.error('Match failed:'+ str(response.status_code))

    if (match):
                #post event (only biggest face considered)
                face = person[0]
                eventId = source+str(epochT) # take souce + timestamp as identifier
                event = {"eventId":eventId, 
                         "siteId":fileName, # for seb - take filename as site
                         "sourceId":source,
                         "startTime":epochT,
                         "endTime":epochT+1000, # take 100 msec as event duration
                         "context":"live",
                         "type":"person",
                         "left":face['offsetX'],
                         "top":face['offsetY'],
                         "width":face['relativeWidth'],
                         "height":face['relativeHeight']
                } 
                if ('personId' in face):
                    if ('rootPersonId' in face): rootId = face['rootPersonId']
                    else: rootId = face['personId'] 
                    event.update({"rootPersonId":rootId,"personId":face['personId'],"similarityScore":face['similarityScore']})
                    # root person id needed to 
                if ('idClass' in face): 
                        event.update({"idClass":face['idClass']})

                with sess.post(EVENT_URL,  headers=header_json, json=event) as response:
                    if 200 <= response.status_code <= 299:
                        logging.info('Event created ' + eventId)
                    else: 
                        logging.error('Event post failed:'+ str(response.status_code))

                # now add same image as thumbnail image
                post_url = OBJECT_URL.format(base64.b64encode(bytes(eventId, 'utf-8')).decode('utf-8'))

                # re-open file
                with open(fullFileName, 'rb') as data:
                    with sess.post(post_url,  headers=header_data, data=data) as response:
                        if 200 <= response.status_code <= 299:
                            logging.info('Thumbnail uploaded ' + eventId)
                        else: 
                            logging.error('Thumbnail upload failed:'+ str(response.status_code))

    return match

def process(path):
    sess = requests.Session()

    # create backup/error directory if not existing
    pathlib.Path(BACKUP_PATH).mkdir(parents=True, exist_ok=True)
    pathlib.Path(ERROR_PATH).mkdir(parents=True, exist_ok=True)
    logging.info("Processing Path: {}".format(path) )

    for r, d, f in os.walk(path):
        for file in f:
            if '.jpg' in file:
                full_path_of_file = os.path.join(r, file)
                logging.info("Processing file: {}".format(full_path_of_file) )
                try: 
                    with open(full_path_of_file, 'rb') as data:
                        success = match(sess, data, file,full_path_of_file)
                    if (MOVE_FILES):
                        if (success): #move file into success folder 
                             shutil.move(full_path_of_file,BACKUP_PATH+file)
                        else:
                            logging.warning("File import failed for "+file)
                            shutil.move(full_path_of_file,ERROR_PATH+file)
                except FileNotFoundError:
                    logging.error('Missing file {}'.format(f))


if __name__ == '__main__':
    logging.info("Starting process...")
    start_time = datetime.now()
    try:
        createHeaders(user_id, passwd, directory)
        process(ORIGINAL_PATH)
        end_time = datetime.now()
        elapsed_time = end_time - start_time
        logging.info('...ending process. Time slapsed {}'.format(elapsed_time))
    except Exception as e:
        logging.error('An error has ocurred. {}'.format(e))

