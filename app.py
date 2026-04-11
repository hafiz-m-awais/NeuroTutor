import logging
from datetime import datetime
from flask import Flask, request, jsonify, render_template, Response, stream_with_context
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from config import Config
from modules.ai import build_prompt, stream_response
from modules.validators import validate_request

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
            headers={
                'Cache-Control': 'no-cache',
                'X-Accel-Buffering': 'no'
            }
        )

    except Exception as e:
        log.error(f"Error: {e}", exc_info=True)
        return jsonify({'error': 'Something went wrong. Please try again.'}), 500

@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'timestamp': datetime.now().isoformat()})

if __name__ == '__main__':
    log.info(f"Starting {Config.APP_NAME}")
    app.run(debug=False, port=7860, host='0.0.0.0')