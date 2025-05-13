from flask import Flask, request, render_template, jsonify
from datetime import datetime
import os
import cv2
import numpy as np
import cloudinary
import cloudinary.uploader

cloudinary.config(
  cloud_name='dlwozbaha',
  api_key='756293496318513',
  api_secret='P9PEye3ou-GEO8WJCSIAYqm5Rfo'
)


app = Flask(__name__)
UPLOAD_FOLDER = 'static'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

mode = "auto"
latest_result = {"status": "WAITING", "timestamp": "", "image": ""}
last_returned_result = {"status": "", "timestamp": "", "image": ""}
bangtai_status = "START"  # Trạng thái ban đầu của băng tải

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
    return render_template('index.html', time=datetime.now().timestamp())


@app.route('/upload', methods=['POST'])
def upload_image():
    global latest_result
    now = datetime.now().strftime("%Y%m%d-%H%M%S")
    filename = f"{now}.jpg"
    filepath = os.path.join(UPLOAD_FOLDER, filename)

    # Lưu ảnh tạm vào local
    with open(filepath, 'wb') as f:
        f.write(request.data)
        f.flush()
        os.fsync(f.fileno())

    # Nếu ở chế độ tự động → nhận diện
    if mode == "auto":
        result = detect_defect(filepath)  # Kết quả: OK hoặc ERROR
        latest_result = {"status": result, "timestamp": now, "image": filename}

        # Upload lên Cloudinary với tag là OK hoặc ERROR
        try:
            upload_result = cloudinary.uploader.upload(
                filepath,
                public_id=f"product_{now}",
                tags=[result]
            )
            print(f"Uploaded to Cloudinary: {upload_result.get('secure_url')}")
        except Exception as e:
            print(f"Cloudinary upload failed: {e}")

        print(f"New image: {filename}, Status: {result}")
        return jsonify({"result": result})
    if mode =="manual":
      result = manual_result()
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

        print(f"New image: {filename}, Status: {result}")
        return jsonify({"result": result})
    return jsonify({"result": "IGNORED"})


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
        return jsonify({"Bangtai":bangtai_status})
    return jsonify({"error":"Invalid command"}), 400

@app.route('/bangtai')
def bangtai():
    return jsonify({"Bangtai":bangtai_status})

@app.route('/manual-result', methods=['POST'])
def manual_result():
    global latest_result
    result = request.json.get("result")
    latest_result["status"] = result
    return result

@app.route("/images", methods=["GET"])
def get_images():
    try:
        # Lấy tối đa 50 ảnh đã được upload gần đây nhất
        response = cloudinary.api.resources(
            type="upload",
            prefix="product_",
            max_results=50,
            direction="desc"
        )

        images = []
        for item in response.get("resources", []):
            images.append({
                "url": item["secure_url"],
                "tags": item.get("tags", []),
                "created_at": item["created_at"]
            })

        return jsonify(images)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-store'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)
