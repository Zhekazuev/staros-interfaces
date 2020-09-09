"""
Read interfaces from hardware
Save interfaces to interfaces.csv
"""
import paramiko
import config
import time
import csv
import re


hosts = config.gomel_ultra_hosts


user = config.user
secret = config.password
port = 22


def get_intefaces(ip):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(hostname=ip, username=user, password=secret, port=port)
    channel = client.invoke_shell()

    channel.send('sho context\n')
    time.sleep(1)
    out = str(channel.recv(9999)).split('\\n')

    contexts = []
    all_interfaces = []
    for line in out:
        if 'Active' in line:
            contexts.append(line.split()[0])

    for context in contexts:
        channel.send(f'context {context}\n')
        time.sleep(1)

        channel.send(f'sho ip interface summary\n')
        time.sleep(0.2)
        interfaces = str(channel.recv(9999)).split('\\n')
        for interface in interfaces:
            if "UP" in interface:
                name = interface.split()[0]

                if re.findall(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\/\d{1,3}", interface):
                    prefix = re.findall(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\/\d{1,3}", interface)[0]
                else:
                    prefix = ""

                channel.send(f'sho ip interface name {name}\n')
                time.sleep(1)
                full_interface = str(channel.recv(9999))

                if re.findall(r".+Intf\s+Type:\s+(\S+)\\r\\nDescription", full_interface):
                    ptype = re.findall(r".+Intf\s+Type:\s+(\S+)\\r\\nDescription", full_interface)[0]
                else:
                    ptype = ""

                if re.findall(r"Description:\s+(.+)\\r\\nVRF", full_interface):
                    description = re.findall(r"Description:\s+(.+)\\r\\nVRF", full_interface)[0]
                else:
                    description = ""

                if re.findall(r"IP\s+State:\s+(.+)\\r\\nIP Address", full_interface):
                    state = re.findall(r"IP\s+State:\s+(.+)\\r\\nIP Address", full_interface)[0]
                else:
                    state = ""

                if re.findall(r"Number\s+of\s+Secondary Addresses:\s+([1-9])\\r\\n", full_interface):
                    ipv6 = re.findall(r"IPv6 Address:\s+(.+)\\r\\n\\r\\n", full_interface)[0]
                else:
                    ipv6 = ""

                all_interfaces.append({"context": context,
                                       "name": name,
                                       "prefix": prefix,
                                       "type": ptype,
                                       "description": description,
                                       "state": state,
                                       "ipv6": ipv6})
                print({"context": context,
                       "name": name,
                       "prefix": prefix,
                       "type": ptype,
                       "description": description,
                       "state": state,
                       "ipv6": ipv6})

    client.close()
    return all_interfaces


def main():
    with open(f"interfaces.csv", "w", encoding="utf-8") as csv_file:
        csv_file.write('Region;Device;Context Name;Interface Name;Prefix;Interface Type;Description;IP State;IPv6\n')

    for region in hosts.keys():
        print(f"Interfaces getting from {region} is start")
        for host in hosts.get(region):
            print(f"\tInterfaces getting from {host.get('hostname')} is start")
            interfaces = get_intefaces(host.get('host'))

            with open(f"interfaces.csv", "a", encoding="utf-8") as csv_file:
                for interface in interfaces:
                    csv_file.write(f"{region};{host.get('hostname')};{interface.get('context')};"
                                   f"{interface.get('name')};{interface.get('prefix')};{interface.get('type')};"
                                   f"{interface.get('description')};{interface.get('state')};"
                                   f"{interface.get('ipv6')}\n")

            print(f"\tInterfaces getting from {host.get('hostname')} is end")
        print(f"Interfaces getting from {region} is end")
    print("File successfully create")


if __name__ == '__main__':
    main()
