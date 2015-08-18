#!/usr/bin/python
import sys
import time

import config_loader

from sqlobject import *

from models.masterdb import *
from datetime import datetime, date, timedelta
import traceback
import commands
from pprint import pprint
import turbogears

from sqlobject import IN, AND, OR


######

def deleteServerTemplate(server_id=None, template_id=None, **kwargs):
    try:
        server = Server.get(int(server_id))
        template = Server.get(int(template_id))
    except:
        print 'Failed to find server or template. What I found was template:  %s and server: %s' % (template.name, server.name)

    if kwargs['delete_strategy'] == 'false':
        for resource in ServerResource.selectBy(server=server, server_template=template):
            resource.delete()
        for mp in MonitorPoint.selectBy(server=server, server_template=template):
            mp.delete()

    try:
        Server_ServerTemplate.selectBy(server_template=template, server=server)[0].destroySelf()
    except:
        print 'Failed to remove %s and the template association from %s' % (template.name, server.name)

if __name__ == '__main__':
    chand = ServerGroup.get(151).getAllServers()
    elseg = ServerGroup.get(139).getAllServers()
    servers = chand + elseg
    template_id = '297'
    contin = str(raw_input('Removing template with ID %s from %s server. Proceed? [Y/N]\n' % (template_id,len(servers))))
    if contin.lower() == 'y' or contin.lower() == 'yes':
        print 'Proceeding...'
        for server in servers:
            deleteServerTemplate(server.id,template_id,delete_strategy='false')
    else: 
        print 'Quitting!'
