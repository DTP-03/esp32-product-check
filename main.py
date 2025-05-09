from flask import Flask, request, jsonify
import numpy as np
import cv2

app = Flask(__name__)

def is_red_circle(img):
    # Resize để tăng tốc độ
    img = cv2.resize(img, (320, 240))
    # Chuyển ảnh sang HSV
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    # Phạm vi màu đỏ trong HSV
    lower_red1 = np.array([0, 100, 100])
    upper_red1 = np.array([10, 255, 255])
    lower_red2 = np.array([160, 100, 100])
    upper_red2 = np.array([180, 255, 255])

    # Tạo mask cho màu đỏ
    mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
    mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
    red_mask = cv2.bitwise_or(mask1, mask2)

    # Tìm contours
    contours, _ = cv2.findContours(red_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area > 500:  # Lọc vùng nhỏ
            (x, y), radius = cv2.minEnclosingCircle(cnt)
            circle_area = 3.14 * radius * radius
            if 0.7 < area / circle_area < 1.3:
                return True
    return False

@app.route('/detect', methods=['POST'])
def detect():
    try:
        file = request.data
        np_arr = np.frombuffer(file, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        if img is None:
            return jsonify({'result': 'ERROR', 'reason': 'Invalid image'}), 400

        if is_red_circle(img):
            return jsonify({'result': 'OK'})
        else:
            return jsonify({'result': 'ERROR'})
    except Exception as e:
        return jsonify({'result': 'ERROR', 'reason': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
