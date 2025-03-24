from flask import Flask, request, jsonify
import cv2
import numpy as np
import paho.mqtt.client as mqtt
import os

app = Flask(__name__)

# Kết nối MQTT
MQTT_BROKER = "mqtt.eclipse.org"  # Hoặc broker của bạn
MQTT_TOPIC = "iot/product/status"
mqtt_client = mqtt.Client()
mqtt_client.connect(MQTT_BROKER, 1883, 60)

# API nhận ảnh từ ESP32
@app.route('/upload', methods=['POST'])
def upload():
    if 'image' not in request.files:
        return jsonify({"error": "No image provided"}), 400

    file = request.files['image']
    img = cv2.imdecode(np.frombuffer(file.read(), np.uint8), cv2.IMREAD_COLOR)

    # Xử lý ảnh để phát hiện lỗi
    result = process_image(img)

    # Gửi kết quả qua MQTT
    mqtt_client.publish(MQTT_TOPIC, result)

    return jsonify({"status": result})

def process_image(img):
    # Giả lập kiểm tra lỗi: Nếu ảnh quá tối, coi là lỗi
    return "NG" if np.mean(img) < 100 else "OK"

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
