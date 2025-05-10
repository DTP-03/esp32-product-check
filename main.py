from flask import Flask, request, render_template, jsonify
from datetime import datetime
import os
import cv2
import numpy as np

app = Flask(__name__)  # Sửa lỗi ở đây
UPLOAD_FOLDER = 'static/latest'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

mode = "auto"
latest_result = {"status": "WAITING", "timestamp": ""}

def detect_defect(img_path):
    """
    Hàm nhận diện sản phẩm có hình tứ giác màu đỏ
    """
    # Đọc ảnh
    img = cv2.imread(img_path)

    # Chuyển ảnh sang không gian màu HSV để dễ dàng xử lý màu sắc
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    # Xác định phạm vi màu đỏ trong không gian HSV
    lower_red = np.array([0, 120, 70])
    upper_red = np.array([10, 255, 255])
    mask1 = cv2.inRange(hsv, lower_red, upper_red)

    lower_red = np.array([170, 120, 70])
    upper_red = np.array([180, 255, 255])
    mask2 = cv2.inRange(hsv, lower_red, upper_red)

    # Kết hợp các mask
    mask = cv2.bitwise_or(mask1, mask2)

    # Áp dụng mask vào ảnh để chỉ giữ lại các vùng đỏ
    red_area = cv2.bitwise_and(img, img, mask=mask)

    # Chuyển sang ảnh xám và phát hiện các cạnh
    gray = cv2.cvtColor(red_area, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 100, 200)

    # Tìm các đường viền trong ảnh
    contours, _ = cv2.findContours(edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    # Kiểm tra các hình dạng (số lượng điểm của mỗi contour)
    for contour in contours:
        # Làm phẳng contour và tính chu vi
        epsilon = 0.04 * cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, epsilon, True)

        # Kiểm tra nếu contour có 4 cạnh (hình tứ giác)
        if len(approx) == 4:
            # Kiểm tra diện tích hình tứ giác để tránh các lỗi phát hiện nhỏ
            area = cv2.contourArea(contour)
            if area > 1000:  # Chỉ chấp nhận những hình có diện tích đủ lớn
                return "OK"

    # Nếu không tìm thấy hình tứ giác màu đỏ, trả về ERROR
    return "ERROR"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_image():
    global latest_result
    now = datetime.now().strftime("%Y%m%d-%H%M%S")
    filename = f"{now}.jpg"
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    
    # Lưu ảnh vào thư mục static/latest
    with open(filepath, 'wb') as f:
        f.write(request.data)

    # Kiểm tra chế độ và thực hiện nhận diện
    if mode == "auto":
        result = detect_defect(filepath)  # Gọi hàm nhận diện sản phẩm
    else:
        result = latest_result["status"]  # Giữ nguyên status cũ trong chế độ thủ công

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
