# IoT Inspector Local

IoT Inspector that works without the cloud.

## Usage from an end-user's perspective

1. Run IoT Inspector Local on a participant's computer.

2. Open the AR app on an iPhone that is connected to the same network.

## Usage from the researcher's perspective

Ask participant to do the following:

1. Run IoT Inspector Local; see `src/README.md` for instructions.

2. Copy down the IP address displayed on IoT Inspector's terminal window. Let's say this IP is 10.0.0.X.

Do the following from the AR app:

1. Issue an HTTP `GET` request to `http://10.0.0.X:46241/is_ready`. Upon error, check again in a second or two.

2. Assuming no error, the response should be a JSON object: `{"status": "OK"}`.

3. Issue an HTTP `GET` request to `http://10.0.0.X:46241/get_device_list`. The response should be a JSON object in the form of:

    ```
    {
        "abc001": {
            "device_id": "abc001",
            "device_ip": "10.0.0.5",
            "device_vendor": "Google",      // name based on device's MAC address
            "device_name": "Google Home",   // name based on IoT Inspector's device identification algorithm
            "netdisco_name": "Google Home", // name inferred from a device's SSDP/mDNS
            "dhcp_name": "",                // name obtained from DHCP Requests
            "is_inspected": true            // whether we are collecting traffic
        },
        "def002": {
            "device_id": "def002",
            "device_ip": "10.0.0.6",
            "device_vendor": "",
            "device_name": "",
            "netdisco_name": "",
            "dhcp_name": "",
            "is_inspected": false
        }
    }
    ```

    Note that the JSON object above constantly changes, as IoT Inspector scans for more devices. Examples of changes include:

    * New additions of devices. In fact, when you request `http://10.0.0.X:46241/get_device_list` for the first time, you will likely get back `{}`, since IoT Inspector is still in the process of scanning for new devices.
    * Updates to device names. For example, you might get an empty string in `netdisco_name`, but a few seconds later it becomes `Smart TV`.

    Because of the changes above, it is recommended that the AR app requests `http://10.0.0.X:46241/get_device_list` as often as possible.

4. From the device list, decide which devices are of interest. For example, take a look at all the `device_name` fields and identify all the smart TVs and Google Homes. Remember their `device_id`s.

5. Let's say you're interested in the Google Home, whose `device_id` is `abc001`. Issue an HTTP `GET` request to `http://10.0.0.:46241X/enable_inspection/abc001`, which should return a JSON object: `{"status": "OK"}`. Repeat this step for each device of interest. This step basically instructs IoT Inspector to start capturing network traffic for each device of interest. Each inspected device will have the `is_inspected` field set as `true` upon `/get_device_list`.

6. To see what traffic has been captured, issue an HTTP `GET` request to `http://10.0.0.X:46241/get_traffic` once every few seconds, which returns a JSON object in the form of:

    ```
    {
        'abc001':
            {
                "72.12.13.14": {
                    "hostname": "server1.googleusercontents.com",
                    "inbound_bytes_per_second": 23,
                    "outbound_bytes_per_second": 32
                },
                "35.112.131.5": {
                    "hostname": "server1.fbcdn.com",
                    "inbound_bytes_per_second": 23,
                    "outbound_bytes_per_second": 32
                },

            },
    }
    ```

    This JSON object shows all destinations visited by every inspected device since `http://10.0.0.X:46241/get_traffic` was called the last time. Note that `is_tracking` indicates that IP address is an advertising or tracking service. Any of the fields above could be empty, because IoT Inspector has no information, or the feature is not implemented yet.

    I suggest requesting `http://10.0.0.X:46241/get_traffic` roughly once every two seconds to get an updated view of the traffic.

7. When you are no longer interested in a device, say `abc001`, issue an HTTP `GET` request to `http://10.0.0.X:46241/disable_inspection/abc001`.

8. When the AR app quits, issue an HTTP `GET` request to `http://10.0.0.X:46241/shutdown` to terminate IoT Inspector.

## Summary of IoT Inspector's HTTP API

* `/is_ready`: Checks if IoT Inspector is ready to interface with the AR app.
* `/get_device_list`: Returns a list of devices and constantly changes.
* `/enable_inspection/<device_id>`: Instructs IoT Inspector to start collecting network traffic from a given `device_id`.
* `/get_traffic`: Returns network traffic from every inspected device between the last time you called this API and now.
* `/disable_inspection/<device_id>`: Instructs IoT Inspector to stop collecting network traffic from a given `device_id`.
* `/shutdown`: Stops inspecting all traffic and quits IoT Inspector Local.
* `/block_device/<device_id>/<start_unix_ts>/<stop_unix_ts>`: Sends wrong spoofed ARP packets to `device_id` (effectively blocking the device) between two UNIX timestamps (epoch). You can call this function multiple times to update the start and stop timestamps.
* `/unblock_device/<device_id>`: Unblocks that device.
* `/list_blocked_devices`: Shows a list of blocked `device_id`s.


## Contact

Questions? Email Danny Y. Huang at `dhuang@nyu.edu`.