from flask import Flask, request, jsonify
import paho.mqtt.client as mqtt
import cv2
import numpy as np
import base64
import json
import os

app = Flask(__name__)

# ✅ Dùng HiveMQ làm MQTT Broker (Thay nếu bạn có MQTT broker riêng)
MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
MQTT_TOPIC_SUB = "iot/product/result"
MQTT_TOPIC_PUB = "iot/product/image"

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

def on_connect(client, userdata, flags, reason_code, properties=None):
    if reason_code == 0:
        print("✅ Kết nối MQTT thành công!")
        client.subscribe(MQTT_TOPIC_SUB)
    else:
        print(f"⚠ Kết nối thất bại, mã lỗi: {reason_code}")

def on_message(client, userdata, msg):
    print(f"📩 Nhận dữ liệu từ MQTT: {msg.payload[:100]}...")
    try:
        data = json.loads(msg.payload.decode())
        if "image" in data:
            print("🖼 Ảnh nhận được, đang xử lý...")
            img_data = base64.b64decode(data["image"])
            np_arr = np.frombuffer(img_data, np.uint8)
            img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            if img is not None:
                result = detect_defect(img)
                response = {"status": result}
                client.publish(MQTT_TOPIC_PUB, json.dumps(response))
                print("✅ Xử lý xong, kết quả:", result)
            else:
                print("❌ Lỗi: Ảnh không hợp lệ")
    except Exception as e:
        print(f"❌ Lỗi khi xử lý MQTT: {e}")

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
    print("🚀 Kết nối MQTT...")
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_start()
    port = int(os.environ.get("PORT", 5000))  # Lấy cổng từ Railway
    app.run(host="0.0.0.0", port=port)
