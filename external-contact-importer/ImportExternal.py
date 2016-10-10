#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import codecs
import copy
import csv
import datetime
import json
import re
import StringIO
import sys
import traceback

from multiprocessing import Pool
from urlparse import urljoin

import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from requests.packages.urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

# Turn off urllib3's warnings for cert validation so we can use -nv
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

NO_STRIP = False
DEV = False
DEBUG = False
CSV_ONLY = False
NUM_PROCS = 4

SITE_GROUP_RE = re.compile("^([0-9]+)\-(?:[\w\:]+\/{1,2})?([\w\.\-\/]+?)\/?#?$")

def make_unicode(s):
    if type(s) != unicode:
        s = s.decode('utf-8')
        return s
    else:
        return s

def raise_if_err(r, output=sys.stdout):
    try:
        r.raise_for_status()
    except requests.HTTPError as e:
        output = sys.stdout
        print >>output, "\n---Exception occured---"
        print >>output, "Request URL: %s" % e.request.url
        print >>output, "Request body: %s" % e.request.body
        print >>output, " "
        traceback.print_exc(file=output)
        raise

class Client(object):
    VERBS = ('delete', 'get', 'post', 'put')
    
    def __init__(self, token, host='https://api2.panopta.com', version='2'):
        self.session = requests.Session()
        retries = Retry(total=5,
                        backoff_factor=0.1,
                        status_forcelist=[ 500, 502, 503, 504 ])
        self.base_url = urljoin(host, 'v' + version)
        self.session.mount(self.base_url, HTTPAdapter(max_retries=retries))
        self.session.auth = PanoptaAuth(token)
        self.session.headers.update({'Accept': 'application/json', 'User-Agent': 'Panopta Importer'})

    def url(self, *path_parts):
        return '/'.join([self.base_url] + [part.strip('/') for part in path_parts])

    def __getattr__(self, name):
        if name in self.VERBS:
            def wrapper(*args, **kwargs):
                return getattr(self.session, name)(*args, **kwargs)
            return wrapper
        else:
            return object.__getattr_(self, name)


class PanoptaAuth(requests.auth.AuthBase):
    def __init__(self, token):
        self.token = token

    def __call__(self, request):
        request.headers.update({'Authorization': 'ApiKey %s' % self.token})
        return request 

class Contact(object):
    def __init__(self, name, cells=None, emails=None):
        self.name = name
        self.emails = emails
        self.cells = cells

        self.pano_url = None
        self.crm_account = None

    def __hash__(self):
        return 00042000

    def __eq__(self, other):
        return self.name == other.name and self.emails == other.emails and self.cells == other.cells

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, name):
        if name:
            self._name = make_unicode(name)
        else:
            self._name = None

    @property
    def emails(self):
        if DEV:
            emails = [u'Dev42-' + email if not email.startswith(u'Dev42-') else email for email in self._emails]
            return set(emails)
        return self._emails

    @emails.setter
    def emails(self, emails):
        if emails:
            if type(emails) != set:
                raise ValueError("Emails must be in a set.")
            emails = [make_unicode(email) for email in emails]
            self._emails = set(emails)
        else:
            self._emails = set()

    @property
    def cells(self):
        if DEV:
            cells = [u'424242' + cell if not cell.startswith(u'424242') else cell for cell in self._cells]
            return set(cells)
        return self._cells

    @cells.setter
    def cells(self, cells):
        if cells:
            if type(cells) != set:
                raise ValueError("Cells must be in a set.")
            cells = [make_unicode(re.sub(r'[^\d]+', '', cell)) for cell in cells]
            self._cells = set(cells)
        else:
            self._cells = set()

    @property
    def crm_account(self):
        return self._crm_account

    @crm_account.setter
    def crm_account(self, crm_account):
        if crm_account:
            self._crm_account = make_unicode(crm_account)
        else:
            self._crm_account = None

    @property
    def pano_url(self):
        return self._pano_url

    @pano_url.setter
    def pano_url(self, pano_url):
        if pano_url:
            self._pano_url = make_unicode(pano_url)
        else:
            self._pano_url = None


