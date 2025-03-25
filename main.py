from flask import Flask, request, jsonify
import paho.mqtt.client as mqtt
import cv2
import numpy as np
import base64
import json

app = Flask(__name__)

MQTT_BROKER = "thingsboard.cloud"
MQTT_TOPIC_SUB = "v1/devices/me/telemetry"
MQTT_TOPIC_PUB = "v1/devices/me/attributes"
DEVICE_TOKEN = "ssj4d8ew7gdudn9mokwb"

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.username_pw_set(DEVICE_TOKEN)

def on_connect(client, userdata, flags, reason_code, properties=None):
    if reason_code == 0:
        print(" Connected to MQTT Broker!")
        client.subscribe(MQTT_TOPIC_SUB)
    else:
        print(f"⚠ Connection failed with reason code {reason_code}")

def on_message(client, userdata, msg):
    print(f" Nhận dữ liệu từ MQTT: {msg.payload[:100]}...")
    try:
        data = json.loads(msg.payload.decode())
        if "image" in data:
            print(" Ảnh nhận được! Đang xử lý...")
            img_data = base64.b64decode(data["image"])
            np_arr = np.frombuffer(img_data, np.uint8)
            img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            if img is not None:
                result = detect_defect(img)
                response = {"status": result}
                client.publish(MQTT_TOPIC_PUB, json.dumps(response))
                print(" Xử lý xong, gửi kết quả:", result)
            else:
                print(" Lỗi: Hình ảnh giải mã bị NULL")
    except Exception as e:
        print(f" Lỗi khi xử lý MQTT: {e}")

def detect_defect(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 100, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    return "error" if len(contours) > 10 else "ok"

@app.route('/upload', methods=['POST'])
def upload():
    if 'image' not in request.files:
        return jsonify({"error": "No image provided"}), 400
    file = request.files['image']
    img_np = np.frombuffer(file.read(), np.uint8)
    img = cv2.imdecode(img_np, cv2.IMREAD_COLOR)
    result = detect_defect(img)
    response = {"status": result}
    client.publish(MQTT_TOPIC_PUB, json.dumps(response))
    return jsonify(response)

if __name__ == "__main__":
    client.on_connect = on_connect
    client.on_message = on_message
    print(" Đang kết nối MQTT...")
    client.connect(MQTT_BROKER, 1883, 60)
    client.loop_start()
    app.run(host="0.0.0.0", port=5000)
