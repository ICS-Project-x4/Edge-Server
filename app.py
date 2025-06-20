import os
import jwt
import json
import time
import datetime
import uuid
import psutil
import sqlite3
from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import paho.mqtt.client as mqtt
import paho.mqtt.publish as publish
import secrets
from database import db, User, SimCard, Message, Log, init_db, SmsStatus

# Import eventlet and monkey patch
import eventlet
eventlet.monkey_patch()

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app, resources={r"/*": {"origins": "*"}})

# Configure Socket.io with CORS
socketio = SocketIO(app, 
    cors_allowed_origins="*",
    async_mode='eventlet',
    ping_timeout=60,
    ping_interval=25,
    max_http_buffer_size=1e8
)

# Configure SQLite database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sms_gateway.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,
    'pool_recycle': 300,
    'pool_use_lifo': True
}
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(32))
MQTT_HOST = "localhost"
MQTT_PORT = 1883
# Initialize database
db.init_app(app)
init_db(app)

import json
import paho.mqtt.client as mqtt

# MQTT Client setup with a message callback parameter
def create_mqtt_client(topic, on_message_callback):
    mqtt_client = mqtt.Client()

    def on_connect(client, userdata, flags, rc):
        print(f"Connected to MQTT broker with result code: {rc}")
        print(f"Subscribing to topic: {topic}")
        client.subscribe(topic)
        print(f"Successfully subscribed to topic: {topic}")

    def on_message(client, userdata, msg):
        try:
            print(f"Received message on topic {msg.topic}")
            payload = msg.payload.decode()
            print(f"Message payload: {payload}")
            on_message_callback(payload)
        except Exception as e:
            print(f"Error processing MQTT message: {str(e)}")

    def on_disconnect(client, userdata, rc):
        print(f"Disconnected from MQTT broker with result code: {rc}")

    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    mqtt_client.on_disconnect = on_disconnect

    return mqtt_client


def handle_sms_status_message(payload):
    print("Received status message:", payload)
    try:
        data = json.loads(payload)
        print("Parsed status data:", data)
        
        with app.app_context():
            try:
                # Update the message status in the database
                message = Message.query.filter_by(id=data.get('message_id')).first()
                if message:
                    print(f"Found message with ID: {message.id}, updating status to: {data['status']}")
                    message.status = data['status']
                    db.session.commit()
                    print("Message status updated successfully")
                else:
                    print(f"No message found with ID: {data.get('message_id')}")
                
                # Create SMS status record
                sms_status = SmsStatus(
                    sender_number=data["sender_number"],
                    receiver_number=data["receiver_number"],
                    message=data["message"],
                    status=data["status"]
                )
                db.session.add(sms_status)
                db.session.commit()
                
                print("Saved status record:", sms_status.to_dict())
                
                # Emit socket event for status update
                socketio.emit('sms_status_update', {
                    'message_id': data.get('message_id'),
                    'status': data['status'],
                    'timestamp': datetime.datetime.now().isoformat()
                })
                
                # Also emit the full status data
                socketio.emit('mqtt_status', payload)
                
            except Exception as e:
                db.session.rollback()
                print(f"Error updating message status: {str(e)}")
                raise
    except json.JSONDecodeError as json_error:
        print(f"Invalid JSON payload: {str(json_error)}")
    except Exception as e:
        print(f"Error processing status message: {str(e)}")

# Create client and pass callback
mqtt_client = create_mqtt_client('/sms/status',handle_sms_status_message)

