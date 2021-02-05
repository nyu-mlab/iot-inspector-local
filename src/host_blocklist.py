import tldextract

blocked_domains = set()

def parse_blocklist():

    with open('hosts-blocklists.txt') as fp:
        for line in fp:
            if '::' in line:
                domain = line.split('/')[1].lower().strip()
                if domain:
                    blocked_domains.add(domain)


def is_hostname_blocked(hostname):

    reg_domain = tldextract.extract(hostname).registered_domain.lower().strip()
    if reg_domain:
        return reg_domain in blocked_domains

    return False


parse_blocklist()


if __name__ == '__main__':
    # Test
    print(is_hostname_blocked('server1.fbcdn.com'))
    print(is_hostname_blocked('server1.googleusercontents.com'))
    print(is_hostname_blocked('doubleclick.com'))