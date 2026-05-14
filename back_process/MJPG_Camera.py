import cv2
from flask import Flask, Response, request, abort
from functools import wraps
import base64
import configparser
import os

app = Flask(__name__)

script_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(script_dir) 


cert_path = os.path.join(root_dir, "cert.pem")
key_path = os.path.join(root_dir, "key.pem")


config_file = os.path.join(root_dir, "credential.env")

camera = cv2.VideoCapture(0)
config = configparser.ConfigParser()
config.optionxform = str

if os.path.exists(config_file):
    config.read(config_file)
    try:
        camera_user = config.get("MJPG Camera", "User")
        camera_password = config.get("MJPG Camera", "Password")
    except (configparser.NoSectionError, configparser.NoOptionError):
        print("No credential found, i suppose that camera is disable")
        exit()
else:
    print(f"No config file!!! {config_file}")
    exit()

USERNAME = camera_user
PASSWORD = camera_password

if USERNAME == "-" or PASSWORD == "-":
    print("Camera is disabled")
    exit()

def check_auth(auth_header):
    if not auth_header:
        return False
    try:
        auth_type, creds = auth_header.split(" ", 1)
        if auth_type.lower() != "basic":
            return False
        decoded = base64.b64decode(creds).decode("utf-8")
        user, pwd = decoded.split(":", 1)
        return user == USERNAME and pwd == PASSWORD
    except:
        return False

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not check_auth(request.headers.get("Authorization")):
            return Response(
                "Authentication required",
                401,
                {"WWW-Authenticate": 'Basic realm="Login Required"'}
            )
        return f(*args, **kwargs)
    return decorated

def generate_frames():
    while True:
        success, frame = camera.read()
        if not success:
            break
        _, buffer = cv2.imencode('.jpg', frame)
        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

@app.route('/')
@require_auth
def video():
    return Response(
        generate_frames(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )

if __name__ == "__main__":
    if os.path.exists(cert_path) and os.path.exists(key_path):
        print(f"Starting camera (Porta 9123)")
        app.run(host="0.0.0.0", port=9123, ssl_context=(cert_path, key_path))
    else:
        print("ERROR: No ssl certific found")
        exit()