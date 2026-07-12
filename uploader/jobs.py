import requests
import json

def get_queue():
    url  = "https://queue-server-wpes.onrender.com/"
    response = requests.get(url)
    data = json.loads(response.text)
    number = data["no_of_jobs"]
    if number > 0 :
        return True
    else :
        return False
get_queue()
