# SMS Gateway Backend Documentation

## Overview
The SMS Gateway is a Flask-based backend system that provides SMS messaging capabilities through a RESTful API. It supports both incoming and outgoing SMS messages, SIM card management, and real-time status updates via WebSocket connections.

## System Architecture

### Core Components
- **Flask Server**: Main web server handling HTTP requests
- **Socket.IO**: Real-time communication for status updates
- **MQTT Broker**: Message queuing for SMS operations
- **SQLite Database**: Data persistence for messages, SIM cards, and logs

### Key Features
- RESTful API for SMS operations
- Real-time status updates via WebSocket
- SIM card management
- Message logging and tracking
- System statistics and monitoring
- Authentication and API key management

## API Endpoints

### Authentication
- **POST /api/auth**
  - Authenticates users and returns JWT token
  - Required fields: username, password
  - Returns: token, username, role, api_key

### SIM Card Management
- **GET /api/sim-cards**
  - Lists all SIM cards
  - Requires API key
  - Returns: List of SIM cards with id, number, and status

- **POST /api/sim-cards**
  - Adds a new SIM card
  - Requires API key
  - Required fields: number
  - Optional fields: status

- **PUT /api/sim-cards/<sim_id>**
  - Updates SIM card details
  - Requires API key
  - Fields: number, status

- **DELETE /api/sim-cards/<sim_id>**
  - Deletes a SIM card
  - Requires API key

### SMS Operations
- **POST /api/sms**
  - Sends an SMS message
  - Requires API key
  - Required fields: recipient, message
  - Optional fields: sim_card_id
  - Returns: message_id, sender_sim

- **GET /api/sms/inbox**
  - Retrieves incoming messages
  - Requires API key
  - Returns: List of incoming messages

- **GET /api/sms/outbox**
  - Retrieves outgoing messages
  - Requires API key
  - Returns: List of outgoing messages

### System Management
- **GET /api/statistics**
  - Retrieves system statistics
  - Requires API key
  - Returns: Memory usage, database size, message stats, SIM card stats

- **GET /api/logs**
  - Retrieves system logs
  - Requires API key
  - Returns: List of system logs

- **POST /api/generate-api-key**
  - Generates new API key for authenticated user
  - Requires JWT token
  - Returns: New API key

## Authentication

### API Key Authentication
- Required for most endpoints
- Include in request headers as: `X-API-Key: your_api_key`

### JWT Authentication
- Required for user-specific operations
- Include in request headers as: `Authorization: Bearer your_jwt_token`

## WebSocket Events

### Available Events
- **sms_status_update**: Real-time SMS status updates
- **mqtt_status**: MQTT message status updates

## Database Schema

### Main Tables
1. **User**
   - id
   - username
   - password_hash
   - role
   - api_key

2. **SimCard**
   - id
   - number
   - status

3. **Message**
   - id
   - sender
   - recipient
   - message
   - direction
   - status
   - timestamp
   - sender_sim

4. **Log**
   - id
   - action
   - details
   - status
   - timestamp
   - sender_sim

5. **SmsStatus**
   - id
   - sender_number
   - receiver_number
   - message
   - status
   - timestamp

## Setup and Installation

### Prerequisites
- Python 3.x
- MQTT Broker (e.g., Mosquitto)
- Required Python packages (install via pip):
  ```
  flask
  flask-cors
  flask-socketio
  paho-mqtt
  psutil
  pyjwt
  sqlalchemy
  eventlet
  ```

### Configuration
1. Set up environment variables:
   - SECRET_KEY: For JWT token generation
   - Database path: Default is 'sqlite:///sms_gateway.db'

2. Configure MQTT broker:
   - Default host: localhost
   - Default port: 1883

### Running the Server
```bash
python app.py
```
Server runs on port 5001 by default.

## Error Handling
- All endpoints return appropriate HTTP status codes
- Error responses include descriptive messages
- Database operations are wrapped in try-catch blocks
- Failed operations are rolled back to maintain data integrity

## Security Considerations
- Passwords are hashed using Werkzeug's security functions
- API keys are required for most operations
- JWT tokens expire after 24 hours
- CORS is enabled for all origins (configurable)
- Database connections use connection pooling

## Monitoring and Statistics
The system provides various statistics including:
- System memory usage
- Database size
- Message counts (total, incoming, outgoing)
- SIM card usage statistics
- Daily message counts
- Component-wise memory usage

## Best Practices
1. Always use HTTPS in production
2. Regularly rotate API keys
3. Monitor system logs for unusual activity
4. Keep SIM card statuses up to date
5. Regularly backup the database
6. Monitor system statistics for performance issues
