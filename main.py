from flask import Flask, request, jsonify
import cv2
import numpy as np

app = Flask(__name__)

@app.route('/upload', methods=['POST'])
def upload():
    image_bytes = request.data
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    result = recognize_product(img)
    return jsonify({'status': result})

def recognize_product(img):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    lower_red = np.array([0, 70, 50])
    upper_red = np.array([10, 255, 255])
    mask = cv2.inRange(hsv, lower_red, upper_red)

    contours, _ = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    for c in contours:
        approx = cv2.approxPolyDP(c, 0.04 * cv2.arcLength(c, True), True)
        area = cv2.contourArea(c)
        if len(approx) > 8 and area > 1000:
            return "OK"
    return "ERROR"

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)
