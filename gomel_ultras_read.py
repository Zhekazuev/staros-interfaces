"""
Read interfaces from hardware
Save interfaces to interfaces.csv
Save interfaces to interfaces.xlsx
"""
from config import StarOS
import paramiko
import pyexcel
import time
import csv
import re


class SSH:
    """
    Class SSH is needed for a simple connection, execute command and put/get files
    """
    def __init__(self, host, user, password, port=22):
        self.client = None
        self.conn = None
        self.host = host
        self.user = user
        self.password = password
        self.port = port

    def connect(self):
        """
        Create ssh connection
        """
        if self.conn is None:
            try:
                self.client = paramiko.SSHClient()
                self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                self.client.connect(hostname=self.host, port=self.port, username=self.user, password=self.password)
                return self.client
            except paramiko.AuthenticationException as authException:
                print(f"{authException}, please verify your credentials")
            except paramiko.SSHException as sshException:
                print(f"Could not establish SSH connection: {sshException}")

    def execute_commands(self, cmd):
        """
        Execute command in succession.

        :param cmd: One command for example: show administrators
        :type cmd: str
        """
        stdin, stdout, stderr = self.client.exec_command(cmd)
        stdout.channel.recv_exit_status()
        response = stdout.readlines()
        return response

    def put(self, localpath, remotepath):
        sftp = self.client.open_sftp()
        sftp.put(localpath, remotepath)
        time.sleep(10)
        sftp.close()
        self.client.close()

    def get(self, remotepath, localpath):
        sftp = self.client.open_sftp()
        sftp.get(remotepath, localpath)
        time.sleep(10)
        sftp.close()
        self.client.close()

    def disconnect(self):
        """Close ssh connection."""
        if self.client:
            self.client.close()


def get_intefaces(ip, user, secret):
    ssh = SSH(host=ip, user=user, password=secret).connect()
    shell = ssh.invoke_shell()

    # read all contexts
    shell.send('sho context\n')
    time.sleep(1)
    out = shell.recv(10000).decode('utf8').split('\n')

    contexts = []
    all_interfaces = []

    # append all contexts in list
    for line in out:
        if 'Active' in line:
            contexts.append(line.split()[0])

    for context in contexts:
        # choose context in device
        shell.send(f'context {context}\n')
        time.sleep(1)

        # show all IPv4 interfaces in curent context
        shell.send(f'sho ip interface summary\n')
        time.sleep(0.5)
        interfaces = shell.recv(10000).decode('utf8').split('\n')

        for interface in interfaces:
            # choose only UP interfaces
            if "UP" in interface:
                # get interface name
                name = interface.split()[0]

                # get full info about interface with specified name
                shell.send(f'sho ip interface name {name}\n')
                time.sleep(5)
                full_interface = shell.recv(10000).decode('utf8')

                # get ipv4 prefix
                if re.findall(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\/\d{1,3}", interface):
                    prefix = re.findall(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\/\d{1,3}", interface)[0]
                else:
                    prefix = ""

                # get prefix type
                if re.findall(r"Intf\s+Type:\s+(.+)\r\nDescription", full_interface):
                    ptype = re.findall(r"Intf\s+Type:\s+(.+)\r\nDescription", full_interface)[0]
                else:
                    ptype = ""

                # get description
                if re.findall(r"Description:\s+(.+)\r\nVRF", full_interface):
                    description = re.findall(r"Description:\s+(.+)\r\nVRF", full_interface)[0].replace(",", ";")
                else:
                    description = ""

                # get interface state
                if re.findall(r"IP\s+State:\s+(.+)\r\nIP Address", full_interface):
                    state = re.findall(r"IP\s+State:\s+(.+)\r\nIP Address", full_interface)[0].replace(",", ";")
                else:
                    state = ""

                # get ipv6 prefix if exist
                if re.findall(r"Number\s+of\s+Secondary Addresses:\s+([1-9])\r\n", full_interface):
                    ipv6 = re.findall(r"IPv6 Address:\s+(.+)\r\n\r\n", full_interface)[0]
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
    ssh.close()
    return all_interfaces


def create_csv_file(output_file_name, fieldnames, delimiter=","):
    """
    Create csv file
    """
    with open(f'files/{output_file_name}.csv', 'w') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter=delimiter, quotechar='"')
        writer.writeheader()


def write_interfaces_file(interfaces, region, host, output_file_name, fieldnames, delimiter=","):
    """
    Write info in csv file
    :param interfaces: interfaces list
    :param region: region name
    :param host: host
    :param output_file_name: output file name
    :param fieldnames: fieldnames
    :param delimiter: delimiter
    :return: None
    """
    with open(f'files/{output_file_name}.csv', 'a') as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames, delimiter=delimiter, quotechar='"')
        for interface in interfaces:
            writer.writerow({"Region": region, "Device": host.get('hostname'),
                             "Context Name": interface.get('context'),
                             "Interface Name": interface.get('name'), "Prefix": interface.get('prefix'),
                             "Interface Type": interface.get('type'), "Description": interface.get('description'),
                             "IP State": interface.get('state'), "IPv6": interface.get('ipv6')})
    print("Interfaces added to file")


def create_xlsx_copy(output_file_name, delimiter=","):
    """
    Create copy csv file in xlsx format
    """
    sheet = pyexcel.get_sheet(file_name=f"files/{output_file_name}.csv", delimiter=delimiter)
    return sheet.save_as(f"files/{output_file_name}.xlsx")


def main():
    """
    Main logic
    :return: None
    """
    # hosts parameters
    hosts = StarOS.gomel_ultra_hosts
    user = StarOS.staros_user
    secret = StarOS.staros_secret

    # file parameters
    output_file_name = "gomel_ultras_interfaces"
    fieldnames = ['Region', 'Device', 'Context Name', 'Interface Name', 'Prefix', 'Interface Type',
                  'Description', 'IP State', 'IPv6']
    create_csv_file(output_file_name, fieldnames)

    # read from hosts interfaces
    for region in hosts.keys():
        print(f"Interfaces getting from {region} is start")
        for host in hosts.get(region):
            print(f"\tInterfaces getting from {host.get('hostname')} is start")

            interfaces = get_intefaces(host.get('host'), user, secret)
            write_interfaces_file(interfaces, region, host, output_file_name, fieldnames)

            print(f"\tInterfaces getting from {host.get('hostname')} is end")
        print(f"Interfaces getting from {region} is end")
    print("File successfully create")
    create_xlsx_copy(output_file_name)


if __name__ == '__main__':
    main()
