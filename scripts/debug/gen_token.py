import time
import jwt

now = int(time.time())
payload = {
    'iss': 'devkey', 
    'sub': 'admin', 
    'exp': now+3600, 
    'video': {
        'room': '*', 
        'roomJoin': True, 
        'canPublish': True, 
        'canSubscribe': True
    }
}
token = jwt.encode(payload, 'secret12345678', algorithm='HS256')
print(token)