def handle_sms_receive_message(payload):
    try:
        # Parse the incoming payload
        data = json.loads(payload)
        
        # Validate required fields
        required_fields = ['sender_number', 'receiver_number', 'message']
        if not all(field in data for field in required_fields):
            print(f"Missing required fields in payload: {payload}")
            return

        sender_number = data['sender_number']
        receiver_number = data['receiver_number']
        message_text = data['message']

        with app.app_context():
            try:
                # Find the SimCard by sender number
                sim_card = SimCard.query.filter_by(number=sender_number).first()
                
                if not sim_card:
                    print(f"No SIM card found for sender number: {sender_number}")
                    # Create a new SIM card entry if not found
                    sim_card = SimCard(
                        number=sender_number,
                        status='active'
                    )
                    db.session.add(sim_card)
                    db.session.flush()  # Get the ID without committing

                # Create the Message object
                message = Message(
                    sender=sender_number,
                    recipient=receiver_number,
                    message=message_text,
                    direction='incoming',
                    sender_sim=sim_card.id,
                    status='received'
                )
                db.session.add(message)
                db.session.flush()  # Get the message ID

                # Create a single log entry
                log = Log(
                    action='receive_sms',
                    details=json.dumps({
                        'recipient': receiver_number,
                        'message_id': message.id,
                        'sim_card': sim_card.number,
                        'sender': sender_number,
                        'message': message_text[:100]  # Store first 100 chars
                    }),
                    status='SUCCESS',
                    sender_sim=sim_card.id
                )
                db.session.add(log)
                
                # Commit all changes in a single transaction
                db.session.commit()

                # Emit socket event with the complete message data
                socketio.emit('sms_status_update', {
                    'message_id': message.id,
                    'recipient': receiver_number,
                    'sender': sender_number,
                    'message': message_text,
                    'status': 'received',
                    'timestamp': message.timestamp.isoformat(),
                    'sim_card': sim_card.number
                })

                # Publish status update for the received message
                status_payload = {
                    'message_id': message.id,
                    'sender_number': sender_number,
                    'receiver_number': receiver_number,
                    'message': message_text,
                    'status': 'SUCCESS'
                }

                publish.single("sms/status", json.dumps(status_payload), hostname="localhost", port=1883)

                print(f"Successfully saved incoming message from {sender_number} to {receiver_number}")
                print(f"Message ID: {message.id}, SIM Card: {sim_card.number}")

            except Exception as db_error:
                db.session.rollback()
                print(f"Database error while saving message: {str(db_error)}")
                raise

    except json.JSONDecodeError as json_error:
        print(f"Invalid JSON payload: {str(json_error)}")
    except Exception as e:
        print(f"Error processing received message: {str(e)}")


# Create and connect client, subscribing to /sms/receive with the callback
mqtt_client_receive_msg = create_mqtt_client('/sms/receive', handle_sms_receive_message)

try:
    print("Attempting to connect to MQTT broker...")
    mqtt_client_receive_msg.connect("localhost", 1883, 60)
    mqtt_client_receive_msg.loop_start()
    print("MQTT client started successfully")
except Exception as e:
    print(f"Failed to connect to MQTT broker: {str(e)}")

try:
    print("Attempting to connect to MQTT broker...")
    mqtt_client.connect("localhost", 1883, 60)
    mqtt_client.loop_start()
    print("MQTT client started successfully")
except Exception as e:
    print(f"Failed to connect to MQTT broker: {str(e)}")


def get_next_available_sim():
    # Find the active SIM card with the least number of outgoing messages
    sim = (
        db.session.query(SimCard)
        .filter_by(status='active')
        .outerjoin(Message, (SimCard.id == Message.sender_sim) & (Message.direction == 'outgoing'))
        .group_by(SimCard.id)
        .order_by(func.count(Message.id))
        .first()
    )
    return sim

def require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if not api_key:
            return jsonify({'message': 'API key is missing'}), 401
        
        user = User.query.filter_by(api_key=api_key).first()
        if not user:
            return jsonify({'message': 'Invalid API key'}), 401
        
        return f(*args, **kwargs)
    return decorated

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'message': 'Token is missing'}), 401
        
        try:
            token = token.split(' ')[1]  # Remove 'Bearer ' prefix
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user = User.query.get(data['user_id'])
            if not current_user:
                return jsonify({'message': 'User not found'}), 401
        except:
            return jsonify({'message': 'Token is invalid'}), 401
        
        return f(current_user, *args, **kwargs)
    return decorated

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/api/auth', methods=['POST'])
def auth():
    data = request.get_json()
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'message': 'Missing username or password'}), 400
    
    user = User.query.filter_by(username=data['username']).first()
    if not user or not check_password_hash(user.password_hash, data['password']):
        return jsonify({'message': 'Invalid username or password'}), 401
    
    token = jwt.encode({
        'user_id': user.id,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    }, app.config['SECRET_KEY'])
    
    return jsonify({
        'token': token,
        'username': user.username,
        'role': user.role,
        'api_key': user.api_key
    })

@app.route('/api/sim-cards', methods=['GET'])
@require_api_key
def get_sim_cards():
    sim_cards = SimCard.query.all()
    return jsonify({
        'sim_cards': [{
            'id': sim.id,
            'number': sim.number,
            'status': sim.status
        } for sim in sim_cards]
    })

