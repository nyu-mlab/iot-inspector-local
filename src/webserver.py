from flask import Flask, g
import threading
import utils
import server_config
import time
import json
import oui_parser


PORT = 46241

GLOBAL_CONTEXT = {'host_state': None}

OK_JSON = json.dumps({'status': 'OK'})

app = Flask(__name__)


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


@app.route('/get_device_list', methods=['GET'])
def get_device_list():
    """
    Returns a list of devices; constantly changes.

    """
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
            device_vendor = oui_parser.get_vendor(utils.get_oui(mac))

            output_dict.setdefault(
                device_id, 
                {
                    'device_id': device_id, 
                    'device_ip': ip,
                    'device_vendor': device_vendor, 
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

    return json.dumps(output_dict, indent=2)


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

    with host_state.lock:
        # flow_key is a tuple of (device_id, device_port, remote_ip, remote_port, protocol)
        for flow_key in host_state.pending_flow_dict:
            device_id = flow_key[0]
            dest_ip = flow_key[2]
            dest_domain = get_domain_name(host_state, device_id, dest_ip)
            device_dict = output_dict.setdefault(device_id, {})
            if dest_ip not in device_dict:
                device_dict[dest_ip] = {
                    'hostname': dest_domain,
                    'short_domain': '',      # TODO; not implemented
                    'owner_company': '',     # TODO; not implemented
                    'ip_country_code': '',   # TODO; not implemented
                    'purpose': '',           # TODO; not implemented
                    'is_tracking': ''        # TODO; not implemented
                }

        # Reset pending
        host_state.pending_flow_dict = {}
    
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


@app.route('/enable_inspection/<device_id>', methods=['GET'])
def enable_inspection(device_id):

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
            blocked_device_list = host_state.block_device_dict.keys()

    return json.dumps(blocked_device_list)
