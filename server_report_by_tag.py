# Server report by tag script, most internals borrowed from the customerconfigurationreport.py Jason Abate wrote
#
# INSTRUCTIONS:
# command line usage goes: python server_report_by_tags.py $customerID $tag1 $tag2 $tag3
# you can substitute the $customerID for the customer id or the customer's name
# you can add as many tags as you want, it will search using 'and' logic so any servers with $tag1 AND $tag2 
# more functionality on the logic for generating reports will allow AND and OR logic soon hopefully



#!/usr/bin/python
import sys
import time
sys.path.append("/usr/lib/resultharvester")

from sqlobject import *

from models.masterdb import *
from datetime import datetime, date, timedelta
import traceback
import commands
from pprint import pprint

import turbogears
turbogears.update_config(configfile="/home/cory.pulm/scripts-secondary.cfg")

from sqlobject import IN, AND, OR

def cf(s):

  c = Customer.selectBy(email_address=s)
  if c.count() == 1: return c[0]
  elif c.count(): return c
  c = Customer.selectBy(name=s)
  if c.count() == 1: return c[0]
  elif c.count(): return c


###############



MINIMUM_TRANSIENTS = 10
TIME_RANGE = 15  # in minutes to look back

try:
  c=Customer.get(sys.argv[1])
except:
  c = Customer.selectBy(name=sys.argv[1])[0]

t = set([x.lower() for x in sys.argv[2:]])
print("Checking servers for tag(s): %s" % ([x for x in t]))

# Net Checks
############
print "Configuration Report for %s" % c.name
print
print "Network Check Configuration"
print "Server, Check Name, FQDN, Service Type, Frequency, Location"
for s in c.servers:
  matched = t & set([x.lower() for x in s.getTags()])
  if matched  == t:
    for mp in s.active_monitor_points:
      sched = mp.getPrimarySchedule()
      loc = ""
      if sched and sched.monitor_node: loc = sched.monitor_node.name
      print ", ".join([s.name, mp.name, mp.getFQDN(), mp.service_type.name, str(mp.frequency), loc])


# Agent Metrics
###############
print
print "Server Resource Configuration"
print "Server, Resource, Alert Threshold, Threshold Duration, Alert Type"
for s in c.servers:
  matched = t & set([x.lower() for x in s.getTags()])
  if matched  == t: 
    for sr in s.server_resources:
      if sr.status == 'active':
        metadata = sr.loadMetadata()
        name = sr.name
        if metadata.get("resource_option", "") and sr.status is 'active':
          name += " [%s]" % metadata['resource_option'].strip('"')
        for srt in sr.thresholds:
          print ", ".join([s.name, name, str(srt.alert_threshold), str(srt.alert_delay/60), srt.severity])
        if sr.thresholds == []:
          print ", ".join([s.name, name, "", "", ""])
