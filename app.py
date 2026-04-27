import json
import logging
from datetime import datetime
from cachetools import TTLCache
from flask import Flask, request, jsonify, render_template, Response, stream_with_context, session
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from config import Config
from modules.validators import validate_request
from werkzeug.utils import secure_filename
from modules.models import db, User
from modules.ai import build_prompt, stream_response, stream_debug, generate_quiz, generate_roadmap, generate_compare, initialize_keys
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('NeuroTutor.log'),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = Config.SECRET_KEY
app.config['SQLALCHEMY_DATABASE_URI'] = Config.SQLALCHEMY_DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = Config.SQLALCHEMY_TRACK_MODIFICATIONS
app.config.update(
    SESSION_COOKIE_SAMESITE="None",
    SESSION_COOKIE_SECURE=True,
)

# Initialize Database and LoginManager
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

with app.app_context():
    db.create_all()
initialize_keys()
log.info(f"Total API keys loaded: {len(Config.GEMINI_API_KEYS)}")

def get_real_ip():
    """Resolve IP correctly behind Hugging Face / Nginx reverse proxy."""
    forwarded = request.headers.get('X-Forwarded-For')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.remote_addr

limiter = Limiter(
    get_real_ip,
    app=app,
    default_limits=[Config.RATE_LIMIT_PER_DAY, Config.RATE_LIMIT_PER_HOUR],
    storage_uri="memory://"
)


@app.route('/')
@login_required
def home():
    log.info("Home accessed")
    return render_template('index.html', current_user=current_user)

# --- Authentication Routes ---

