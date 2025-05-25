from flask_login import UserMixin

class User(UserMixin):
    def __init__(self, id, email, name):
        self.id = id
        self.email = email
        self.name = name
    
    def get_id(self):
        return str(self.id)