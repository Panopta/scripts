import requests
import json
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("fqdn", nargs="?", default=None, type=str)
parser.add_argument("status", nargs="?", default=None, type=str)
parser.add_argument("--csv", nargs="?", default=None, type=str)

def change_status(fqdn, status, csv=False):
     headers = {"Authorization" : "ApiKey APIKEYHERE", "content-type":"application/json"}
     get_servers = requests.get("https://api2.panopta.com/v2/server?fqdn=" + fqdn, headers=headers, verify=False)
     reply = get_servers.json()
     data = {}
     sid = ''
     
     for i in reply["server_list"]:
         sid = str(i["url"].split("/")[-1])
         data["fqdn"] = i["fqdn"]
         data["name"] = i["name"]
         data["notification_schedule"] = i["notification_schedule"]
         data["server_group"] = i["server_group"]
         data["status"] = str(status)
     if sid:
         set_status = requests.put("https://api2.panopta.com/v2/server/" + sid, data=json.dumps(data), headers=headers, verify=False)
         if int(get_servers.status_code) <= 204:
             print("Successfully set %s to status '%s'" % (str(fqdn), str(status)))
             srvStat = "Successful"
         else:
             print("An error occurred setting %s to status '%s'" % (fqdn, status))
             print("The server returned a status code of %s with the headers of %s" % (str(set_status.status_code), str(set_status.headers)))
             srvStat = "error " + str(set_status.status_code)
     else:
         print("Error server with FQDN of %s not found!" % str(fqdn))
         srvStat = "not found"
     if csv:
         with open(str(csv),'a') as f:
             f.write("%s,%s" % (str(fqdn), srvStat))
             f.write("\n")


if __name__ == "__main__":
    args = parser.parse_args()
    if args.fqdn and (args.status == "active" or args.status == "suspended"):
        change_status(args.fqdn, args.status, args.csv)
    else:
        print("%s is not a correct status, please use either active or suspend as a server status" % (args.status))

