from flask import Flask, request, jsonify
import cv2
import numpy as np
import base64
import os

app = Flask(__name__)

def detect_defect(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 100, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    return "error" if len(contours) > 10 else "ok"

@app.route('/process', methods=['POST'])
def process():
    data = request.get_json()
    if "image" not in data:
        return jsonify({"error": "No image provided"}), 400
    
    img_data = base64.b64decode(data["image"])
    np_arr = np.frombuffer(img_data, np.uint8)
    img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    
    result = detect_defect(img)
    return jsonify({"status": result})  # Trả về HTTP thay vì MQTT

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
