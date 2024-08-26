import requests

# send detection result to smart-fridge server
def send_detection_result(names):
    url = 'http://127.0.0.1:8080//sync/object_detection' #######
    headers={
        'Content-type':'application/json',
        'Accept':'application/json'
    }
    r = requests.post(url, json={'objects': names}, headers=headers)
    
    return r.status_code