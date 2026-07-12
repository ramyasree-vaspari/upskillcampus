from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import sqlite3
import numpy as np
import base64
import cv2
import json
import os
from database import DB_PATH, init_db

app = Flask(__name__)
# Fixed secret key so sessions persist across server restarts
app.secret_key = 'securevote_secret_key_2024_rtp'

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

detector = None
recognizer = None

def init_models():
    global detector, recognizer
    if detector is None and os.path.exists("yunet.onnx"):
        detector = cv2.FaceDetectorYN.create("yunet.onnx", "", (320, 320), 0.9, 0.3, 5000)
    if recognizer is None and os.path.exists("sface.onnx"):
        recognizer = cv2.FaceRecognizerSF.create("sface.onnx", "")

def extract_face_encoding(image_b64):
    try:
        init_models()
        if detector is None or recognizer is None:
            missing = []
            if not os.path.exists("yunet.onnx"):
                missing.append("yunet.onnx")
            if not os.path.exists("sface.onnx"):
                missing.append("sface.onnx")
            msg = (
                f"Missing model file(s): {', '.join(missing)}. "
                "Please run 'python download_models.py' in the project folder first."
            ) if missing else "Face recognition models failed to load."
            return None, msg

        header, encoded = image_b64.split(",", 1)
        decoded = base64.b64decode(encoded)
        nparr = np.frombuffer(decoded, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        height, width, _ = img.shape
        detector.setInputSize((width, height))

        # Detect faces
        _, faces = detector.detect(img)

        if faces is None or len(faces) == 0:
            return None, "No face detected. Please ensure good lighting and look directly into the camera."

        # Select the largest face detected based on width * height
        faces = sorted(faces, key=lambda f: f[2] * f[3], reverse=True)
        face = faces[0]

        # Align face and extract features
        aligned_face = recognizer.alignCrop(img, face)
        feature = recognizer.feature(aligned_face)

        # Feature is a 1x128 numpy array
        encoding = feature[0].tolist()
        return encoding, "Success"
    except Exception as e:
        return None, str(e)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template('register.html')
        
    data = request.json
    name = data.get('name')
    voter_id = data.get('voter_id')
    image_b64 = data.get('image')
    
    if not name or not voter_id or not image_b64:
        return jsonify({"success": False, "message": "Missing required fields"}), 400
        
    encoding, msg = extract_face_encoding(image_b64)
    if not encoding:
        return jsonify({"success": False, "message": msg}), 400
        
    conn = get_db_connection()
    c = conn.cursor()
    
    # Check if face already exists using SFace cosine distance
    c.execute('SELECT face_encoding FROM users')
    existing_users = c.fetchall()
    
    new_encoding_np = np.array([encoding], dtype=np.float32)
    face_exists = False
    
    for row in existing_users:
        stored_encoding = np.array([json.loads(row['face_encoding'])], dtype=np.float32)
        
        # SFace Cosine distance threshold is usually 0.363 for verification
        score = recognizer.match(stored_encoding, new_encoding_np, cv2.FaceRecognizerSF_FR_COSINE)
        if score >= 0.363:
            face_exists = True
            break
            
    if face_exists:
        conn.close()
        return jsonify({"success": False, "message": "This face is already registered. Duplicate accounts are not allowed."}), 400
        
    try:
        c.execute('INSERT INTO users (name, voter_id, face_encoding) VALUES (?, ?, ?)', 
                  (name, voter_id, json.dumps(encoding)))
        conn.commit()
    except sqlite3.IntegrityError:
        return jsonify({"success": False, "message": "Voter ID already registered"}), 400
    finally:
        conn.close()  # Always close once, in finally block only
        
    return jsonify({"success": True, "message": "Registration successful"}), 200

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')
        
    data = request.json
    voter_id = data.get('voter_id')
    image_b64 = data.get('image')
    
    if not voter_id or not image_b64:
        return jsonify({"success": False, "message": "Missing required fields"}), 400
        
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT id, name, face_encoding, has_voted FROM users WHERE voter_id = ?', (voter_id,))
    user = c.fetchone()
    conn.close()
    
    if not user:
        return jsonify({"success": False, "message": "Voter ID not found"}), 404
        
    live_encoding, msg = extract_face_encoding(image_b64)
    if not live_encoding:
        return jsonify({"success": False, "message": msg}), 400
        
    stored_encoding = np.array([json.loads(user['face_encoding'])], dtype=np.float32)
    live_encoding_np = np.array([live_encoding], dtype=np.float32)
    
    # Compare using OpenCV SFace Cosine distance
    score = recognizer.match(stored_encoding, live_encoding_np, cv2.FaceRecognizerSF_FR_COSINE)
    match = score >= 0.363
    
    if match:
        session['user_id'] = user['id']
        session['name'] = user['name']
        session['has_voted'] = user['has_voted']
        return jsonify({"success": True, "message": "Login successful"}), 200
    else:
        return jsonify({"success": False, "message": "Face verification failed"}), 401

@app.route('/vote', methods=['GET', 'POST'])
def vote():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    c = conn.cursor()
    
    # Re-check user status to be safe against race conditions
    c.execute('SELECT has_voted FROM users WHERE id = ?', (session['user_id'],))
    user = c.fetchone()
    
    if request.method == 'GET':
        if user['has_voted']:
            conn.close()
            return render_template('success.html', message="You have already cast your vote.")
            
        c.execute('SELECT * FROM candidates')
        candidates = c.fetchall()
        conn.close()
        return render_template('vote.html', candidates=candidates)
        
    # POST
    if user['has_voted']:
        conn.close()
        return jsonify({"success": False, "message": "Duplicate vote detected"}), 403
        
    candidate_id = request.json.get('candidate_id')
    if not candidate_id:
        conn.close()
        return jsonify({"success": False, "message": "No candidate selected"}), 400
        
    try:
        c.execute('UPDATE candidates SET vote_count = vote_count + 1 WHERE id = ?', (candidate_id,))
        c.execute('UPDATE users SET has_voted = 1 WHERE id = ?', (session['user_id'],))
        conn.commit()
        session['has_voted'] = 1
        return jsonify({"success": True, "message": "Vote cast successfully"}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        conn.close()

@app.route('/admin')
def admin():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT name, party, vote_count FROM candidates ORDER BY vote_count DESC')
    results = c.fetchall()
    
    c.execute('SELECT COUNT(*) FROM users')
    total_users = c.fetchone()[0]
    
    c.execute('SELECT COUNT(*) FROM users WHERE has_voted = 1')
    total_votes = c.fetchone()[0]
    conn.close()
    
    return render_template('admin.html', results=results, total_users=total_users, total_votes=total_votes)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    # Initialize the database (creates tables & seeds candidates if needed)
    init_db()
    app.run(debug=True, port=5000)
