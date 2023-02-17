# cisco-ztp-flask-netbox
Testing Cisco IOS-XE ZTP process with the Flask API endpoint, using Netbox as the source of truth and LibreNMS for monitoring. The process begins with the router requesting a script from the API endpoint to run inside its guest shell. The script then sends an HTTP post message containing the router's serial number to another API endpoint, triggering a script that uses the serial number to locate the device in Netbox and generate a configuration based on its config context details. Once the configuration is generated, the router sends a HTTP GET request to download and implement the config changes. 

The script continues by using napalm to collect interface and IP address details, which are then used to update the device in Netbox. Finally, the script adds the device to LibreNMS for monitoring after completion.

# Workflow
![alt text](https://i.imgur.com/FoTRLFy.png)

# Script Run
![alt text](https://i.imgur.com/1hikQQK.png)

# Netbox
- Onboard interface created temporarily and can be deleted after
![alt text](https://i.imgur.com/1emjJ8v.png)

# LibreNMS
![alt text](https://i.imgur.com/7ypDIL1.png)
