from flask import Flask, request, jsonify, render_template
import cv2
import numpy as np
import os
from datetime import datetime

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/')
def index():
    # Truyền giá trị 'status' (OK hoặc ERROR) vào template
    status = "OK"  # Đây là ví dụ, bạn có thể gọi hàm recognize_product ở đây hoặc từ nơi khác
    return render_template("status.html", status=status)

@app.route('/upload', methods=['POST'])
def upload():
    try:
        image_bytes = request.data
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        # Save image with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        image_path = os.path.join(UPLOAD_FOLDER, f'{timestamp}.jpg')
        cv2.imwrite(image_path, img)

        result = recognize_product(img)
        return jsonify({'status': result})
    except Exception as e:
        return jsonify({'status': 'error', 'reason': str(e)}), 500

def recognize_product(img):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    lower_red1 = np.array([0, 100, 100])
    upper_red1 = np.array([10, 255, 255])
    lower_red2 = np.array([160, 100, 100])
    upper_red2 = np.array([179, 255, 255])

    mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
    mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
    mask = mask1 | mask2

    contours, _ = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    for c in contours:
        area = cv2.contourArea(c)
        perimeter = cv2.arcLength(c, True)
        if area > 1000 and perimeter > 100:
            approx = cv2.approxPolyDP(c, 0.04 * perimeter, True)
            if len(approx) > 8:
                return "OK"
    return "ERROR"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
