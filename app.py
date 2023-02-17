from flask import Flask, request, send_from_directory, make_response
import os
import threading

app = Flask(__name__)

CONFIG_DIR = "/your/path/ztp-files"


@app.route("/ztp-files/<path:path>", methods=["GET", "POST"])
def get_files(path):
    return send_from_directory(CONFIG_DIR, path, as_attachment=True)


@app.route("/onboard-router", methods=["POST"])
def generate_config():

    serial_number = request.data.decode("utf-8").strip()

    thread = threading.Thread(target=generate_config_thread, args=(serial_number,))
    thread.start()

    response = make_response("onboarding started", 200)
    return response


def generate_config_thread(serial_number):
    os.system(
        f"python3 /your/path/onboard-device-ztp.py --serial_number {serial_number}"
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)