@app.route('/api/sim-cards', methods=['POST'])
@require_api_key
def add_sim_card():
    data = request.get_json()
    if not data or not data.get('number'):
        return jsonify({'message': 'Phone number is required'}), 400
    
    try:
        sim_card = SimCard(
            number=data['number'],
            status=data.get('status', 'active')
        )
        db.session.add(sim_card)
        db.session.commit()
        
        log = Log(
            action='add_sim_card',
            details=json.dumps({'number': data['number'], 'status': data.get('status', 'active')}),
            status='success'
        )
        db.session.add(log)
        db.session.commit()
        
        return jsonify({
            'message': 'SIM card added successfully',
            'sim_card': {
                'id': sim_card.id,
                'number': sim_card.number,
                'status': sim_card.status
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': str(e)}), 500

@app.route('/api/sim-cards/<sim_id>', methods=['PUT'])
@require_api_key
def update_sim_card(sim_id):
    data = request.get_json()
    if not data:
        return jsonify({'message': 'No data provided'}), 400
    
    sim_card = SimCard.query.get(sim_id)
    if not sim_card:
        return jsonify({'message': 'SIM card not found'}), 404
    
    try:
        if 'number' in data:
            sim_card.number = data['number']
        if 'status' in data:
            sim_card.status = data['status']
        
        db.session.commit()
        
        log = Log(
            action='update_sim_card',
            details=json.dumps({'sim_id': sim_id, 'updates': data}),
            status='success'
        )
        db.session.add(log)
        db.session.commit()
        
        return jsonify({
            'message': 'SIM card updated successfully',
            'sim_card': {
                'id': sim_card.id,
                'number': sim_card.number,
                'status': sim_card.status
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': str(e)}), 500

@app.route('/api/sim-cards/<sim_id>', methods=['DELETE'])
@require_api_key
def delete_sim_card(sim_id):
    sim_card = SimCard.query.get(sim_id)
    if not sim_card:
        return jsonify({'message': 'SIM card not found'}), 404
    
    try:
        db.session.delete(sim_card)
        db.session.commit()
        
        log = Log(
            action='delete_sim_card',
            details=json.dumps({'sim_id': sim_id}),
            status='success'
        )
        db.session.add(log)
        db.session.commit()
        
        return jsonify({'message': 'SIM card deleted successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': str(e)}), 500
@app.route('/api/sms', methods=['POST'])
@require_api_key
def send_sms():
    try:
        print("Received SMS send request")
        data = request.get_json()
        if not data:
            print("No data provided in request")
            return jsonify({'error': 'No data provided'}), 400

        # Validate required fields
        if not data.get('recipient'):
            print("Missing recipient in request")
            return jsonify({'error': 'Recipient phone number is required'}), 400
        if not data.get('message'):
            print("Missing message in request")
            return jsonify({'error': 'Message content is required'}), 400

        recipient = data['recipient']
        message_text = data['message']
        sim_card_id = data.get('sim_card_id')
        print(f"Processing SMS to {recipient} with sim_card_id: {sim_card_id}")

        # Validate phone number format
        if not recipient.startswith('+'):
            print(f"Invalid phone number format: {recipient}")
            return jsonify({'error': 'Phone number must start with + and include country code'}), 400

        # Get SIM card
        sim_card = None
        if sim_card_id:
            sim_card = SimCard.query.get(sim_card_id)
            if not sim_card:
                print(f"No SIM card found with ID: {sim_card_id}")
                return jsonify({'error': f'No SIM card found with ID: {sim_card_id}'}), 400
            if sim_card.status != 'active':
                print(f"SIM card {sim_card_id} is not active")
                return jsonify({'error': f'SIM card {sim_card_id} is not active'}), 400
        else:
            sim_card = get_next_available_sim()
            if not sim_card:
                print("No active SIM cards available")
                return jsonify({'error': 'No active SIM cards available'}), 400

        print(f"Using SIM card: {sim_card.number}")

        # Create message record
        message = Message(
            recipient=recipient,
            message=message_text,
            status='pending',
            direction='outgoing',
            sender_sim=sim_card.id
        )
        db.session.add(message)
        db.session.flush()  # ensure defaults like id and timestamp are generated
        print(f"Created message record with ID: {message.id}")

        print(f"Publishing message to MQTT broker at {MQTT_HOST}:{MQTT_PORT}")
        try:
            message_dict = message.to_dict()
            print(f"Message content: {message_dict}")
            
            # Always send to topic sms/send/<sender_number> (with + removed)
            mqtt_topic = f"sms/send/{sim_card.number.replace('+', '')}"
            payload = {"number": message_dict["recipient"],"message": message_dict["message"],"message_id": message_dict["id"]}
            publish.single(
                mqtt_topic, 
                json.dumps(payload), 
                hostname=MQTT_HOST, 
                port=MQTT_PORT,
                keepalive=60,
                qos=1
            )
            print(f"Message published successfully to topic: {mqtt_topic}")
        except Exception as e:
            print(f"Failed to publish message: {str(e)}")
            raise

        # Create log details
        log_details = {
            'recipient': recipient,
            'message_id': message.id,
            'sim_card': sim_card.number,
            'message': message_text[:100]  # Store first 100 chars
        }
        
        # Create log entry with properly formatted details
        log = Log(
            action='send_sms',
            details=json.dumps(log_details, ensure_ascii=False),
            status='pending',
            sender_sim=sim_card.id
        )
        db.session.add(log)
        
        # Commit both message and log
        db.session.commit()

        # Emit socket event
        socketio.emit('sms_status_update', {
            'message_id': message.id,
            'recipient': recipient,
            'status': 'pending'
        })

        return jsonify({
            'message': 'SMS queued for sending',
            'message_id': message.id,
            'sender_sim': sim_card.number
        })

    except Exception as e:
        db.session.rollback()
        print(f"Error in send_sms: {str(e)}")  # Add logging
        return jsonify({'error': f'Failed to send SMS: {str(e)}'}), 500


@app.route('/api/sms/inbox', methods=['GET'])
@require_api_key
def get_inbox():
    try:
        messages = Message.query.filter_by(direction='incoming').order_by(Message.timestamp.desc()).all()
        return jsonify({
            'messages': [msg.to_dict() for msg in messages]
        })
    except Exception as e:
        print(f"Error in get_inbox: {str(e)}")  # Add logging
        return jsonify({'error': 'Failed to fetch inbox messages'}), 500

@app.route('/api/sms/outbox', methods=['GET'])
@require_api_key
def get_outbox():
    try:
        messages = Message.query.filter_by(direction='outgoing').order_by(Message.timestamp.desc()).all()
        return jsonify({
            'messages': [msg.to_dict() for msg in messages]
        })
    except Exception as e:
        print(f"Error in get_outbox: {str(e)}")  # Add logging
        return jsonify({'error': 'Failed to fetch outbox messages'}), 500

@app.route('/api/logs', methods=['GET'])
@require_api_key
def get_logs():
    logs = Log.query.order_by(Log.timestamp.desc()).all()
    return jsonify({
        'logs': [log.to_dict() for log in logs]
    })
@app.route('/api/generate-api-key', methods=['POST'])
@token_required
def generate_api_key(current_user):
    try:
        api_key = secrets.token_hex(32)
        current_user.api_key = api_key
        db.session.commit()
        
        log = Log(
            action='generate_api_key',
            details=json.dumps({'user_id': current_user.id}),
            status='success'
        )
        db.session.add(log)
        db.session.commit()
        
        return jsonify({'api_key': api_key})
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': str(e)}), 500

@app.route('/api/sms-status', methods=['GET'])
@require_api_key
def get_all_sms_statuses():
    try:
        # Get all messages with their statuses
        messages = SmsStatus.query.order_by(SmsStatus.timestamp.desc()).all()
        
        # Format the response
        statuses = []
        for msg in messages:
            status = {
                'id': msg.id,
                'timestamp': int(msg.timestamp.timestamp()),
                'sender_number': msg.sender_number,
                'receiver_number': msg.receiver_number,
                'message': msg.message,
                'status': msg.status,
            }
            statuses.append(status)
            
        return jsonify({
            'statuses': statuses
        })
    except Exception as e:
        print(f"Error in get_all_sms_statuses: {str(e)}")
        return jsonify({'error': 'Failed to fetch SMS statuses'}), 500

def get_system_memory_stats():
    """Get system memory statistics"""
    memory = psutil.virtual_memory()
    return {
        'total': memory.total,
        'used': memory.used,
        'free': memory.free,
        'percent': memory.percent
    }

def get_database_file_size(db_path='instance/sms_gateway.db'):
    """Return the SQLite DB file size"""
    try:
        size_bytes = os.path.getsize(db_path)
        size_mb = size_bytes / (1024 * 1024)
        return {
            'name': os.path.basename(db_path),
            'size_bytes': size_bytes,
            'size_mb': round(size_mb, 2),
            'last_updated': datetime.datetime.now().isoformat()
        }
    except Exception as e:
        print(f"Error getting database size: {e}")
        return {
            'name': os.path.basename(db_path),
            'error': str(e),
            'size_bytes': 0,
            'size_mb': 0.0
        }

def get_component_memory_usage():
    """Get memory usage by main process and database file"""
    components = []

    process = psutil.Process()
    process_memory = process.memory_info().rss
    total_memory = psutil.virtual_memory().total

    components.append({
        'name': 'Main Process',
        'memory_usage': process_memory,
        'percentage': (process_memory / total_memory) * 100,
        'last_updated': datetime.datetime.now().isoformat()
    })

    db_info = get_database_file_size()
    db_size_bytes = db_info.get('size_bytes', 0)

    components.append({
        'name': 'Database File',
        'memory_usage': db_size_bytes,
        'percentage': (db_size_bytes / total_memory) * 100,
        'last_updated': datetime.datetime.now().isoformat()
    })

    return components

def get_message_statistics():
    """Get statistics about messages"""
    try:
        total_messages = Message.query.count()
        incoming_messages = Message.query.filter_by(direction='incoming').count()
        outgoing_messages = Message.query.filter_by(direction='outgoing').count()
        
        # Get messages for today
        today = datetime.datetime.now().date()
        messages_today = Message.query.filter(
            db.func.date(Message.timestamp) == today
        ).count()
        
        # Get messages per day for the last 7 days
        seven_days_ago = datetime.datetime.now() - datetime.timedelta(days=7)
        messages_per_day = db.session.query(
            db.func.date(Message.timestamp).label('date'),
            db.func.count(Message.id).label('count')
        ).filter(Message.timestamp >= seven_days_ago)\
         .group_by(db.func.date(Message.timestamp))\
         .all()
        
        messages_per_day = [{
            'date': day.date,
            'count': day.count
        } for day in messages_per_day]
        
        return {
            'total_messages': total_messages,
            'incoming_messages': incoming_messages,
            'outgoing_messages': outgoing_messages,
            'messages_today': messages_today,
            'messages_per_day': messages_per_day
        }
    except Exception as e:
        print(f"Error getting message statistics: {e}")
        return {
            'total_messages': 0,
            'incoming_messages': 0,
            'outgoing_messages': 0,
            'messages_today': 0,
            'messages_per_day': []
        }


from sqlalchemy import func, desc

def get_sim_card_statistics():
    """Get statistics about SIM cards"""
    try:
        total_sims = SimCard.query.count()
        active_sims = SimCard.query.filter_by(status='active').count()
        inactive_sims = SimCard.query.filter_by(status='inactive').count()

        # Get top 5 most used SIMs
        results = (
            db.session.query(
                SimCard.number.label("number"),
                func.count(Message.id).label("message_count")
            )
            .join(Message, SimCard.id == Message.sender_sim)
            .group_by(SimCard.number)
            .order_by(desc("message_count"))
            .limit(5)
            .all()
        )

        most_used_sims = [
            {'number': r.number, 'message_count': r.message_count}
            for r in results
        ]

        most_used_sim = most_used_sims[0] if most_used_sims else {'number': 'N/A', 'message_count': 0}

        return {
            'total_sims': total_sims,
            'active_sims': active_sims,
            'inactive_sims': inactive_sims,
            'most_used_sim': most_used_sim,
            'most_used_sims': most_used_sims
        }

    except Exception as e:
        print(f"Error getting SIM card statistics: {e}")
        return {
            'total_sims': 0,
            'active_sims': 0,
            'inactive_sims': 0,
            'most_used_sim': {'number': 'N/A', 'message_count': 0},
            'most_used_sims': []
        }


@app.route('/api/statistics', methods=['GET'])
@require_api_key
def get_statistics():
    """Get system statistics including memory usage, database size, messages, and SIM cards"""
    try:
        stats = {
            'memory': get_system_memory_stats(),
            'components': get_component_memory_usage(),
            'database': get_database_file_size(),
            'messages': get_message_statistics(),
            'sim_cards': get_sim_card_statistics()
        }
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5001, debug=True)
