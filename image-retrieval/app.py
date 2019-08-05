#!/usr/bin/python3

import logging
import base64
import requests
from datetime import datetime
from person import Person
from Crypto.Cipher import AES

logging.basicConfig(filename='app.log', filemode='w',level=logging.DEBUG, format='"%(asctime)s" - "%(levelname)s" - "%(message)s"')
logging.getLogger().addHandler(logging.StreamHandler())

session = requests.Session()

BASE_COVI_URL='https://covi.int2.real.com'
ROOTPEOPLE_RESOURCE='{0}/rootpeople/{1}'
IMAGE_KEY_RESOURCE='{0}/imagekey'

KEY_HEADER_AUTHORIZATION='X-RPC-AUTHORIZATION'
KEY_HEADER_DIRECTORY='X-RPC-DIRECTORY'

ENCRYPTED_PATH_PSEUDO_PROTOCOL = 'ehttps://'

PATH = 'output/{}.jpg'

def createHeader(user_id, password, directory):
    encode_password =  base64.b64encode(bytes(password, 'utf-8')).decode('utf-8')
    header_user = user_id+':'+encode_password
    logging.debug('userId:password {}'.format(header_user))
    return {
        KEY_HEADER_AUTHORIZATION : header_user,
        KEY_HEADER_DIRECTORY : directory
    }

header = createHeader('userid', 'passwd', 'directory')

def get_people():
    url = ROOTPEOPLE_RESOURCE.format(BASE_COVI_URL,'?count=0&include-expired=true')
    response = session.get(url,  headers=header)
    if response.status_code == 200:
        response = response.json()
        if 'people' in response.keys():
            return response["people"]
    return None

def get_image_key():
    url = IMAGE_KEY_RESOURCE.format(BASE_COVI_URL)
    response = session.get(url,  headers=header)
    if response.status_code == 200:
        response = response.json()
        if 'key' in response.keys():
            return response['key']
    return None

def get_file(file_uri):
    if file_uri.startswith(ENCRYPTED_PATH_PSEUDO_PROTOCOL):
        file_uri = file_uri.replace(ENCRYPTED_PATH_PSEUDO_PROTOCOL, "https://")
    response = session.get(file_uri,  headers=header)
    if response.status_code == 200:
        return response.content
    return None

def decrypt_file(file_uri, person_id, image_key):
    logging.debug('decrypting from URI {} using image key: {} for person-id: {} to: {}.'.format(file_uri, image_key, person_id, PATH.format(person_id)))
    data = get_file(file_uri)
    if data is not None:
        key = base64.b64decode(image_key) #use image  key
        iv = data[0:16] #take first 16 bytes
        aes = AES.new(key, AES.MODE_CBC, iv)
        encrypted_image_body = data[16:] #take the remaining bytes besides the first 16 to compose the body of the image
        return aes.decrypt(encrypted_image_body)

def regular_file_creation(file_uri, person_id):
    logging.info('do NOT decrypt from URI {} for person-id {} to {}'.format(file_uri, person_id, PATH.format(person_id)))
    return get_file(file_uri)

def get_image_file(person, image_key):
    if person is not None:
        file = person.image_uri
        person_id = person.person_id
        data = None
        if file.startswith(ENCRYPTED_PATH_PSEUDO_PROTOCOL):
            data = decrypt_file(file, person_id, image_key)
        else:
            data = regular_file_creation(file, person_id)

        if data is not None:
            with open(PATH.format(person_id), 'w+b') as f:
                f.write(data)

def process():
    image_key = get_image_key()
    people = get_people()
    logging.info("Nummber of people found {}".format(len(people)))
    for item in people:
        if 'personId' in item.keys():
            personId = item['personId']
            if 'unmergedImageURI' in item.keys():
                imageUri = item['unmergedImageURI']
            elif 'imageURI' in item.keys():
                imageUri = item['imageURI']
            else:
                imageUri = None
            if imageUri is not None:
                get_image_file(Person(personId, imageUri), image_key)

if __name__ == '__main__':
    logging.info("Starting process...")
    start_time = datetime.now()
    try:
        process()
    except Exception as e:
        logging.error('An error has ocurred. {}'.format(e))
    finally:
        end_time = datetime.now()
        elapsed_time = end_time - start_time
        logging.info('...ending process. Time slapsed {}'.format(elapsed_time))
