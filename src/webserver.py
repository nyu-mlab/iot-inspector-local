from flask import Flask, g
import threading

import flask
import utils
import time
import json
import host_blocklist
import device_identification


PORT = 46241

GLOBAL_CONTEXT = {'host_state': None}

OK_JSON = json.dumps({'status': 'OK'})

app = Flask(__name__)


SHOW_DEVICE_TEMPLATE = """
<html><head><title>Show Devices</title></head>
<body>
<h1>Debug Interface for Weijia to Take Devices Out of Inspection</h1>
Instructions for Weijia:
<ol>
    <li>When you are able to experiment with a particular device, click the "Block Inspection" link for that device (even if the device is currently not being inspected.) This will prevent others from inspecting the device.</li>
    <li>When you are done with the experiment with that particular device, click the "Allow Inspection" link for that device.</li>
</ol>
<hr />
<h3>Devices under inspection</h3>
<ul>
{inspected_text}
</ul>
<hr />
<h3>Devices not under inspection</h3>
<ul>
{not_inspected_text}
</ul>
</body>
</html>

"""


def start_thread(host_state):

    GLOBAL_CONTEXT['host_state'] = host_state

    th = threading.Thread(target=_monitor_web_server)
    th.daemon = True
    th.start()


def _monitor_web_server():

    utils.restart_upon_crash(app.run, kwargs={'port': PORT})


def get_host_state():

    if getattr(g, 'host_state', None) is None:
        g.host_state = GLOBAL_CONTEXT['host_state']

    return g.host_state


def log_http_request(request_name):

    host_state = get_host_state()
    if host_state is not None:
        utils.log('[HTTP] request:', request_name)
        with host_state.lock:
            host_state.last_ui_contact_ts = time.time()


@app.route('/weijia_control_devices', methods=['GET'])
def show_devices():

    inspected_text = ''
    not_inspected_text = ''

    black_list = get_weijia_black_list()

    for device_dict in get_device_list_helper().values():

        name = device_dict['device_name']
        vendor = device_dict['device_vendor']
        device_id = device_dict['device_id']
        if name == '' or vendor == '':
            continue

        black_list_status = ''
        if device_id in black_list:
            black_list_status = '<i>(Currently blocked by Weijia)</i>'

        item = f'<li>{vendor} {name} {black_list_status} <small>[<a href="/weijia_enable_inspection/{device_id}">Allow Inspection</a> | <a href="/weijia_disable_inspection/{device_id}">Block Inspection</a>]</small></li>\n'

        if device_dict['is_inspected']:
            inspected_text += item
        else:
            not_inspected_text += item

    return SHOW_DEVICE_TEMPLATE.format(inspected_text=inspected_text, not_inspected_text=not_inspected_text)


def get_weijia_black_list():

    try:
        with open('weijia_black_list.txt') as fp:
            return json.load(fp)
    except IOError:
        return []


def set_weijia_black_list(black_list):

    with open('weijia_black_list.txt', 'w') as fp:
        json.dump(black_list, fp)


@app.route('/weijia_enable_inspection/<device_id>', methods=['GET'])
def weijia_enable_inspection(device_id):

    black_list = get_weijia_black_list()
    if device_id in black_list:
        black_list.remove(device_id)
    set_weijia_black_list(black_list)

    enable_inspection(device_id)

    return flask.redirect('/weijia_control_devices')


@app.route('/weijia_disable_inspection/<device_id>', methods=['GET'])
def weijia_disable_inspection(device_id):

    black_list = get_weijia_black_list()
    if device_id not in black_list:
        black_list.append(device_id)
    set_weijia_black_list(black_list)

    disable_inspection(device_id)

    return flask.redirect('/weijia_control_devices')


@app.route('/get_device_list', methods=['GET'])
def get_device_list():
    """
    Returns a list of devices; constantly changes.

    """
    return json.dumps(get_device_list_helper(), indent=2)


def get_device_list_helper():

    # Maps device_id -> {device_id, device_vendor, netdisco_name}
    output_dict = {}

    host_state = get_host_state()
    if host_state is None:
        return json.dumps(output_dict)

    # Get device vendor
    with host_state.lock:
        for (ip, mac) in host_state.ip_mac_dict.items():

            # Never include the gateway
            if ip == host_state.gateway_ip:
                continue

            device_id = utils.get_device_id(mac, host_state)

            output_dict.setdefault(
                device_id,
                {
                    'device_id': device_id,
                    'device_ip': ip,
                    'device_name': device_identification.get_device_name(mac),
                    'device_vendor': device_identification.get_device_vendor(mac),
                    'netdisco_name': '',
                    'dhcp_name': '',
                    'is_inspected': device_id in host_state.device_whitelist
                }
            )

    # Fill out netdisco_name

    with host_state.lock:
        for (device_id, device_info_list) in host_state.pending_netdisco_dict.items():
            if device_id in output_dict:
                output_dict[device_id]['netdisco_name'] = device_info_list

        # Reset pending dict
        host_state.pending_netdisco_dict = {}

    # Fill out dhcp_name

    with host_state.lock:
        for (device_id, dhcp_name) in host_state.pending_dhcp_dict.items():
            if device_id in output_dict:
                output_dict[device_id]['dhcp_name'] = dhcp_name

        # Reset pending dict
        host_state.pending_dhcp_dict = {}

    return output_dict


