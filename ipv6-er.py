import argparse

parser = argparse.ArgumentParser()
parser.add_argument("ip", nargs="?", default=None, type=str)

def multiZero(ip):
    half = ip.split('::')
    first = half[0]
    second = half[1]
    total = (len(first.split(':')) + len(second.split(':')))
    print("%s missing octets" % str(8 - total))
    insert = ''
    for i in range((8 -total)):
        insert = insert + '0000:'
    print insert
    ip = ip.replace('::',(':' + insert))
    print ip
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

    print("Full IP - " + str(full).strip(':'))
    

if __name__ == '__main__':
    args = parser.parse_args()
    if args.ip:
        if '::' in args.ip: multiZero(args.ip)
        else: singleZero(args.ip)
    else: print("IP missing or misformatted please try again")

