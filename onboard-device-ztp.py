import argparse
import os
import time
from typing import Dict

import pynetbox
import requests
from dotenv import load_dotenv
from jinja2 import Environment, FileSystemLoader
from nornir import InitNornir
from nornir.core.task import Task
from nornir_napalm.plugins.tasks import napalm_get
from rich import print as rprint

### arg stuff ###
parser = argparse.ArgumentParser()
parser.add_argument("--serial_number", type=str, help="serial number")
args = parser.parse_args()

### env stuff ###
load_dotenv(dotenv_path="/your/path/.env")
netbox_ip = os.environ.get("NETBOX_IP")
api_key = os.environ.get("NETBOX_API_KEY")
librenms_url = os.environ.get("LIBRENMS_URL")
librenms_token = os.environ.get("LIBRENMS_TOKEN")
j2_template_path = os.environ.get("ROUTER_TEMPLATE_PATH")
nornir_config = os.environ.get("NORNIR_CONFIG")
ztp_dir = os.environ.get("ZTP_DIR")
snmp_secret = os.environ.get("SNMP_SECRET")

### initialize pynetbox, librenms and nornir ###
nb = pynetbox.api(netbox_ip, token=api_key)
nr = InitNornir(config_file=nornir_config)
librenms_url = librenms_url
headers = {"X-Auth-Token": f"{librenms_token}"}


def load_template(template_path: str) -> Environment:
    """
    Loads a Jinja2 template from the specified path.

    Args:
        template_path (str): The path to the template file.

    Returns:
        An Environment object representing the loaded template.
    """
    file_loader = FileSystemLoader(template_path)
    env = Environment(loader=file_loader, trim_blocks=True, lstrip_blocks=True)
    return env.get_template("dmvpn-spoke-router.j2")


def render_template(template, data):
    """
    Renders a Jinja2 template with the given data.

    Args:
        template (Template): The Jinja2 template to render.
        data (dict): The data to use for rendering the template.

    Returns:
        The rendered template as a string.
    """
    return template.render(data)


def save_config(rendered_config: str) -> None:
    """
    Saves the rendered configuration to a file in the specified directory.

    Args:
        rendered_config (str): The rendered configuration to save.

    Returns:
        None
    """
    directory = ztp_dir
    filename = "ztp-config"
    file_path = os.path.join(directory, filename)
    with open(file_path, "w") as f:
        f.write(rendered_config)
    if os.path.exists(file_path):
        rprint("[yellow]" + "*" * 100 + "[/yellow]")
        print("Config file generated")
        rprint("[yellow]" + "*" * 100 + "[/yellow]")
    else:
        rprint("[yellow]" + "*" * 100 + "[/yellow]")
        print("Error: Config file was not saved")
        rprint("[yellow]" + "*" * 100 + "[/yellow]")


def interfaces_task(task: Task) -> None:
    """
    Retrieve the list of interfaces using the Napalm plugin.

    Args:
        task (Task): A Nornir task object.

    Returns:
        None
    """
    task.run(task=napalm_get, getters=["get_interfaces"])


def interfaces_ip_task(task: Task) -> None:
    """
    Retrieve the list of IP addresses assigned to each interface using the Napalm plugin.

    Args:
        task (Task): A Nornir task object.

    Returns:
        None
    """
    task.run(task=napalm_get, getters=["get_interfaces_ip"])


def create_interfaces_netbox(results_interface: Dict[str, object]) -> None:
    """
    Creates interfaces in NetBox based on the information retrieved by the "get_interfaces" getter.

    Args:
        results_interface (Dict[str, object]): A dictionary of the results of the "get_interfaces" task.

    Returns:
        None
    """
    interface_list = []
    for key, multi_result in results_interface.items():
        device_id = nb.dcim.devices.get(name=key).id
        info = multi_result[1].result
        info_data = info["get_interfaces"]
        for interface, values in info_data.items():
            description = values["description"]
            mtu = int(values["mtu"])

            template_interface = {
                "device": device_id,
                "vdcs": [],
                "name": interface,
                "type": "1000base-t",
                "enabled": True,
                "description": description,
                "mtu": mtu,
            }

            interface_list.append(template_interface)

    nb_int_result = nb.dcim.interfaces.create(interface_list)
    print(f"Interfaces configured Below")
    rprint("[yellow]" + "*" * 100 + "[/yellow]")
    print(nb_int_result)
    rprint("[yellow]" + "*" * 100 + "[/yellow]")


def assign_ip_interface_netbox(results_ip: Dict[str, object]) -> None:
    """
    Assigns IP addresses to interfaces in NetBox based on the information retrieved by the "get_interfaces_ip" getter.

    Args:
        results_ip (object): A dictionary of the results of the "get_interfaces_ip" task.

    Returns:
        None
    """
    for key, multi_result in results_ip.items():
        info = multi_result[1].result
        info_data = info["get_interfaces_ip"]
        for interface, values in info_data.items():
            ipv4 = values.get("ipv4")
            if ipv4:
                for ip_address, ip_values in ipv4.items():
                    prefix_length = ip_values.get("prefix_length")

            nb_interface = nb.dcim.interfaces.get(name=interface, device=key)

            netbox_ip = nb.ipam.ip_addresses.create(
                address=f"{ip_address}/{prefix_length}"
            )
            netbox_ip.assigned_object = nb_interface
            netbox_ip.assigned_object_id = nb_interface.id
            netbox_ip.assigned_object_type = "dcim.interface"
            netbox_ip.save()
            print(f"{key} {interface} configured with IP {ip_address}/{prefix_length}")
    rprint("[yellow]" + "*" * 100 + "[/yellow]")


def add_device_librenms(hostname: str, ip: str) -> None:
    """
    Adds a new device to LibreNMS.

    Args:
        hostname (str): The hostname of the device.
        ip (str): The IP address of the device.

    Returns:
        None
    """
    data = {
        "hostname": f"{ip}",
        "version": "v2c",
        "community": f"{snmp_secret}",
        "force_add": True,
    }
    response = requests.post(librenms_url, headers=headers, json=data)
    response = response.json()
    return print(
        f'Device: {hostname} IP: {response["devices"][0]["hostname"]} added to LibreNMS'
    )


def main() -> None:
    """
    The main function that orchestrates the ZTP process.

    Args:
        None

    Returns:
        None
    """
    serial_number = args.serial_number

    config_context = nb.dcim.devices.get(serial=serial_number).config_context

    hostname = config_context["hostname"]

    mgmt_ip = config_context["interfaces"]["GigabitEthernet4"]["ip_address"]

    template = load_template(j2_template_path)

    config = render_template(template, config_context)

    save_config(config)

    time.sleep(30)

    target = nr.filter(name=hostname)

    results_interface = target.run(name="GETTING INTERFACE LIST", task=interfaces_task)

    results_ip = target.run(
        name="GETTING INTERFACE IP ADDRESS", task=interfaces_ip_task
    )

    create_interfaces_netbox(results_interface)

    assign_ip_interface_netbox(results_ip)

    add_device_librenms(hostname, mgmt_ip)
    
    rprint("[yellow]" + "*" * 100 + "[/yellow]")


if __name__ == "__main__":
    main()
