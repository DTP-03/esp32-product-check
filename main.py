from flask import Flask, request, render_template, jsonify, Response
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import pytz
import os
import cv2
import numpy as np

app = Flask(__name__)

# --- Cấu hình DB PostgreSQL qua biến môi trường ---
db_url = os.getenv("DATABASE_URL", "")
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)
app.config["SQLALCHEMY_DATABASE_URI"] = db_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# --- Model sản phẩm ---
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(256))
    content = db.Column(db.LargeBinary)
    status = db.Column(db.String(10))
    created_at = db.Column(db.DateTime)

# --- Trạng thái hiện tại và múi giờ VN ---
mode = "auto"
latest_result = {"status": "WAITING", "timestamp": "", "image_id": None}
VN_TZ = pytz.timezone("Asia/Ho_Chi_Minh")
UPLOAD_FOLDER = 'static'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# --- Hàm phát hiện lỗi ---
def detect_defect(img_path):
    img = cv2.imread(img_path)
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    lower1, upper1 = np.array([0,100,50]), np.array([10,255,255])
    lower2, upper2 = np.array([160,100,50]), np.array([180,255,255])
    mask = cv2.bitwise_or(cv2.inRange(hsv, lower1, upper1),
                          cv2.inRange(hsv, lower2, upper2))
    kernel = np.ones((5,5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    gray = cv2.cvtColor(cv2.bitwise_and(img, img, mask=mask), cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(cv2.GaussianBlur(gray,(5,5),0), 50, 150)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for c in contours:
        if cv2.contourArea(c)>800 and len(cv2.approxPolyDP(c, 0.03*cv2.arcLength(c, True), True))>=4:
            return "OK"
    return "ERROR"

# --- Routes ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_image():
    now = datetime.now(VN_TZ)
    timestamp = now.strftime("%Y%m%d-%H%M%S")
    filename = f"{timestamp}.jpg"
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    with open(filepath, 'wb') as f:
        f.write(request.data)
    result = detect_defect(filepath) if mode == "auto" else latest_result["status"]
    prod = Product(filename=filename,
                   content=open(filepath, 'rb').read(),
                   status=result,
                   created_at=now)
    db.session.add(prod)
    db.session.commit()
    latest_result.update({"status": result, "timestamp": timestamp, "image_id": prod.id})
    return jsonify({"result": result})

@app.route('/product/<int:id>/image')
def product_image(id):
    prod = Product.query.get_or_404(id)
    return Response(prod.content, mimetype='image/jpeg')

@app.route('/status')
def get_status():
    return jsonify(latest_result)

@app.route('/stats')
def stats():
    total = Product.query.count()
    ok = Product.query.filter_by(status="OK").count()
    err = Product.query.filter_by(status="ERROR").count()
    return jsonify({"total": total, "ok": ok, "error": err})

# --- Run ---
if __name__ == '__main__':
    db.create_all()
    app.run(debug=True)
