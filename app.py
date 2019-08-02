#!/usr/bin/python3

import logging
import base64
import requests
from datetime import datetime
from person import Person
from Crypto.Cipher import AES

logging.basicConfig(filename='app.log', filemode='w',level=logging.DEBUG, format='"%(asctime)s" - "%(levelname)s" - "%(message)s"')
logging.getLogger().addHandler(logging.StreamHandler())

BASE_COVI_URL='https://covi.int2.real.com'
ROOTPEOPLE_RESOURCE='{0}/rootpeople/{1}'
IMAGE_KEY_RESOURCE='{0}/imagekey'

KEY_HEADER_AUTHORIZATION='X-RPC-AUTHORIZATION'
KEY_HEADER_DIRECTORY='X-RPC-DIRECTORY'

ENCRYPTED_PATH_PSEUDO_PROTOCOL = 'ehttps://'

def createHeader(user_id, password, directory):
    encode_password =  base64.b64encode(bytes(password, 'utf-8')).decode('utf-8')
    return {
        KEY_HEADER_AUTHORIZATION : user_id+':'+encode_password,
        KEY_HEADER_DIRECTORY : directory
    }

header = createHeader('userid', 'passwd', 'directory')

def get_people():
    url = ROOTPEOPLE_RESOURCE.format(BASE_COVI_URL,'?count=0&include-expired=true')
    response = requests.get(url,  headers=header)
    if response.status_code == 200:
        response = response.json()
        if 'people' in response.keys():
            return response["people"]
    return None

def get_image_key():
    url = IMAGE_KEY_RESOURCE.format(BASE_COVI_URL)
    response = requests.get(url,  headers=header)
    if response.status_code == 200:
        response = response.json()
        return response['key']
    return None

def get_file(file_uri):
    if file_uri.startswith(ENCRYPTED_PATH_PSEUDO_PROTOCOL):
        file_uri = file_uri.replace(ENCRYPTED_PATH_PSEUDO_PROTOCOL, "https://")
    response = requests.get(file_uri,  headers=header)
    if response.status_code == 200:
        return response.content
    return None

def decrypt_file(file_uri, person_id, path, image_key):
    logging.debug('decrypt from URI {} using image key: {} for person-id: {} to: {}.'.format(file_uri, image_key, person_id, path+""+person_id))
    data = get_file(file_uri)
    if data is not None:
        logging.debug(len(data))
        iv = data[0:16]
        logging.debug(len(iv))
        key = base64.b64decode(image_key)
        encrypted_image_body = data[16:]
        logging.debug(len(encrypted_image_body))
        aes = AES.new(key, AES.MODE_CBC, iv)
        decrypted_data = aes.decrypt(encrypted_image_body)
        f = open('output/{}.jpg'.format(person_id), 'w+b')
        f.write(decrypted_data)
        f.close()

def regular_file_creation(file_uri, person_id, path):
    logging.info('do NOT decrypt from URI {} for person-id {} to {}'.format(file_uri, person_id, path+""+person_id+".jpg"))
    data = get_file(file_uri)
    if data is not None:
        f = open('output/{}.jpg'.format(person_id), 'w+b')
        f.write(data)
        f.close()

def get_image_file(person, path, image_key):
    if person is not None:
        file = person.image_uri
        person_id = person.person_id
        if file.startswith(ENCRYPTED_PATH_PSEUDO_PROTOCOL):
            decrypt_file(file, person_id, path, image_key)
        else:
            regular_file_creation(file, person_id, path)

def main():
    print("Starting process...")

    image_key = get_image_key()
    path = 'output/'
    people = get_people()
    logging.info("Nummber of people found {}".format(len(people)))
    for item in people:
        if 'personId' in item.keys():
            personId = item['personId']
            if 'unmergedImageURI' in item.keys():
                imageUri = item['unmergedImageURI']
            else:
                imageUri = item['imageURI']
            person = Person(personId, imageUri)
            get_image_file(person, path, image_key)

if __name__ == '__main__':
    start_time = datetime.now()
    try:
        main()
    except Exception as e:
        logging.error('An error has ocurred. {}'.format(e))
    finally:
        end_time = datetime.now()
        elapsed_time = end_time-start_time
        logging.info('...ending process. Time slapsed {}'.format(elapsed_time))