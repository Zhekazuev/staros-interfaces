"""
Read interfaces from csv file
Pushing interfaces to netbox
"""
from config import Netbox
import requests
import csv
import json

nb_url = Netbox.nb_url
headers = Netbox.headers
vrfs = Netbox.vrfs_info


def get_context(device, context):
    """
    Get context by device and context name
    """
    get_context_url = f"{nb_url}/api/dcim/interfaces/?name={context}&device={device}"
    context = json.loads(requests.get(get_context_url, headers=headers).text).get("results")
    return context


def get_contexts(device):
    """
    Get contexts by device
    """
    get_contexts_url = f"{nb_url}/api/dcim/interfaces/?device={device}"
    contexts = json.loads(requests.get(get_contexts_url, headers=headers).text).get("results")
    return contexts


def get_device_id(device_name):
    """
    Get DeviceID in Netbox by Device Name
    """
    get_device_url = f"{nb_url}/api/dcim/devices/?name={device_name}"
    device_id = json.loads(requests.get(get_device_url, headers=headers).text).get("results")[0].get("id")
    return device_id


def get_role(row):
    """
    Defining RoleID
    """
    # Will remake to dictionary like vrfs
    if row.get('Interface Type') == 'Loopback':
        role = 10
    elif row.get("Context Name") == "local":
        role = 40
    else:
        role = None
    return role


def check_ip(address, vrf_id, interface_id):
    """
    Determining the existence of an IP
    """
    get_ip = f"{nb_url}/api/ipam/ip-addresses/?address={address}&vrf_id={vrf_id}&interface_id={interface_id}"
    result_ip = json.loads(requests.get(get_ip, headers=headers).text).get("results")
    return result_ip


def create_ipv4(row, vrf_id, role, interface_id, interface_name):
    """
    Creating IPv4 address in interface
    """
    interface_url = f"{nb_url}/api/ipam/ip-addresses/"
    prefix = row.get("Prefix")
    push_interface = {
        "address": prefix,
        "vrf": vrf_id,
        "tenant": None,
        "status": 1,
        "role": role,
        "interface": interface_id,
        "description": interface_name,
        "nat_inside": None,
        "nat_outside": None,
        "tags": ["staros", "staros_production", row.get('Device'), row.get('Region'),
                 row.get("Context Name"), row.get("Interface Type"), "script"],
        "custom_fields": {}
    }
    new_interface = requests.post(interface_url, headers=headers, json=push_interface)
    return new_interface.text


def create_ipv6(row, vrf_id, interface_id, interface_name):
    """
    Creating IPv6 address in interface
    """
    interface_url = f"{nb_url}/api/ipam/ip-addresses/"
    prefixv6 = row.get("IPv6")
    push_interfacev6 = {
        "address": prefixv6,
        "vrf": vrf_id,
        "tenant": None,
        "status": 1,
        "role": 20,
        "interface": interface_id,
        "description": interface_name,
        "nat_inside": None,
        "nat_outside": None,
        "tags": ["staros", "staros_production", row.get('Device'), row.get('Region'),
                 row.get("Context Name"), row.get("Interface Type"), "script"],
        "custom_fields": {}
    }
    new_interface = requests.post(interface_url, headers=headers, json=push_interfacev6)
    return new_interface.text


def read_file(file_name, delimiter=","):
    with open(f'files/{file_name}.csv') as csv_file:
        reader = csv.DictReader(csv_file, delimiter=delimiter, quotechar='"')
    return reader


def create_contexts(device, file_name):
    print('Creating contexts...')
    reader = read_file(file_name)

    context_url = f"{nb_url}/api/dcim/interfaces/"

    for row in reader:
        if row.get('Device') == device:
            context = row.get('Context Name')
            device_id = get_device_id(device)
            push_context = {
                "device": device_id,
                "name": context,
                "type": 0,
                "form_factor": 0,
                "enabled": True,
                "lag": None,
                "mtu": None,
                "mac_address": None,
                "mgmt_only": False,
                "description": "",
                "connection_status": None,
                "cable": None,
                "mode": None,
                "untagged_vlan": None,
                "tagged_vlans": [],
                "tags": ["staros", "staros_production", row.get('Device'), row.get('Region'),
                         row.get("Context Name"), "script"]
            }
            context = get_context(device, context)
            if context:
                continue
            else:
                new_context = requests.post(context_url, headers=headers, json=push_context)
                print(new_context.text)
    print("Contexts are created!")


def create_interfaces(device, file_name):
    reader = read_file(file_name)

    for row in reader:
        # exclude not current devices
        if row.get('Device') == device:
            # exclide WIFI, SRP, XGB, ARDTEST, Gi-2 Contexts
            if row.get('Context Name') == "WIFI" or row.get('Context Name') == "SRP" \
                    or row.get('Context Name') == "XGB" \
                    or row.get('Context Name') == "ARDTEST" or row.get('Context Name') == "Gi-2":
                continue

            role = get_role(row)
            contexts = get_contexts(row.get('Device'))

            for context in contexts:
                if row.get('Context Name') == context.get("name"):
                    interface_id = context.get("id")
                    interface_name = row.get("Interface Name")
                    ipv4 = row.get("Prefix")
                    ipv6 = row.get("IPv6")
                    if row.get('Context Name') == "SG":
                        vrf_id = vrfs.get(row['Context Name']).get(row.get('Region')).get("id")
                    else:
                        vrf_id = vrfs.get(row['Context Name']).get("id")

                    if not check_ip(ipv4, vrf_id, interface_id):
                        # creating IPv4 interface in current Context
                        print(create_ipv4(row, vrf_id, role, interface_id, interface_name))

                    # if secondary IPv6 address is in file, creating him
                    if ipv6 and (not check_ip(ipv6, vrf_id, interface_id)):
                        print(create_ipv6(row, vrf_id, interface_id, interface_name))

        print("\tInterfaces are created!")


# In this point you can add Click cli-arguments and others
def main():
    """
    Pushing contexts and interfaces to Netbox for one specified device
    context(StarOS) is interface(Netbox)
    interface(StarOS) is address(Netbox) in interface(Netbox)
    """
    file_name = "interfaces"
    device = "device name in file"
    create_contexts(device, file_name)
    create_interfaces(device, file_name)


if __name__ == '__main__':
    # main definition need for Click library
    main()