class AccountMap(object):
    def __init__(self, pano_client, name, crm_servers, crm_contacts, panopta_server_group, panopta_contact_group, intern_sched_id):
        self.pano_client = pano_client
        self.name = name
        self.crm_servers = crm_servers
        self.crm_contacts = crm_contacts
        self.panopta_server_group = panopta_server_group
        self.panopta_contact_group = panopta_contact_group
        self.intern_sched_id = intern_sched_id


def import_into_pano(account):
    # Counters
    counters = {'new_server_groups': 0,
                'new_contact_groups': 0,
                'new_servers': 0,
                'new_scheds': 0,
                'new_contacts': 0,
                'updated_contacts': 0,
                'deleted_contacts': 0}

    client = account.pano_client
    email_type = client.url('contact_type/61')
    sms_type = client.url('contact_type/91')

    try:
        UTF8Writer = codecs.getwriter('utf8')
        output = StringIO.StringIO()
        output = UTF8Writer(output)

        if DEBUG:
            print >>output, "Processing contact group: " + account.name

        # TODO Deal with contacts in Pano that aren't in CSV?
        # for pano_contact in account.panopta_contacts:
        #     if pano_contact.name not in crm_names:
        #         # Delete contact
        #         r = client.delete(pano_contact.pano_url)
        #         if r.status_code != 404:
        #             raise_if_err(r, output)
        #         if DEBUG:
        #             print >>output, "DELETED: " + pano_contact.name
        #         deleted_contacts += 1
        
        if not account.panopta_contact_group:
            payload = {'contact_list': [], 'name': account.name}
            r = client.post(client.url('contact_group'), headers={'content-type': 'application/json'}, json=payload)
            raise_if_err(r, output)
            group_url = r.headers['location']
            r = client.get(group_url)
            raise_if_err(r, output)
            account.panopta_contact_group = r.json()

            counters['new_contact_groups'] += 1
            if DEBUG:
                print >>output, "CREATED CONTACT GROUP: " + account.name
        
        # Create server group if needed
        notif_sched = None
        if not account.panopta_server_group:
            had_server_group = False
            payload = {'name': account.name}
            r = client.post(client.url('server_group'), headers={'content-type': 'application/json'}, json=payload)
            raise_if_err(r, output)
            server_group_url = r.headers['location']
            r = client.get(server_group_url)
            raise_if_err(r, output)
            account.panopta_server_group = r.json()
            account.panopta_server_group['servers'] = []

            counters['new_server_groups'] += 1
            if DEBUG:
                print >>output, "CREATED SERVER GROUP: " + account.name
                
            # Create new notification schedule for internal contacts
            contact_events = {600: {'name': "External Contact Event",
                                  'contacts': [account.panopta_contact_group['url']],
                                  'email_message': "",
                                  'text_message': ""}}
            payload = {'name': account.name, 'contact_events': contact_events}
            r = client.post(client.url('notification_schedule'), headers={'content-type': 'application/json'}, json=payload)
            raise_if_err(r, output)
            notif_sched = r.headers['location']
            counters['new_scheds'] += 1
            if DEBUG:
                print >>output, "NEW SCHEDULE: " + account.name
                
            # Add the already exisiting internal schedule to the main slot
            int_sched_url = client.url('notification_schedule/' + str(account.intern_sched_id))
            payload = {'name': account.name,
                       'notification_schedule': int_sched_url}
            r = client.put(server_group_url, headers={'content-type': 'application/json'}, json=payload)
            raise_if_err(r, output)
        else:
            r = client.get(client.url('notification_schedule'), params={'name': account.name})
            raise_if_err(r, output)
            j = r.json() 

            results = j['notification_schedule_list']
            if len(results) > 0:
                notif_sched = results[0]['url']
            elif DEBUG:
                print >>output, "No external schedule found for group %s so none being added." % account.name

        # Add servers
        for crm_server_name in account.crm_servers:
            panopta_server_names = [s['name'] for s in account.panopta_server_group['servers']]
            if crm_server_name not in panopta_server_names:
                payload = {'name': crm_server_name, 'fqdn': crm_server_name, 'server_group': account.panopta_server_group['url']}
                r = client.post(client.url('server'), headers={'content-type': 'application/json'}, json=payload)
                raise_if_err(r, output)
                new_url = r.headers['location']

                # If we have a configured external notification schedule, add it to auxiliary
                if notif_sched:
                    payload = {'name': crm_server_name, 'fqdn': crm_server_name, 'server_group': account.panopta_server_group['url'],
                               'auxiliary_notification': {'network_outages': [notif_sched]}}
                    r = client.put(new_url, json=payload)
                    raise_if_err(r, output)

                counters['new_servers'] += 1
                if DEBUG:
                    print >>output, "NEW SERVER: " + crm_server_name

        # Add/update contacts
        for crm_contact in account.crm_contacts:
            # Contact implements tests for equality based on identical info
            if crm_contact not in account.panopta_contact_group['contact_list']:
                panopta_names = [c.name for c in account.panopta_contact_group['contact_list']]
                if crm_contact.name in panopta_names:
                    # Update contact
                    # TODO: Timezones
                    matching_contacts = [contact for contact in account.panopta_contact_group['contact_list'] if contact.name == crm_contact.name]
                    if len(matching_contacts) > 1:
                        # TODO
                        if DEBUG:
                            print >>output, "Multiple contacts exist in Panopta with name %s. Skipping." % crm_contact.name
                        continue
                    match = matching_contacts[0]
                    # payload = {"name": match.name, "timezone": client.url('timezone/America/Chicago'), "external": True}
                    # r = client.put(match.pano_url, headers={'content-type': 'application/json'}, json=payload)
                    # raise_if_err(r, output)

                    # We need to get the existing contact infos to know their urls
                    r = client.get(match.pano_url + "/contact_info")
                    raise_if_err(r, output)
                    pano_contact_info = r.json()['contact_info_list']

                    # Remove deleted emails
                    emails_to_remove = match.emails - crm_contact.emails
                    for delete_email in emails_to_remove:
                        for ci in pano_contact_info:
                            if ci['detail'] == delete_email:
                                r = client.delete(ci['url'])
                                raise_if_err(r, output)
                    # Add new emails
                    emails_to_add = crm_contact.emails - match.emails
                    for add_email in emails_to_add:
                        payload = {'type': email_type, 'info': add_email}
                        r = client.post(match.pano_url + '/contact_info', headers={'content-type': 'application/json'}, json=payload)
                        raise_if_err(r, output)

                    # Remove deleted cell numbers
                    cells_to_remove = match.cells - crm_contact.cells
                    for delete_cell in cells_to_remove:
                        for ci in pano_contact_info:
                            just_nums = make_unicode(re.sub(r'[^\d]+', '', ci['detail']))
                            if just_nums == delete_cell:
                                r = client.delete(ci['url'])
                                raise_if_err(r, output)
                    # Add new cells
                    cells_to_add = crm_contact.cells - match.cells
                    for add_cell in cells_to_add:
                        payload = {'type': sms_type, 'info': add_cell}
                        r = client.post(match.pano_url + '/contact_info', headers={'content-type': 'application/json'}, json=payload)
                        raise_if_err(r, output)

                    counters['updated_contacts'] += 1
                    if DEBUG:
                        print >>output, "UPDATED CONTACT: " + crm_contact.name
                else:
                    # Add brand new contact
                    payload = {'name': crm_contact.name, 'timezone': client.url('timezone/America/Chicago'), 'external': 'true'}
                    r = client.post(client.url('contact'), headers={'content-type': 'application/json'}, json=payload)
                    raise_if_err(r, output)
                    new_contact_url = r.headers['location']
                    for email in crm_contact.emails:
                        payload = {'type': email_type, 'info': email}
                        r = client.post(new_contact_url + '/contact_info', headers={'content-type': 'application/json'}, json=payload)
                        raise_if_err(r, output)
                    for cell in crm_contact.cells:
                        payload = {'type': sms_type, 'info': cell}
                        r = client.post(new_contact_url + '/contact_info', headers={'content-type': 'application/json'}, json=payload)
                        raise_if_err(r, output)
                    # Add new contact to contact group
                    if account.panopta_contact_group:
                        existing_contact_urls = [c.pano_url for c in account.panopta_contact_group['contact_list']]
                        new_contact_urls = existing_contact_urls + [new_contact_url]
                        payload = {'name': account.panopta_contact_group['name'], 'contact_list': new_contact_urls}
                        r = client.put(account.panopta_contact_group['url'], headers={'content-type': 'application/json'}, json=payload)
                        raise_if_err(r, output)
                        # We need to add our new contact to the local list for future checks
                        new_contact = copy.deepcopy(crm_contact)
                        new_contact.pano_url = new_contact_url
                        new_contact.crm_contact = None
                        account.panopta_contact_group['contact_list'] += [new_contact]

                    counters['new_contacts'] += 1
                    if DEBUG:
                        print >>output, "ADDED CONTACT: " + crm_contact.name
        out = output.getvalue()
        output.close()
        return {'output': out, 'counters': counters}
    except:
        raise Exception("".join(traceback.format_exception(*sys.exc_info())))


