import os
import jwt
import json
import time
import datetime
import uuid
from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import paho.mqtt.publish as publish
import secrets

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Secret key for JWT token
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev_secret_key')

# Simulated database (in production, use a real database)
users = {
    "admin": {
        "username": "admin",
        "password": generate_password_hash("admin123"),
        "api_key": "test_api_key_123456",
        "role": "admin"
    }
}

# In-memory storage for SMS messages (replace with a database in production)
sms_inbox = []
sms_outbox = []
logs = []

# Available SIM cards (in production, this would come from your GSM module)
available_sim_cards = [
    {"id": "sim1", "number": "+1234567890", "status": "active"},
    {"id": "sim2", "number": "+0987654321", "status": "active"}
]

# Helper function to get next available SIM card
def get_next_available_sim():
    for sim in available_sim_cards:
        if sim["status"] == "active":
            return sim
    return None

# Helper function to require API key authentication
def require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')

        if not api_key:
            api_key = request.args.get('api_key')

        if not api_key:
            data = request.get_json()
            if data and 'api_key' in data:
                api_key = data['api_key']

        if not api_key:
            return jsonify({'message': 'API key is missing!'}), 401

        valid_user = None
        for user in users.values():
            if user.get('api_key') == api_key:
                valid_user = user
                break

        if not valid_user:
            return jsonify({'message': 'Invalid API key!'}), 401

        return f(*args, **kwargs)
    return decorated

# Helper function to require JWT token for protected routes
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith('Bearer '):
                token = auth_header[7:]

        if not token:
            return jsonify({'message': 'Token is missing!'}), 401

        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user = users.get(data['username'])
            if not current_user:
                return jsonify({'message': 'Invalid token!'}), 401
        except:
            return jsonify({'message': 'Invalid token!'}), 401

        return f(current_user, *args, **kwargs)
    return decorated

# Serve the main page
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

# Authentication endpoint
@app.route('/api/auth', methods=['POST'])
def auth():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'message': 'Username and password are required!'}), 400

    user = users.get(username)
    if not user or not check_password_hash(user['password'], password):
        return jsonify({'message': 'Invalid credentials!'}), 401

    # Generate JWT token
    token = jwt.encode({
        'username': username,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    }, app.config['SECRET_KEY'], algorithm="HS256")

    # Log authentication
    log_entry = {
        'id': str(uuid.uuid4()),
        'timestamp': time.time(),
        'action': 'authentication',
        'username': username,
        'status': 'success'
    }
    logs.append(log_entry)

    return jsonify({
        'token': token,
        'api_key': user['api_key'],
        'username': user['username'],
        'role': user.get('role', 'user')
    })

# SIM Card Management Endpoints
@app.route('/api/sim-cards', methods=['GET'])
@require_api_key
def get_sim_cards():
    return jsonify({
        'sim_cards': available_sim_cards,
        'count': len(available_sim_cards)
    })

@app.route('/api/sim-cards', methods=['POST'])
@require_api_key
def add_sim_card():
    data = request.get_json()
    
    # Validate input
    if not data or not data.get('number') or not data['number'].strip():
        return jsonify({'message': 'SIM card number is required and cannot be empty!'}), 400
    
    # Process phone number format
    number = data['number'].strip().replace(' ', '')
    if not number.startswith('+'):
        number = '+' + number
    
    # Check if number contains actual digits after +
    if len(number) <= 1 or not number[1:].isdigit():
        return jsonify({'message': 'SIM card number must contain digits after + sign!'}), 400
    
    # Generate unique ID
    sim_id = f"sim{len(available_sim_cards) + 1}"
    
    # Create new SIM card
    new_sim = {
        'id': sim_id,
        'number': number,
        'status': data.get('status', 'active')
    }
    
    # Add to list
    available_sim_cards.append(new_sim)
    
    # Log the action
    log_entry = {
        'id': str(uuid.uuid4()),
        'timestamp': time.time(),
        'action': 'add_sim_card',
        'sim_id': sim_id,
        'number': number,
        'status': 'success'
    }
    logs.append(log_entry)
    
    return jsonify({
        'message': 'SIM card added successfully',
        'sim_card': new_sim
    })