@app.route('/get_traffic', methods=['GET'])
def get_traffic():
    """
    Returns a dictionary of destination visited for every inspected device since
    last call to this method.

    """
    # Maps device_id -> dest_ip -> ip_dict
    output_dict = {}

    host_state = get_host_state()
    if host_state is None:
        return json.dumps(output_dict)

    current_ts = time.time()

    with host_state.lock:
        # flow_key is a tuple of (device_id, device_port, remote_ip, remote_port, protocol)
        for flow_key in host_state.pending_flow_dict:
            # Dest stats
            device_id = flow_key[0]
            dest_ip = flow_key[2]
            dest_domain = get_domain_name(host_state, device_id, dest_ip)
            # Make sure device is whitelisted
            if device_id not in host_state.device_whitelist:
                continue
            # Byte counters
            flow_stats = host_state.pending_flow_dict[flow_key]
            inbound_bps = 0
            outbound_bps = 0
            delta_ts = current_ts - host_state.last_get_traffic_ts
            if delta_ts > 0:
                inbound_bps = flow_stats['inbound_byte_count'] / delta_ts
                outbound_bps = flow_stats['outbound_byte_count'] / delta_ts
            # Send to output
            device_dict = output_dict.setdefault(device_id, {})
            if dest_ip not in device_dict:
                device_dict[dest_ip] = {
                    'hostname': dest_domain,
                    'short_domain': '',                 # TODO; not implemented
                    'owner_company': '',                # TODO; not implemented
                    'ip_country_code': '',              # TODO; not implemented
                    'purpose': '',                      # TODO; not implemented
                    'is_tracking': host_blocklist.is_hostname_blocked(dest_domain),
                    'inbound_bytes_per_second': inbound_bps,
                    'outbound_bytes_per_second': outbound_bps
                }

        # Reset pending
        host_state.pending_flow_dict = {}
        host_state.last_get_traffic_ts = current_ts

    return json.dumps(output_dict, indent=2)


def get_domain_name(host_state, query_device_id, query_ip_address):

    ret_domain = ''

    for (dns_key, ip_set) in host_state.pending_dns_dict.items():
        device_id, domain = dns_key[0], dns_key[1]
        if query_ip_address in ip_set:
            ret_domain = domain
            if device_id == query_device_id:
                return domain

    return ret_domain



@app.route('/is_ready', methods=['GET'])
def is_ready():
    """Checks if IoT Inspector is ready to interface with the AR app."""

    return OK_JSON


@app.route('/shutdown', methods=['GET'])
def shutdown():

    host_state = get_host_state()
    if host_state is not None:
        with host_state.lock:
            host_state.quit = True

    return OK_JSON



@app.route('/disable_inspection/<device_id>', methods=['GET'])
def disable_inspection(device_id):

    host_state = get_host_state()
    if host_state is not None:
        with host_state.lock:
            try:
                host_state.device_whitelist.remove(device_id)
            except ValueError:
                pass

    return OK_JSON


@app.route('/disable_all_inspection', methods=['GET'])
def disable_all_inspection():

    host_state = get_host_state()
    if host_state is not None:
        with host_state.lock:
            host_state.device_whitelist = []

    return OK_JSON


@app.route('/enable_inspection/<device_id>', methods=['GET'])
def enable_inspection(device_id):

    black_list = get_weijia_black_list()
    if device_id in black_list:
        return OK_JSON

    host_state = get_host_state()
    if host_state is not None:
        with host_state.lock:
            if device_id not in host_state.device_whitelist:
                host_state.device_whitelist.append(device_id)

    return OK_JSON


@app.route('/block_device/<device_id>/<start_unix_ts>/<stop_unix_ts>', methods=['GET'])
def block_device(device_id, start_unix_ts, stop_unix_ts):

    host_state = get_host_state()
    if host_state is not None:
        with host_state.lock:
            host_state.block_device_dict[device_id] = (int(start_unix_ts), int(stop_unix_ts))

    return OK_JSON


@app.route('/unblock_device/<device_id>', methods=['GET'])
def unblock_device(device_id):

    host_state = get_host_state()
    if host_state is not None:
        with host_state.lock:
            if device_id in host_state.block_device_dict:
                del host_state.block_device_dict[device_id]

    return OK_JSON


@app.route('/list_blocked_devices', methods=['GET'])
def list_blocked_devices():

    blocked_device_list = []

    host_state = get_host_state()
    if host_state is not None:
        with host_state.lock:
            blocked_device_list = list(host_state.block_device_dict.keys())

    return json.dumps(blocked_device_list)
