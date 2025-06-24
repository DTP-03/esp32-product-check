from flask import Flask, request, render_template, jsonify
from datetime import datetime
import pytz
import os
import cv2
import numpy as np
import cloudinary
import cloudinary.uploader
from flask_cors import CORS

# Cấu hình Cloudinary từ biến môi trường (bảo mật hơn)
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME", "dlwozbaha"),
    api_key=os.getenv("CLOUDINARY_API_KEY", "756293496318513"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET", "P9PEye3ou-GEO8WJCSIAYqm5Rfo")
)

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = 'static'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

mode = "auto"  # auto or manual
latest_result = {"status": "WAITING", "timestamp": "", "image": ""}
last_returned_result = {"status": "", "timestamp": "", "image": ""}
bangtai_status = "START"

# Múi giờ Việt Nam
VN_TZ = pytz.timezone("Asia/Ho_Chi_Minh")

def detect_defect(img_path):
    img = cv2.imread(img_path)
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    lower_yellow = np.array([15, 100, 100])
    upper_yellow = np.array([35, 255, 255])

    mask = cv2.inRange(hsv, lower_yellow, upper_yellow)

    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

    red_area = cv2.bitwise_and(img, img, mask=mask)
    gray = cv2.cvtColor(red_area, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 50, 150)

    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    for contour in contours:
        area = cv2.contourArea(contour)
        if area > 800:
            approx = cv2.approxPolyDP(contour, 0.03 * cv2.arcLength(contour, True), True)
            if len(approx) >= 8:
                return "OK"

    return "ERROR"

@app.route('/')
def index():
    return render_template('index.html', time=datetime.now(VN_TZ).timestamp())

@app.route('/upload', methods=['POST'])
def upload_image():
    global latest_result, total_count, OK_count

    now = datetime.now(VN_TZ).strftime("%Y%m%d-%H%M%S")
    filename = f"{now}.jpg"
    filepath = os.path.join(UPLOAD_FOLDER, filename)

    with open(filepath, 'wb') as f:
        f.write(request.data)
        f.flush()
        os.fsync(f.fileno())

    if mode == "auto":
        result = detect_defect(filepath)
    else:
        result = latest_result.get("status", "OK")
        
      # cộng số lượng các sản phẩm  
    total_count +=1;
    if result == "OK":
        OK_count +=1;
    
    latest_result = {"status": result, "timestamp": now, "image": filename}

    try:
        upload_result = cloudinary.uploader.upload(
            filepath,
            public_id=f"product_{now}",
            tags=[result]
        )
        print(f"Uploaded to Cloudinary: {upload_result.get('secure_url')}")
    except Exception as e:
        print(f"Cloudinary upload failed: {e}")

    return jsonify({"result": result})



@app.route('/manual-result', methods=['POST'])
def manual_result():
    global latest_result
    result = request.json.get("result")
    if result in ["OK", "ERROR"]:
        latest_result["status"] = result
        return jsonify({"status": result})
    return jsonify({"error": "Invalid result"}), 400

@app.route('/status')
def get_status():
    global last_returned_result
    if latest_result["status"] != "WAITING":
        last_returned_result = latest_result
    return jsonify(last_returned_result)

@app.route('/set-bangtai', methods=['POST'])
def set_bangtai():
    global bangtai_status
    data = request.get_json()
    if data and data.get("Bangtai") in ["START", "STOP"]:
        bangtai_status = data["Bangtai"]
        return jsonify({"Bangtai": bangtai_status})
    return jsonify({"error": "Invalid command"}), 400

@app.route('/bangtai')
def bangtai():
    return jsonify({"Bangtai": bangtai_status})

@app.route("/images", methods=["GET"])
def get_images():
    try:
        response = cloudinary.api.resources(
            type="upload",
            prefix="product_",
            max_results=50,
        )
        images = [{
            "url": item["secure_url"],
            "tags": item.get("tags", []),
            "created_at": item["created_at"]
        } for item in response.get("resources", [])]
        return jsonify(images)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-store'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.route('/counts')
def get_counts():
    return jsonify({
        "total": total_count,
        "ok": OK_count,
    })


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)