@app.route('/api/sim-cards/<sim_id>', methods=['PUT'])
@require_api_key
def update_sim_card(sim_id):
    data = request.get_json()
    
    # Find the SIM card
    sim_card = None
    for sim in available_sim_cards:
        if sim['id'] == sim_id:
            sim_card = sim
            break
    
    if not sim_card:
        return jsonify({'message': 'SIM card not found!'}), 404
    
    # Update fields
    if 'number' in data:
        if not data['number'] or not data['number'].strip():
            return jsonify({'message': 'SIM card number cannot be empty!'}), 400
        number = data['number'].strip().replace(' ', '')
        if not number.startswith('+'):
            number = '+' + number
        # Check if number contains actual digits after +
        if len(number) <= 1 or not number[1:].isdigit():
            return jsonify({'message': 'SIM card number must contain digits after + sign!'}), 400
        sim_card['number'] = number
    
    if 'status' in data:
        sim_card['status'] = data['status']
    
    # Log the action
    log_entry = {
        'id': str(uuid.uuid4()),
        'timestamp': time.time(),
        'action': 'update_sim_card',
        'sim_id': sim_id,
        'number': sim_card['number'],
        'status': 'success'
    }
    logs.append(log_entry)
    
    return jsonify({
        'message': 'SIM card updated successfully',
        'sim_card': sim_card
    })

@app.route('/api/sim-cards/<sim_id>', methods=['DELETE'])
@require_api_key
def delete_sim_card(sim_id):
    # Find the SIM card
    sim_card = None
    for sim in available_sim_cards:
        if sim['id'] == sim_id:
            sim_card = sim
            break
    
    if not sim_card:
        return jsonify({'message': 'SIM card not found!'}), 404
    
    # Remove from list
    available_sim_cards.remove(sim_card)
    
    # Log the action
    log_entry = {
        'id': str(uuid.uuid4()),
        'timestamp': time.time(),
        'action': 'delete_sim_card',
        'sim_id': sim_id,
        'number': sim_card['number'],
        'status': 'success'
    }
    logs.append(log_entry)
    
    return jsonify({
        'message': 'SIM card deleted successfully'
    })

# Send SMS endpoint
@app.route('/api/sms', methods=['POST'])
@require_api_key
def send_sms():
    data = request.get_json()

    # Validate input
    recipient = data.get('recipient')
    message = data.get('message')
    sim_card_id = data.get('sim_card_id')  # Optional: specific SIM card to use

    if not recipient or not recipient.strip():
        return jsonify({'message': 'Recipient number is required and cannot be empty!'}), 400
    if not message or not message.strip():
        return jsonify({'message': 'Message content is required and cannot be empty!'}), 400

    # Process phone number format
    recipient = recipient.strip().replace(' ', '')
    if not recipient.startswith('+'):
        recipient = '+' + recipient
    
    # Check if number contains actual digits after +
    if len(recipient) <= 1 or not recipient[1:].isdigit():
        return jsonify({'message': 'Recipient number must contain digits after + sign!'}), 400

    # Get sender SIM card
    sender_sim = None
    if sim_card_id:
        # Find the specified SIM card
        for sim in available_sim_cards:
            if sim["id"] == sim_card_id:
                sender_sim = sim
                break
        if not sender_sim:
            return jsonify({'message': 'Invalid SIM card ID!'}), 400
    else:
        # Get next available SIM card
        sender_sim = get_next_available_sim()
        if not sender_sim:
            return jsonify({'message': 'No available SIM cards!'}), 400

    # Create SMS record
    sms_id = str(uuid.uuid4())
    sms_record = {
        'id': sms_id,
        'recipient': recipient,
        'message': message.strip(),
        'timestamp': time.time(),
        'status': 'sent',
        'sender_sim': sender_sim["number"]  # Add sender SIM number to record
    }

    # Store in outbox
    sms_outbox.append(sms_record)

    # Log the action
    log_entry = {
        'id': str(uuid.uuid4()),
        'timestamp': time.time(),
        'action': 'send_sms',
        'sms_id': sms_id,
        'recipient': recipient,
        'sender_sim': sender_sim["number"],
        'status': 'sent'
    }
    logs.append(log_entry)

    # In a real system, here we would send the SMS via the GSM module
    # For this demonstration, we'll simulate successful sending

    # Notify all clients that a new SMS has been sent
    socketio.emit('sms_sent', sms_record)
    try:
        payload = json.dumps(sms_record)
        print("MQTT payload:", payload)
        publish.single(
            topic="sms/send",
            payload=payload,
            hostname="localhost"
        )
        print("MQTT message published successfully.")
    except Exception as e:
        print("MQTT publish failed:", str(e))
    return jsonify({
        'message': 'SMS sent successfully',
        'sms_id': sms_id,
        'timestamp': sms_record['timestamp'],
        'sender_sim': sender_sim["number"]
    })

