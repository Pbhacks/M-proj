from flask import Flask, request, jsonify, render_template_string
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import cv2
import numpy as np
import os

# === Initialize Flask app ===
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///rbc_results.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# === Ensure folders ===
os.makedirs('stored_patterns', exist_ok=True)

# === Database model ===
class RBCData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(150))
    raw_count = db.Column(db.Integer)
    rbc_per_uL = db.Column(db.Integer)
    interpretation = db.Column(db.String(100))
    timestamp = db.Column(db.String(100))

with app.app_context():
    db.create_all()

# === Constants ===
DILUTION_FACTOR = 200
CHAMBER_VOLUME_uL = 0.1
CONVERSION_FACTOR = DILUTION_FACTOR / CHAMBER_VOLUME_uL

LOW_THRESHOLD = 4_000_000
HIGH_THRESHOLD = 6_000_000

# === RBC Counting Function ===
def count_rbc_with_grid(image_path):
    image = cv2.imread(image_path)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blur, 50, 150, apertureSize=3)

    lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=100, minLineLength=50, maxLineGap=5)
    grid_mask = np.zeros_like(gray)

    if lines is not None:
        for line in lines:
            x1, y1, x2, y2 = line[0]
            cv2.line(grid_mask, (x1, y1), (x2, y2), 255, 2)

    contours, _ = cv2.findContours(grid_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    largest_contour = max(contours, key=cv2.contourArea)
    x, y, w, h = cv2.boundingRect(largest_contour)

    roi = gray[y:y+h, x:x+w]

    blurred_roi = cv2.medianBlur(roi, 5)
    _, thresh = cv2.threshold(blurred_roi, 127, 255, cv2.THRESH_BINARY_INV)

    contours_rbc, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    min_area = 50
    filtered_contours = [cnt for cnt in contours_rbc if cv2.contourArea(cnt) > min_area]

    raw_rbc_count = len(filtered_contours)
    rbc_per_uL = raw_rbc_count * int(CONVERSION_FACTOR)

    if rbc_per_uL < LOW_THRESHOLD:
        interpretation = "LOW RBC COUNT (Anemia)"
    elif rbc_per_uL > HIGH_THRESHOLD:
        interpretation = "HIGH RBC COUNT (Polycythemia)"
    else:
        interpretation = "NORMAL RBC COUNT"

    output_img = image.copy()
    cv2.rectangle(output_img, (x, y), (x + w, y + h), (255, 0, 0), 3)
    for cnt in filtered_contours:
        cnt_shifted = cnt + [x, y]
        cv2.drawContours(output_img, [cnt_shifted], -1, (0, 255, 0), 2)

    return raw_rbc_count, rbc_per_uL, interpretation, output_img

# === Routes ===

@app.route('/')
def home():
    html = '''
    <h1>🔬 Biomedical RBC Counter API</h1>
    <p>The API is running!</p>
    <p><b>POST</b> an image to <code>/analyze</code> with field name <code>image</code> to get RBC count.</p>
    <p>Example CURL:</p>
    <pre>curl -X POST -F "image=@your_image.jpg" http://localhost:5000/analyze</pre>
    '''
    return render_template_string(html)

@app.route('/analyze', methods=['POST'])
def analyze_image():
    if 'image' not in request.files:
        return jsonify({'error': 'No image uploaded. Please upload an image file with field name "image".'}), 400

    file = request.files['image']
    filename = file.filename
    filepath = os.path.join('stored_patterns', filename)
    file.save(filepath)

    try:
        raw_count, rbc_per_uL, interpretation, processed_img = count_rbc_with_grid(filepath)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        result_img_path = f'stored_patterns/result_{timestamp}.png'
        cv2.imwrite(result_img_path, processed_img)

        new_record = RBCData(filename=result_img_path, raw_count=raw_count, rbc_per_uL=rbc_per_uL,
                             interpretation=interpretation, timestamp=timestamp)
        db.session.add(new_record)
        db.session.commit()

        return jsonify({
            'raw_count_in_ROI': raw_count,
            'estimated_rbc_per_uL': rbc_per_uL,
            'interpretation': interpretation,
            'result_image_saved_at': result_img_path
        })

    except Exception as e:
        return jsonify({'error': f'Processing failed: {e}'}), 500

# === Run app ===
if __name__ == '__main__':
    app.run(debug=True)
