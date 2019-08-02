class Person(object):
    def __init__(self,person_id,image_uri):
        self.person_id = person_id
        self.image_uri = image_uri
        
    def __str__(self):
        return self.person_id+" - "+self.image_uri