@app.route('/register', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def register():
    if request.method == 'GET':
        return render_template('register.html')
        
    data = request.json
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({'error': 'Email and password are required'}), 400
        
    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already registered'}), 400
        
    user = User(email=email)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    
    login_user(user)
    return jsonify({'success': True, 'message': 'Registration successful'})

@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("10 per minute")
def login():
    if request.method == 'GET':
        return render_template('login.html')
        
    data = request.json
    email = data.get('email')
    password = data.get('password')
    
    user = User.query.filter_by(email=email).first()
    if user and user.check_password(password):
        login_user(user)
        return jsonify({'success': True, 'message': 'Logged in successfully'})
        
    return jsonify({'error': 'Invalid email or password'}), 401

@app.route('/logout', methods=['POST', 'GET'])
def logout():
    logout_user()
    return render_template('login.html', message='Logged out successfully')


@app.before_request
def csrf_origin_check():
    if request.method == 'POST':
        origin = request.headers.get('Origin') or request.headers.get('Referer', '')
        if origin:
            # Origin present — check it's in our allowlist
            allowed = any(origin.startswith(o) for o in Config.ALLOWED_ORIGINS)
            if not allowed:
                log.warning(f"CSRF blocked — Origin: {origin}")
                return jsonify({'error': 'Forbidden'}), 403
        else:
            # No Origin/Referer — only allow if AJAX header present (blocks raw curl)
            xhr = request.headers.get('X-Requested-With', '')
            if xhr.lower() != 'xmlhttprequest':
                log.warning(f"CSRF blocked — no Origin/Referer and missing XHR header")
                return jsonify({'error': 'Forbidden'}), 403


@app.route('/ask', methods=['POST'])
@limiter.limit(Config.RATE_LIMIT_PER_MINUTE)
def ask():
    try:
        data = request.get_json()
        valid, error = validate_request(data)
        if not valid:
            return jsonify({'error': error}), 400

        question = data['question'].strip()
        history = data.get('history', [])[-Config.MAX_HISTORY:]

        log.info(f"Question: {question[:60]}...")
        prompt = build_prompt(question, history)

        return Response(
            stream_with_context(stream_response(prompt)),
            mimetype='text/event-stream',
            headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'}
        )

    except Exception as e:
        log.error(f"Error: {e}", exc_info=True)
        return jsonify({'error': 'Something went wrong. Please try again.'}), 500


@app.route('/debug', methods=['POST'])
@limiter.limit(Config.RATE_LIMIT_PER_MINUTE)
def debug():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid request'}), 400

        code = data.get('code', '').strip()

        if not code:
            return jsonify({'error': 'Please paste some code first'}), 400
        if len(code) < 10:
            return jsonify({'error': 'Code is too short'}), 400
        if len(code) > 2000:
            return jsonify({'error': 'Code too long. Max 2000 characters.'}), 400

        log.info(f"Debug: {code[:60]}...")

        return Response(
            stream_with_context(stream_debug(code)),
            mimetype='text/event-stream',
            headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'}
        )

    except Exception as e:
        log.error(f"Debug error: {e}", exc_info=True)
        return jsonify({'error': 'Something went wrong. Please try again.'}), 500


@app.route('/quiz', methods=['POST'])
@limiter.limit(Config.RATE_LIMIT_PER_MINUTE)
def quiz():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid request'}), 400

        topic = data.get('topic', '').strip()
        count = int(data.get('count', 3))
        count = max(3, min(count, 10))

        if not topic:
            return jsonify({'error': 'Please provide a topic'}), 400
        if len(topic) < 3:
            return jsonify({'error': 'Topic is too short'}), 400
        if len(topic) > 100:
            return jsonify({'error': 'Topic too long'}), 400

        log.info(f"Quiz: {topic}")

        quiz_data, error = generate_quiz(topic, count)

        if error:
            return jsonify({'error': error}), 500

        return jsonify(quiz_data)

    except Exception as e:
        log.error(f"Quiz error: {e}", exc_info=True)
        return jsonify({'error': 'Something went wrong. Please try again.'}), 500
@app.route('/roadmap', methods=['POST'])
@limiter.limit(Config.RATE_LIMIT_PER_MINUTE)
def roadmap():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid request'}), 400

        topic = data.get('topic', '').strip()
        days = int(data.get('days', 30))
        level = data.get('level', 'beginner').strip()

        if not topic:
            return jsonify({'error': 'Please provide a topic'}), 400
        if len(topic) < 3:
            return jsonify({'error': 'Topic too short'}), 400
        if len(topic) > 100:
            return jsonify({'error': 'Topic too long'}), 400

        days = max(7, min(days, 90))

        log.info(f"Roadmap: {topic} — {days} days — {level}")

        from modules.ai import generate_roadmap
        roadmap_data, error = generate_roadmap(topic, days, level)

        if error:
            return jsonify({'error': error}), 500

        return jsonify(roadmap_data)

    except Exception as e:
        log.error(f"Roadmap error: {e}", exc_info=True)
        return jsonify({'error': 'Something went wrong. Please try again.'}), 500

@app.route('/compare', methods=['POST'])
@limiter.limit(Config.RATE_LIMIT_PER_MINUTE)
def compare():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid request'}), 400

        concept_a = data.get('concept_a', '').strip()
        concept_b = data.get('concept_b', '').strip()

        if not concept_a or not concept_b:
            return jsonify({'error': 'Please provide both concepts to compare'}), 400

        log.info(f"Compare: {concept_a} vs {concept_b}")

        compare_data, error = generate_compare(concept_a, concept_b)

        if error:
            return jsonify({'error': error}), 500

        return jsonify(compare_data)

    except Exception as e:
        log.error(f"Compare error: {e}", exc_info=True)
        return jsonify({'error': 'Something went wrong. Please try again.'}), 500

@app.route('/generate-title', methods=['POST'])
@login_required
@limiter.limit("20 per minute")
def generate_chat_title():
    try:
        data = request.get_json()
        question = data.get('question', '').strip()
        answer = data.get('answer', '').strip()

        if not question or not answer:
            return jsonify({'error': 'Question and answer required'}), 400

        from modules.ai import generate_title
        title, error = generate_title(question, answer)
        
        if error:
            return jsonify({'error': error}), 500

        return jsonify({'title': title})

    except Exception as e:
        log.error(f"Generate title error: {e}")
        return jsonify({'error': 'Failed to generate title'}), 500

# TTLCache: max 500 sessions, each expires after 30 minutes of inactivity
document_store = TTLCache(maxsize=500, ttl=1800)

@app.route('/upload', methods=['POST'])
@limiter.limit("10 per minute")
def upload():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400

        file = request.files['file']
        if not file or file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        from modules.file_processor import allowed_file, extract_text, MAX_FILE_SIZE
        filename = secure_filename(file.filename)

        if not allowed_file(filename):
            return jsonify({'error': f'File type not supported. Allowed: pdf, txt, py, docx, xlsx, csv, ipynb and more'}), 400

        file.seek(0, 2)
        size = file.tell()
        file.seek(0)

        if size > MAX_FILE_SIZE:
            return jsonify({'error': 'File too large. Max 10MB.'}), 400

        content, file_type = extract_text(file, filename)

        if not content:
            return jsonify({'error': 'Could not extract text from this file.'}), 400

        import uuid
        document_id = str(uuid.uuid4())
        document_store[document_id] = {
            'filename': filename,
            'content': content,
            'type': file_type
        }

        log.info(f"File uploaded: {filename} ({file_type}, {len(content)} chars)")

        return jsonify({
            'filename': filename,
            'type': file_type,
            'size': len(content),
            'document_id': document_id
        })

    except Exception as e:
        log.error(f"Upload error: {e}", exc_info=True)
        return jsonify({'error': 'Upload failed. Please try again.'}), 500

@app.route('/ask-document', methods=['POST'])
@limiter.limit("15 per minute")
def ask_document():
    try:
        data = request.get_json()
        question = data.get('question', '').strip()
        document_ids = data.get('document_ids', [])
        history = data.get('history', [])[-Config.MAX_HISTORY * 2:]

        if not question:
            return jsonify({'error': 'Please ask a question'}), 400

        if not document_ids or not isinstance(document_ids, list):
            return jsonify({'error': 'No active document IDs provided. Please upload again.'}), 400

        docs = []
        for doc_id in document_ids:
            doc = document_store.get(doc_id)
            if doc:
                docs.append(doc)

        if not docs:
            return jsonify({'error': 'No documents found or session expired. Please upload a file first.'}), 400

        from modules.prompts import get_document_qa_prompt
        from modules.ai import stream_with_fallbacks
        
        prompt = get_document_qa_prompt(docs, question, history)

        return Response(
            stream_with_context(stream_with_fallbacks(prompt)),
            mimetype='text/event-stream',
            headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'}
        )

    except Exception as e:
        log.error(f"Document QA error: {e}", exc_info=True)
        return jsonify({'error': 'Something went wrong.'}), 500

@app.route('/summarize-document', methods=['POST'])
@limiter.limit("15 per minute")
def summarize_document():
    try:
        data = request.get_json()
        document_id = data.get('document_id')

        if not document_id:
            return jsonify({'error': 'Missing document ID'}), 400

        doc = document_store.get(document_id)
        if not doc:
            return jsonify({'error': 'Document not found or expired.'}), 400

        from modules.prompts import get_summary_prompt
        from modules.ai import stream_with_fallbacks
        prompt = get_summary_prompt(doc['filename'], doc['content'])

        return Response(
            stream_with_context(stream_with_fallbacks(prompt)),
            mimetype='text/event-stream',
            headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'}
        )
    except Exception as e:
        log.error(f"Summarize error: {e}", exc_info=True)
        return jsonify({'error': 'Something went wrong.'}), 500    
@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'timestamp': datetime.now().isoformat()})

if __name__ == '__main__':
    log.info(f"Starting {Config.APP_NAME}")
    app.run(debug=False, port=7860, host='0.0.0.0')