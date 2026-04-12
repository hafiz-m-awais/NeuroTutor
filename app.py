import logging
from datetime import datetime
from flask import Flask, json, request, jsonify, render_template, Response, stream_with_context
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from config import Config
from modules.validators import validate_request
import json 
from modules.ai import build_prompt, stream_response, stream_debug, generate_quiz, initialize_keys
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
    
@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'timestamp': datetime.now().isoformat()})

if __name__ == '__main__':
    log.info(f"Starting {Config.APP_NAME}")
    app.run(debug=False, port=7860, host='0.0.0.0')