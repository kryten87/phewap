from picowap.phew import access_point, connect_to_wifi, is_connected_to_wifi, dns, server
from picowap.phew.template import render_template
import json
import machine
import os
import utime
import _thread

AP_TEMPLATE_PATH = "/picowap/ap_templates"
APP_TEMPLATE_PATH = "/picowap/app_templates"
WIFI_FILE = "wifi.json"
WIFI_MAX_ATTEMPTS = 3

def machine_reset():
    utime.sleep(1)
    print("Resetting...")
    machine.reset()

def setup_mode(ap_domain, ap_name):
    print("Entering setup mode...")
    
    def ap_index(request):
        if request.headers.get("host").lower() != ap_domain.lower():
            return render_template(f"{AP_TEMPLATE_PATH}/redirect.html", domain = ap_domain.lower())

        return render_template(f"{AP_TEMPLATE_PATH}/index.html")

    def ap_configure(request):
        print("Saving wifi credentials...")

        with open(WIFI_FILE, "w") as f:
            json.dump(request.form, f)
            f.close()

        # Reboot from new thread after we have responded to the user.
        _thread.start_new_thread(machine_reset, ())
        return render_template(f"{AP_TEMPLATE_PATH}/configured.html", ssid = request.form["ssid"])
        
    def ap_catch_all(request):
        if request.headers.get("host") != ap_domain:
            return render_template(f"{AP_TEMPLATE_PATH}/redirect.html", domain = ap_domain)

        return "Not found.", 404

    server.add_route("/", handler = ap_index, methods = ["GET"])
    server.add_route("/configure", handler = ap_configure, methods = ["POST"])
    server.set_callback(ap_catch_all)

    ap = access_point(ap_name)
    ip = ap.ifconfig()[0]
    dns.run_catchall(ip)
    return server

def check(ap_domain, ap_name, max_attempts = WIFI_MAX_ATTEMPTS):
    server = None
    
    # Figure out which mode to start up in...
    try:
        print('checking for config file')
        os.stat(WIFI_FILE)

        # File was found, attempt to connect to wifi...
        with open(WIFI_FILE) as f:
            wifi_current_attempt = 1
            wifi_credentials = json.load(f)
            
            while (wifi_current_attempt < max_attempts):
                ip_address = connect_to_wifi(wifi_credentials["ssid"], wifi_credentials["password"])

                if is_connected_to_wifi():
                    print(f"Connected to wifi, IP address {ip_address}")
                    break
                else:
                    wifi_current_attempt += 1
                    
            if !is_connected_to_wifi():
                # Bad configuration, delete the credentials file, reboot
                # into setup mode to get new credentials from the user.
                print("Bad wifi connection!")
                print(wifi_credentials)
                os.remove(WIFI_FILE)
                machine_reset()

    except Exception:
        # Either no wifi configuration file found, or something went wrong, 
        # so go into setup mode.
        print('starting in setup mode')
        server = setup_mode(ap_domain, ap_name)

    # Start the web server...
    if server != None:
        server.run()
