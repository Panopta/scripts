import argparse

parser = argparse.ArgumentParser(usage="python %(prog)s ipaddress")
parser.add_argument("ip", nargs="?", default=None, type=str, help="Enter an abreviated IPv6 address")

def multiZero(ip):
    half = ip.split('::')
    first = half[0]
    second = half[1]
    total = (len(first.split(':')) + len(second.split(':')))
    print("%s missing octets" % str(8 - total))
    insert = ''
    for i in range((8 -total)):
        insert = insert + '0000:'
    ip = ip.replace('::',(':' + insert))
    addrType(ip)
    singleZero(ip)


def singleZero(ip):
    splitUp = ip.split(':')
    full = ''
    for item in splitUp:
        octet = ''
        if len(item) < 4:
            while (len(item) < 4): item = '0' + item
            octet = item
        else: octet = item
        full = str(full) + str(octet) + ':'

def addrType(ip):
    firstOct = ip.split(':')[0].lower()
    if firstOct == 'fe80': print("This is a LAN IP!")
    if firstOct == 'fc00': print("This is an automatically generated IP that is unroutable!")
    if firstOct == 'ff00': print("This is a multicast address!")
    if firstOct == '2000': print("This is a global unicast address!")
    if firstOct == '3ffe' or firstOct == 'fec0': print("This address is depricated!")
    if '2001:db8:' in ip.lower(): print("Unroutable documentation example IP!")
    if '2001:0:' in ip.lower(): print("This is a Teredo tunnel IP!")
    if firstOct == '2002': print("This is an IPv6 -> IPv4 conversion IP")
    if 'ffff:a.b.c.d' in ip.lower(): print("This is an IPv4 mapped to IPv6 address!")
    if '::a.b.c.d' in ip.lower(): print("This is an embedded IPv4 address!")
    print("\nFull IP - " + str(ip).strip(':'))
    

if __name__ == '__main__':
    args = parser.parse_args()
    if args.ip:
        if '::' in args.ip: multiZero(args.ip)
        else: singleZero(args.ip)
    else: 
        print(" --- IP missing or misformatted please try again ---\n")
        parser.print_help()

