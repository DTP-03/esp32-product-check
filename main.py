from flask import Flask, request, render_template, jsonify
from datetime import datetime
import os
import cv2
import numpy as np

app = Flask(__name__)
UPLOAD_FOLDER = 'static/latest.jpg'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

mode = "auto"
latest_result = {"status": "WAITING", "timestamp": ""}

def detect_defect(img_path):
    # Hàm nhận diện đơn giản (thay thế bằng OpenCV tùy bạn)
    img = cv2.imread(img_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    mean_val = np.mean(gray)
    return "ERROR" if mean_val < 100 else "OK"
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_image():
    global latest_result
    now = datetime.now().strftime("%Y%m%d-%H%M%S")
    filename = f"{now}.jpg"
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    with open(filepath, 'wb') as f:
        f.write(request.data)

    if mode == "auto":
        result = detect_defect(filepath)
    else:
        result = latest_result["status"]  # Giữ nguyên status cũ trong manual

    latest_result = {"status": result, "timestamp": now, "image": filename}
    return jsonify(latest_result)

@app.route('/status')
def get_status():
    return jsonify(latest_result)

@app.route('/set-mode', methods=['POST'])
def set_mode():
    global mode
    mode = request.json.get("mode")
    return jsonify({"mode": mode})

@app.route('/manual-result', methods=['POST'])
def manual_result():
    global latest_result
    result = request.json.get("result")
    latest_result["status"] = result
    return jsonify({"status": result})

if __name__ == '__main__':
    app.run(debug=True)
