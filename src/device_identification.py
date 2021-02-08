"""
Implements the device-identification algorithm

"""
MAC_TO_NAME_MAPPING = {
    '00166cc2382d': ('Samsung', 'Samsung Camera'),
    '001788727b50': ('Philips', 'Philips Light Bulb'),
    '2caa8e9a64b7': ('Wyze', 'Wyze Camera'),
    '4cefc00b91b3': ('Amazon', 'Amazon Echo'),
    '18b4308a9fb2': ('Nest', 'Nest Camera'),
    '24fd5b01b2f8': ('SmartThings', 'SmartThings Dishwasher'),
    '50c7bf09f34c': ('TP-Link', 'TP-Link Smart Plug'),
    '50f14a65371c': ('Bose', 'Bose Speaker'),
    '54e0193c7c14': ('Amazon', 'Ring Camera'),
    '702c1f39256e': ('Wisol', 'Wisol Fridge'),
    'a477332fe06e': ('Google', 'Google Home'),
    'c0972769bd52': ('Samsung', 'Samsung Stove'),
    'd828c9061c69': ('GE', 'GE Dryer'),
    'd828c9061517': ('GE', 'GE Washer'),
    '28395e4d2914': ('Samsung', 'Samsung Smart TV'),
    'f0f0a4f8e5fc': ('Amazon', 'Amazon Fire Stick TV')
}



def get_device_name(mac_address):

    mac_address = mac_address.replace(':', '').lower()

    try:
        return MAC_TO_NAME_MAPPING[mac_address][1]
    except KeyError:
        return ''



def get_device_vendor(mac_address):

    mac_address = mac_address.replace(':', '').lower()

    try:
        return MAC_TO_NAME_MAPPING[mac_address][0]
    except KeyError:
        return ''
