"""
Implements the device-identification algorithm

"""
MAC_TO_NAME_MAPPING = {
    '00166cc2382d': ('Samsung', 'Camera'),
    '001788727b50': ('Philips', 'Light Bulb'),
    '2caa8e9a64b7': ('Wyze', 'Camera'),
    '4cefc00b91b3': ('Amazon', 'Echo'),
    '18b4308a9fb2': ('Nest', 'Camera'),
    '24fd5b01b2f8': ('SmartThings', 'Dishwasher'),
    '50c7bf09f34c': ('TP-Link', 'Smart Plug'),
    '50f14a65371c': ('Bose', 'Speaker'),
    '54e0193c7c14': ('Amazon', 'Ring Camera'),
    '702c1f39256e': ('Wisol', 'Fridge'),
    'a477332fe06e': ('Google', 'Home Voice Assistant'),
    'c0972769bd52': ('Samsung', 'Stove'),
    'd828c9061c69': ('GE', 'Dryer'),
    'd828c9061517': ('GE', 'Washer')
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
