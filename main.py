from flask import Flask, request, render_template, jsonify
from datetime import datetime
import os
import cv2
import numpy as np
import firebase_admin
from firebase_admin import credentials, firestore

# Initialize Flask
app = Flask(__name__)
UPLOAD_FOLDER = 'static'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Initialize Firebase
cred = credentials.Certificate("firebase_key.json")  # file JSON key
firebase_admin.initialize_app(cred)
db = firestore.client()

mode = "auto"
latest_result = {"status": "WAITING", "timestamp": "", "image": ""}

def detect_defect(img_path):
    img = cv2.imread(img_path)
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    lower_red1 = np.array([0, 120, 70])
    upper_red1 = np.array([10, 255, 255])
    mask1 = cv2.inRange(hsv, lower_red1, upper_red1)

    lower_red2 = np.array([170, 120, 70])
    upper_red2 = np.array([180, 255, 255])
    mask2 = cv2.inRange(hsv, lower_red2, upper_red2)

    mask = cv2.bitwise_or(mask1, mask2)
    red_area = cv2.bitwise_and(img, img, mask=mask)
    gray = cv2.cvtColor(red_area, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 100, 200)

    contours, _ = cv2.findContours(edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    for contour in contours:
        epsilon = 0.04 * cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, epsilon, True)
        if len(approx) == 4 and cv2.contourArea(contour) > 1000:
            return "OK"
    return "ERROR"

@app.route('/')
def index():
    return render_template('index.html', mode=mode)

@app.route('/upload', methods=['POST'])
def upload_image():
    global latest_result

    now = datetime.now().strftime("%Y%m%d-%H%M%S")
    filename = "latest.jpg"
    filepath = os.path.join(UPLOAD_FOLDER, filename)

    with open(filepath, 'wb') as f:
        f.write(request.data)

    latest_result = {
        "status": "WAITING",
        "timestamp": now,
        "image": filename,
    }

    if mode == "auto":
        result = detect_defect(filepath)
        latest_result["status"] = result

        # Lưu kết quả lên Firebase
        db.collection("results").add({
            "timestamp": now,
            "status": result,
            "image": filename,
            "mode": "auto"
        })

        return jsonify({"result": result})

    

@app.route('/set-mode', methods=['POST'])
def set_mode():
    global mode
    mode = request.json.get("mode", "auto")
    return jsonify({"mode": mode})

@app.route('/manual-result', methods=['POST'])
def manual_result():
    global latest_result

    if latest_result["status"] != "WAITING":
        return jsonify({"error": "Ảnh đã được xử lý."}), 400

    result = request.json.get("result")
    now = datetime.now().strftime("%Y%m%d-%H%M%S")

    latest_result["status"] = result
    latest_result["timestamp"] = now

    # Lưu vào Firebase
    db.collection("results").add({
        "timestamp": now,
        "status": result,
        "image": latest_result["image"],
        "mode": "manual"
    })

    return jsonify({"result": result})

@app.route('/status', methods=['GET'])
def get_status():
    return jsonify(latest_result)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)
