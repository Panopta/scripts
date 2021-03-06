# Panopta External Contact Importer

## Prerequisites
* Python >= 2.7.9 and < 3
* `requests` from PyPi

## Usage
```
usage: ImportExternal.py [-h] [-v] [--host API_HOST] --key API_KEY [-nc] [-nv]
                         [--just-count-csv] [--dev]
                         server_csv contact_csv internal_sched_id

Import external contacts into Panopta.

positional arguments:
  server_csv         CSV file of servers to import. Named fields: Site, Site
                     Group
  contact_csv        CSV of contacts to import. Named fields: First_Name,
                     Last_Name, Mobile, Email, Site Group
  internal_sched_id  Numeric id of Notification Schedule used for internal
                     contacts.

optional arguments:
  -h, --help         show this help message and exit
  -v                 Produce verbose output.
  --host API_HOST    Host address of Panopta API (defaults to
                     https://api2.panopta.com)
  --key API_KEY      (REQUIRED) Panopta API key to use for making requests.
  -nc                Do not use concurrent processing (much slower).
  -nv                Do not verify SSL certificates.
  --just-count-csv   Just count the records in the CSV files and exit.
  --dev              Pad imported data with junk.
```

## CSV Formatting
The script expects two csv files: one for sites to import, one for contacts.
Any delimiter may be used within each file. The script relies on Python's csv library dialect-sniffing ability to detect it automatically.
Each file is expected to have the first line label the fields *exactly* as described in Usage. (If exporting from Excel, the first row can be a title row.)
Field ordering and extra fields are unimportant. Only fields that match the exact naming scheme above will be considered.

Examples:
### Sites.csv
```
Site,Site Group
http://example1.com,1001-MyGroup
http://anotherexample.com,1002-http://AnotherGroup
```

### Contacts.csv
```
First_Name,Last_Name,Mobile,Email,Site Group
John,Doe,(512) 555-1234,anemail@adomain.com,1001-MyGroup
Doe,Deer,(512) 555-4321,anotheremail@anotherdomain.com,1001-MyGroup
```
