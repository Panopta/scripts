import requests
import json
import argparse
import ast

parser = argparse.ArgumentParser()
parser.add_argument("action",nargs='?', default=None)
parser.add_argument("endPoint",nargs='?', default=None)
parser.add_argument("--data",nargs='?', type=str)
parser.add_argument("--version", '-V', action='version', version='%(prog)s: v1.0')


def apiCall(method, endPoint, payload=None):
    apiKey = "APIKEYHERE"
    headers = {'Authorization' : 'ApiKey ' + apiKey, 'content-type' : 'application/json'}
    baseUrl = "APIURLHERE"
    try:
        payload = json.loads(payload)
    except TypeError:
        pass
    reply = ""
    replyH = ""
    replySC = ""
    print('Setting method: %s - Setting endpoint: %s - Sending payload: %s \n' % (method, baseUrl + endPoint, payload))
    if method == 'get':
        r = requests.get(baseUrl + endPoint, headers=headers, verify=False)
        replyH = r.headers
        reply = r.text
        replySC = r.status_code        

    elif method == 'post':
        r = requests.post(baseUrl + endPoint, headers=headers, data=json.dumps(payload), verify=False)
        replyH = r.headers
        reply = r.text
        replySC = r.status_code

    elif method == 'put':
        r = requests.put(baseUrl + endPoint, headers=headers, data=json.dumps(payload), verify=False)
        replyH = r.headers
        reply = r.text
        replySC = r.status_code

    elif method == 'delete':
        r = requests.get(baseUrl + endPoint, headers=headers, verify=False)
        replyH = r.headers
        reply = r.text
        replySC = r.status_code

    print('Server responded with status code ' + str(replySC))
    print '\n'     
    print('Server replied with the headers:\n' + str(replyH))
    print '\n' 
    print('Server replied with the text:\n' + str(reply))


if __name__ == '__main__':
    args = parser.parse_args()
    if args.data:
        apiCall(args.action.lower(), args.endPoint, args.data)
    else:
        apiCall(args.action, args.endPoint)
