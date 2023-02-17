from cli import configure, cli, pnp
import time
import re
import httplib


config_file = 'ztp-config'



def configure_replace(file, file_system='flash:/'):
    config_command = 'configure replace %s%s force ignorecase' % (file_system, file)
    config_repl = cli(config_command)
    if 'Done' in config_repl:
        print('****** config replaced ******')
    print(config_repl)
    time.sleep(30)

def file_transfer():
    conn = httplib.HTTPConnection("192.168.0.126:5000")
    conn.request("GET", "/ztp-files/ztp-config")
    response = conn.getresponse()
    data = response.read()
    with open("/flash/ztp-config", "wb") as f:
        f.write(data)
    conn.close()

def get_serial():
    try:
        show_version = cli('show version')
    except pnp._pnp.PnPSocketError:
        time.sleep(90)
        show_version = cli('show version')
    try:
        serial = re.search(r"System Serial Number\s+:\s+(\S+)", show_version).group(1)
    except AttributeError:
        serial = re.search(r"Processor board ID\s+(\S+)", show_version).group(1)
    return serial

def send_serial(serial):
    conn = httplib.HTTPConnection("192.168.0.126:5000")
    payload = serial
    headers = { 'Content-Type': 'text/plain' }
    conn.request("POST", "/onboard-router", payload, headers)
    res = conn.getresponse()
    print(res.status, res.reason)
    conn.close()
    

def main():
    print '###### STARTING ZTP SCRIPT ######'
    print '###### STARTING ZTP SCRIPT ######'
    print '\n*** Obtaining serial number of device.. ***'
    print '\n*** Obtaining serial number of device.. ***'
    serial = get_serial()
    
    print '\n*** Sending POST to API endpoint with serial.. ***'
    print '\n*** Sending POST to API endpoint with serial.. ***'
    send_serial(serial)
    time.sleep(5)
    
    print '*** Xferring Configuration!!! ***'
    print '*** Xferring Configuration!!! ***'
    file_transfer()
    print '*** Deploying Configuration ***'
    print '*** Deploying Configuration ***'
    configure_replace(config_file)
    

if __name__ in "__main__":
    main()
