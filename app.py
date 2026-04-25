import json
import logging
from datetime import datetime
from cachetools import TTLCache
from flask import Flask, request, jsonify, render_template, Response, stream_with_context, session
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from config import Config
from modules.validators import validate_request
from werkzeug.utils import secure_filename
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
initialize_keys()
log.info(f"Total API keys loaded: {len(Config.GEMINI_API_KEYS)}")

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[Config.RATE_LIMIT_PER_DAY, Config.RATE_LIMIT_PER_HOUR],
    storage_uri="memory://"
)


@app.route('/')
def home():
    log.info("Home accessed")
    return render_template('index.html')


@app.before_request
def csrf_origin_check():
    if request.method == 'POST':
        origin = request.headers.get('Origin') or request.headers.get('Referer', '')
        if origin:
            allowed = any(origin.startswith(o) for o in Config.ALLOWED_ORIGINS)
            if not allowed:
                log.warning(f"CSRF blocked — Origin: {origin}")
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

        session_id = session.get('session_id')
        if not session_id:
            import uuid
            session_id = str(uuid.uuid4())
            session['session_id'] = session_id
        document_store[session_id] = {
            'filename': filename,
            'content': content,
            'type': file_type
        }

        log.info(f"File uploaded: {filename} ({file_type}, {len(content)} chars)")

        from modules.prompts import get_summary_prompt
        from modules.ai import generate_with_fallback
        prompt = get_summary_prompt(filename, content)
        summary_data, error = generate_with_fallback(prompt, max_tokens=1024, is_json=False)

        if error:
            return jsonify({'error': error}), 500

        return jsonify({
            'filename': filename,
            'type': file_type,
            'size': len(content),
            'summary': summary_data
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
        session_id = session.get('session_id', 'default')

        if not question:
            return jsonify({'error': 'Please ask a question'}), 400

        doc = document_store.get(session_id)
        if not doc:
            return jsonify({'error': 'No document found. Please upload a file first.'}), 400

        from modules.prompts import get_document_qa_prompt
        from modules.ai import stream_with_fallbacks
        prompt = get_document_qa_prompt(doc['filename'], doc['content'], question)

        return Response(
            stream_with_context(stream_with_fallbacks(prompt)),
            mimetype='text/event-stream',
            headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'}
        )

    except Exception as e:
        log.error(f"Document QA error: {e}", exc_info=True)
        return jsonify({'error': 'Something went wrong.'}), 500    
@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'timestamp': datetime.now().isoformat()})

if __name__ == '__main__':
    log.info(f"Starting {Config.APP_NAME}")
    app.run(debug=False, port=7860, host='0.0.0.0')