class Importer(object):
    def __init__(self, api_host, api_key, no_verify=False):
        self.panopta_client = Client(api_key,
                                     host=api_host,
                                     version='2')
        if no_verify:
            # Override session object's verify attribute
            self.panopta_client.session.verify = False

    def get_panopta_contact_groups(self):
        if DEBUG:
            sys.stdout.write("Getting existing Panopta Contact Groups... ")
            sys.stdout.flush()
        client = self.panopta_client
        panopta_contact_groups = {}
        next_url = client.url('contact_group')
        while next_url:
            r = client.get(next_url, params={'limit':50, 'full': 'true'})
            raise_if_err(r)
            j = r.json()
            for grp in j.get('contact_group_list', []):
                panopta_contact_groups[grp['name']] = grp
                # Convert contacts into objects
                contact_objects = []
                for c in grp.get('contact_list', []):
                    new_contact = Contact(c['name'])
                    new_contact.pano_url = c['url']
                    for ci in c['contact_info']:
                        if ci['type'] == client.url('contact_type') + '/61':
                            new_contact.emails = new_contact.emails.union(set([ci['detail']]))
                        elif ci['type'] == client.url('contact_type') + '/91':
                            new_contact.cells = new_contact.cells.union(set([ci['detail']]))
                    contact_objects += [new_contact]
                # Replace JSON list with our objects
                panopta_contact_groups[grp['name']]['contact_list'] = contact_objects
            next_url = j['meta']['next']

        if DEBUG:
            sys.stdout.write("Done\n")
            sys.stdout.flush()
        return panopta_contact_groups

    def get_panopta_server_groups(self):
        if DEBUG:
            sys.stdout.write("Getting existing Panopta Server Groups... ")
            sys.stdout.flush()
        client = self.panopta_client
        panopta_server_groups = {}
        next_url = client.url('server_group')
        while next_url:
            r = client.get(next_url, params={'limit': 50, 'root_only': 'true'})
            raise_if_err(r)
            j = r.json()
            for grp in j.get('server_group_list', []):
                panopta_server_groups[grp['name']] = grp
                server_group_id = grp['url'].split('/')[-1]
                r = client.get(grp['url'] + '/server')
                raise_if_err(r)
                servers = r.json()['server_list']
                panopta_server_groups[grp['name']]['servers'] = servers
            next_url = j['meta']['next']

        if DEBUG:
            sys.stdout.write("Done\n")
            sys.stdout.flush()
        return panopta_server_groups

    def get_crm_accounts(self, csv_filename):
        if DEBUG:
            sys.stdout.write("Reading in CRM accounts from CSV... ")
            sys.stdout.flush()
        groups = 0
        contacts = 0
        emails = 0
        cells = 0
        crm_accounts = {}
        with open(csv_filename, 'rb') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                full_name = make_unicode(" ".join([row['First_Name'], row['Last_Name']]).strip())
                site_group = make_unicode(row['Site Group'])
                if not NO_STRIP:
                    match = re.match(SITE_GROUP_RE, site_group)
                    if match:
                        site_group = make_unicode(match.group(1) + "-" + match.group(2))
                    else:
                        sys.stdout.write("Unkown site group format: %s" % site_group)
                if site_group in crm_accounts:
                    existing_contacts = [c for c in crm_accounts[site_group] if c.name == full_name]
                    if len(existing_contacts) > 0:
                        updated_contact = copy.deepcopy(existing_contacts[0])
                        # Add this row's info to existing Contact
                        if row['Email']:
                            updated_contact.emails = updated_contact.emails.union([row['Email']])
                            emails += 1
                        if row['Mobile']:
                            updated_contact.cells = updated_contact.cells.union([row['Mobile']])
                            cells += 1
                        crm_accounts[site_group].remove(existing_contacts[0])
                        crm_accounts[site_group].append(updated_contact)
                    else:
                        new_contact = Contact(full_name)
                        new_contact.crm_account = site_group
                        if row['Email']:
                            new_contact.emails = new_contact.emails.union([row['Email']])
                            emails += 1
                        if row['Mobile']:
                            new_contact.cells = new_contact.cells.union([row['Mobile']])
                            cells += 1

                        crm_accounts[site_group] += [new_contact]
                        contacts += 1
                else:
                    new_contact = Contact(full_name)
                    new_contact.crm_account = site_group
                    if row['Email']:
                        new_contact.emails = new_contact.emails.union([row['Email']])
                        emails += 1
                    if row['Mobile']:
                        new_contact.cells = new_contact.cells.union([row['Mobile']])
                        cells += 1

                    crm_accounts[site_group] = [new_contact]
                    contacts += 1
                    groups += 1

        if DEBUG:
            sys.stdout.write("Done\n")
            sys.stdout.flush()
        if CSV_ONLY:
            print "\n{0:<30} {1:>6}".format("Contact Groups in CSV:", groups)
            print "{0:<30} {1:>6}".format("Contacts in CSV:", contacts)
            print "   {0:<27} {1:>6}".format("Emails:", emails)
            print "   {0:<27} {1:>6}".format("Cell #s:", cells) + "\n"
        return crm_accounts

    def get_crm_server_groups(self, server_csv):
        if DEBUG:
            sys.stdout.write("Reading in servers from CSV... ")
            sys.stdout.flush()
        groups = 0
        servers = 0
        crm_server_groups = {}
        with open(server_csv, 'rb') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                new_server = make_unicode(row['Site'])
                new_server_group = make_unicode(row['Site Group'])

                if new_server_group in crm_server_groups:
                    crm_server_groups[new_server_group] += [new_server]
                    servers += 1
                else:
                    crm_server_groups[new_server_group] = [new_server]
                    groups += 1
                    servers += 1

        if DEBUG:
            sys.stdout.write("Done\n")
            sys.stdout.flush()
        if CSV_ONLY:
            print "\n{0:<30} {1:>6}".format("Server Groups in CSV:", groups)
            print "{0:<30} {1:>6}".format("Servers in CSV:", servers) + "\n"
        return crm_server_groups

    def import_all(self, server_csv, contact_csv, intern_sched_id, concurrent=False):
        start_time = datetime.datetime.now()
        print "Starting sync at {}...".format(datetime.datetime.now())
        client = self.panopta_client

        crm_server_groups = self.get_crm_server_groups(server_csv)
        crm_accounts = self.get_crm_accounts(contact_csv)
        if CSV_ONLY:
            return

        pano_server_groups = self.get_panopta_server_groups()
        pano_contact_groups = self.get_panopta_contact_groups()

        # TODO: Can we somehow safely remove contact groups that exist in Panopta but not CRM?

        counters = {'new_server_groups': 0,
                    'new_contact_groups': 0,
                    'new_servers': 0,
                    'new_scheds': 0,
                    'new_contacts': 0,
                    'updated_contacts': 0,
                    'deleted_contacts': 0}
        account_maps = []
        for server_group, servers in crm_server_groups.items():
            have_server_group = server_group in pano_server_groups
            have_contact_group = server_group in pano_contact_groups
            if have_server_group:
                panopta_server_group = pano_server_groups[server_group]
            else:
                panopta_server_group = {}
            if have_contact_group:
                panopta_contact_group = pano_contact_groups[server_group]
            else:
                panopta_contact_group = {}

            if server_group in crm_accounts:
                crm_contacts = crm_accounts[server_group]
            else:
                crm_contacts = []

            intern_sched_id = int(intern_sched_id)
            new_acc_map = AccountMap(client, server_group, servers, crm_contacts, panopta_server_group, panopta_contact_group, intern_sched_id)
            account_maps += [new_acc_map]

        if concurrent:
            pool = Pool(NUM_PROCS)
            it = pool.imap_unordered(import_into_pano, account_maps)
            for result in it:
                for key,val in result['counters'].items():
                    counters[key] += val
                if DEBUG:
                    sys.stdout.write(result['output'])
            pool.close()
            pool.join()
        else:
            for account_map in account_maps:
                result = import_into_pano(account_map)
                for key,val in result['counters'].items():
                    counters[key] += val
                if DEBUG:
                    sys.stdout.write(result['output'])

        end_time = datetime.datetime.now()
        print
        print "Sync finished at " + str(end_time)
        print "Total time took: " + str(end_time-start_time)
        print "------- Summary -------"
        print "{0:<30} {1:>6}".format("New server groups:", counters['new_server_groups'])
        print "{0:<30} {1:>6}".format("New servers:", counters['new_servers'])
        print "{0:<30} {1:>6}".format("New notif scheds:", counters['new_scheds'])
        print
        print "{0:<30} {1:>6}".format("New contact groups:", counters['new_contact_groups'])
        print "{0:<30} {1:>6}".format("Added contacts:", counters['new_contacts'])
        print "{0:<30} {1:>6}".format("Updated contacts:", counters['updated_contacts'])
        print "{0:<30} {1:>6}".format("Deleted contacts:", counters['deleted_contacts'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Import external contacts into Panopta.")
    parser.add_argument('-v', dest='verbose', action='store_true', help="Produce verbose output.")
    parser.add_argument('server_csv', help='CSV file of servers to import. Named fields: Site, Site Group')
    parser.add_argument('contact_csv', help='CSV of contacts to import. Named fields: First_Name, Last_Name, Mobile, Email, Site Group')
    parser.add_argument('internal_sched_id', help='Numeric id of Notification Schedule used for internal contacts.')
    parser.add_argument('--host', dest='api_host', required=False, help="Host address of Panopta API (defaults to https://api2.panopta.com)")
    parser.add_argument('--key', dest='api_key', required=True, help="(REQUIRED) Panopta API key to use for making requests.")
    parser.add_argument('-nc', dest='concurrent', action='store_false', help="Do not use concurrent processing (much slower).")
    parser.add_argument('-nv', dest='no_verify', action='store_true', help="Do not verify SSL certificates.")
    parser.add_argument('--just-count-csv', dest='csv_only', action='store_true', help="Just count the records in the CSV files and exit.")
    parser.add_argument('--no-strip', dest='no_strip', action='store_true', help="Don't strip protocol from incoming Site Groups.")
    parser.add_argument('--dev', dest='dev', action='store_true', help="Pad imported data with junk.")
    args = parser.parse_args()
    if args.verbose: DEBUG = True
    if args.csv_only: CSV_ONLY = True
    if args.no_strip: NO_STRIP = True
    if args.dev: DEV = True
    if args.api_host:
        api_host = args.api_host
    else:
        api_host = "https://api2.panopta.com"
        
    if args.concurrent:
        Importer(api_host, args.api_key, no_verify=args.no_verify).import_all(args.server_csv, args.contact_csv, args.internal_sched_id, concurrent=True)
    else:
        Importer(api_host, args.api_key, no_verify=args.no_verify).import_all(args.server_csv, args.internal_sched_id, args.contact_csv)
