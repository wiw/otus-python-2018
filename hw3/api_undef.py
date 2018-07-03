import abc
import json
import datetime
import logging
import hashlib
import uuid
import re
from optparse import OptionParser
from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
import scoring
from pprint import pprint as view
import inspect
SALT = "Otus"
ADMIN_LOGIN = "admin"
ADMIN_SALT = "42"
OK = 200
BAD_REQUEST = 400
FORBIDDEN = 403
NOT_FOUND = 404
INVALID_REQUEST = 422
INTERNAL_ERROR = 500
ERRORS = {
    BAD_REQUEST: "Bad Request",
    FORBIDDEN: "Forbidden",
    NOT_FOUND: "Not Found",
    INVALID_REQUEST: "Invalid Request",
    INTERNAL_ERROR: "Internal Server Error",
}
UNKNOWN = 0
MALE = 1
FEMALE = 2
GENDERS = {
    UNKNOWN: "unknown",
    MALE: "male",
    FEMALE: "female",
}
INTERNAL_METHOD = ['is_admin', 'validate', 'check_valid', 'clean']
rqst0 = {
    "account": "horns&hoofs",
    "login": "h&f",
    "method": "online_score",
    "token": "55cc9ce545bcd144300fe9efc28e65d415b923ebb6be1e19d2750a2c03e80dd209a27954dca045e5bb12418e7d89b6d718a9e35af3",
    "arguments": {
        "phone": "559985002040",
        "email": "j.mormont@bearisland.wst",
        "first_name": "Jorah",
        "last_name": "Mormont",
        "birthday": "28.03.255",
        "gender": 1
    }
}
rqst1 = {
    "account": "horns&hoofs",
    "login": "admin",
    "method": "clients_interests",
    "token": "d3573aff1555cd67dccf21b95fe8c4dc8732f33fd4e32461b7fe6a71d83c947688515e36774c00fb630b039fe2223c991f045f13f2",
    "arguments": {
        "client_ids": [1,2,3,4],
        "date": "20.07.2017"
    }
}
class Field(object):
    def __init__(self, required=False, nullable=False):
        self.required = required
        self.nullable = nullable
    
    empty_values = [{}, "", " ", None, [], ()]
    
    def check_field(self, value):
        return value
    
    def clean(self, value):
        if value in self.empty_values and self.required and not self.nullable:
            raise ValueError({"code": INVALID_REQUEST, "error": "Validation error field '{}'".format(self.__class__.__name__)})
        else:
            value = self.check_field(value)
        return value

class CharField(Field):
    def check_field(self, value):
        if type(value) is str:
            return value
        raise ValueError("'{}' is not string".format(value))
        
class EmailField(CharField):
    def check_field(self, value):
        regex = re.compile("^\S*@(.*)\.([a-z].*)$")
        if regex.match(value) is not None:
            return value
        raise ValueError("'{}' is not correct e-mail. Use this regExp '^\S*@(.*)\.([a-z].*)$' for check your e-mail (https://regex101.com/)".format(value))
        
class ClientIDsField(Field):
    def check_field(self, value):
        if type(value) is list and all([True for x in value if type(x) is int]):
            return value
        raise ValueError("'{}' is not list of integer. Use this format: '[0, 1, 2]'".format(value))

class DateField(Field):
    def check_field(self, value):
        try:
            datetime.datetime.strptime(value, '%d.%m.%Y')
            return value
        except ValueError:
            raise ValueError("'{}' is not date. Please enter a date in the following format: 'DD.MM.YYYY'".format(value))

class ArgumentsField(Field):
    def check_field(self, value):
        if type(value) is dict:
            return value
        raise ValueError("'{}' is not dictionary of arguments".format(value))

class PhoneField(Field):
    def check_field(self, value):
        value = str(value)
        if value and all(x.isdigit() for x in value):
            return unicode(value)
        raise ValueError("'{}' is not phone number. Use only digit on your number.".format(value))


class BirthDayField(DateField):
    def check_field(self, value):
        bd = super(BirthDayField, self).check_field(value)
        diff = datetime.datetime.now().date() - bd
        if (diff.days / 365) < 100 and (diff.days / 365) > 5:
            return bd
        raise ValueError("'{}'. Hmm, you're either a young genius or a centenarian. Specify the actual date of birth.".format(value))


class GenderField(Field):
    def check_field(self, value):
        if type(value) is int and value in GENDERS.keys():
            return value
        raise ValueError("'{}' this is not a sex sign. Use a number from zero to two. So like this: {}".format(value, GENDERS))

            
class ClientsInterestsRequest(object):
    client_ids = ClientIDsField(required=True)
    date = DateField(required=False, nullable=True)
    
class OnlineScoreRequest(object):
    first_name = CharField(required=False, nullable=True)
    last_name = CharField(required=False, nullable=True)
    email = EmailField(required=False, nullable=True)
    phone = PhoneField(required=False, nullable=True)
    birthday = BirthDayField(required=False, nullable=True)
    gender = GenderField(required=False, nullable=True)


class MethodRequest(object):
    account = CharField(required=False, nullable=True)
    login = CharField(required=True, nullable=True)
    token = CharField(required=True, nullable=True)
    arguments = ArgumentsField(required=True, nullable=True)
    method = CharField(required=True, nullable=False)

    @property
    def is_admin(self):
        return self.login == ADMIN_LOGIN
    
def check_auth(request):
    if request.is_admin:
        digest = hashlib.sha512(datetime.datetime.now().strftime("%Y%m%d%H") + ADMIN_SALT).hexdigest()
    else:
        digest = hashlib.sha512(request.account + request.login + SALT).hexdigest()
    if digest == request.token:
        return True
    return False
    
def method_handler(request, ctx, store):
    requests_map = {
        'clients_interests': ClientsInterestsRequest,
        'online_score': OnlineScoreRequest
    }
    method_request = MethodRequest
    validated_request = {}
    for request_name, request_value in request.items():
        validated_request.setdefault(request_name, getattr(method_request, request_name).clean(request_value))
    if method_request.is_admin:
        return {"score": ADMIN_SALT}
    return validated_request

method_handler(rqst0, None, None)
method_handler(rqst1, None, None)