# Get inbox SMS endpoint
@app.route('/api/sms/inbox', methods=['GET'])
@require_api_key
def get_inbox():
    return jsonify({
        'messages': sms_inbox,
        'count': len(sms_inbox)
    })

# Get outbox SMS endpoint
@app.route('/api/sms/outbox', methods=['GET'])
@require_api_key
def get_outbox():
    return jsonify({
        'messages': sms_outbox,
        'count': len(sms_outbox)
    })

# Get logs endpoint
@app.route('/api/logs', methods=['GET'])
@require_api_key
def get_logs():
    return jsonify({
        'logs': logs,
        'count': len(logs)
    })

# Simulate receiving an SMS
@app.route('/api/simulate/receive_sms', methods=['POST'])
def simulate_receive_sms():
    data = request.get_json()

    # Validate input
    sender = data.get('sender')
    message = data.get('message')

    if not sender or not message:
        return jsonify({'message': 'Sender and message are required!'}), 400

    # Process phone number format
    sender = sender.strip().replace(' ', '')
    if not sender.startswith('+'):
        sender = '+' + sender

    # Create SMS record
    sms_id = str(uuid.uuid4())
    sms_record = {
        'id': sms_id,
        'sender': sender,
        'message': message,
        'timestamp': time.time(),
        'status': 'received'
    }

    # Store in inbox
    sms_inbox.append(sms_record)

    # Log the action
    log_entry = {
        'id': str(uuid.uuid4()),
        'timestamp': time.time(),
        'action': 'receive_sms',
        'sms_id': sms_id,
        'sender': sender,
        'status': 'received'
    }
    logs.append(log_entry)

    # Notify all clients that a new SMS has been received
    socketio.emit('sms_received', sms_record)

    return jsonify({
        'message': 'SMS received successfully',
        'sms_id': sms_id,
        'timestamp': sms_record['timestamp']
    })

# API documentation endpoint (simple version)
@app.route('/api/docs')
def api_docs():
    return render_template('api_docs.html')

# Create templates directory if it doesn't exist
if not os.path.exists('templates'):
    os.makedirs('templates')

# Create static directory if it doesn't exist
if not os.path.exists('static'):
    os.makedirs('static')

# Create template files in the templates directory
@app.route('/setup', methods=['GET'])
def setup():
    create_template_files()
    return jsonify({'message': 'Template files created successfully'})

def create_template_files():
    # This function would create template files in a real setup
    pass

@app.route('/api/generate-api-key', methods=['POST'])
@token_required
def generate_api_key(current_user):
    # Generate a new API key
    new_api_key = secrets.token_hex(16)
    current_user['api_key'] = new_api_key
    return jsonify({'api_key': new_api_key, 'message': 'API key generated successfully'})

# Run the application
if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5001, debug=True)
