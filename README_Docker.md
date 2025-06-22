# SMS Gateway - Docker Setup

This document explains how to run the SMS Gateway project using Docker.

## Prerequisites

- Docker
- Docker Compose

## Project Structure

```
ics-sms-project/
├── Dockerfile                 # Main SMS Gateway
├── docker-compose.yml         # Complete system setup
├── requirements.txt           # Main app dependencies
├── app.py                     # Main SMS Gateway
├── config.json                # Configuration
├── otp_app/
│   ├── Dockerfile            # OTP application
│   ├── requirements.txt      # OTP app dependencies
│   ├── otp_app_backend.py    # OTP backend
│   └── templates/
│       └── otp_login.html    # OTP frontend
└── SDK/
    └── sms_sdk.py            # SDK for external use
```

## Quick Start

### 1. Build and Start All Services

```bash
# Build and start all services
docker-compose up --build

# Or run in background
docker-compose up -d --build
```

### 2. Access the Applications

- **SMS Gateway Dashboard**: http://localhost:5001
- **OTP Login Demo**: http://localhost:5002
- **MQTT Broker**: localhost:1883

### 3. Stop Services

```bash
docker-compose down
```

## Services

### 1. Mosquitto MQTT Broker
- **Port**: 1883 (MQTT), 9001 (WebSocket)
- **Purpose**: Message broker for SMS communication
- **Configuration**: Stored in `./mosquitto/config/`

### 2. SMS Gateway (Main Application)
- **Port**: 5001
- **Purpose**: Main SMS gateway with API endpoints
- **Database**: SQLite stored in `./instance/`
- **Configuration**: Uses `config.json`
- **Note**: The main app uses Flask and communicates with the MQTT broker (Mosquitto) and the OTP app via HTTP and MQTT.

### 3. OTP Application
- **Port**: 5002
- **Purpose**: Demo OTP login system
- **Dependencies**: Communicates with SMS Gateway via HTTP
- **Note**: The OTP app uses Flask and should use `sms_gateway` as the API_URL when running in Docker.

## Configuration

### Update SMS Gateway Configuration

Edit `config.json`:
```json
{
  "MQTT": {
    "host": "mosquitto",
    "port": 1883
  }
}
```

### Update OTP App Configuration

Edit `otp_app/otp_app_backend.py`:
```python
API_URL = "http://sms_gateway:5001"  # Use container name in Docker
```

## Development

### Running Individual Services

```bash
# Run only MQTT broker
docker-compose up mosquitto

# Run only SMS Gateway
docker-compose up sms_gateway

# Run only OTP app
docker-compose up otp_app
```

### Rebuild Only One Service

```bash
# Rebuild and restart only the OTP app
docker-compose up -d --build otp_app

# Rebuild and restart only the SMS Gateway
docker-compose up -d --build sms_gateway
```

### Persisting the SQLite Database

The SQLite database is stored in the `instance/` directory and is mounted as a volume in the container. This ensures your data persists across container restarts.

### Overriding Environment Variables

You can override environment variables using a `.env` file or by specifying them in `docker-compose.yml` under the `environment` section for each service.

Example `.env` file:
```
FLASK_ENV=production
SECRET_KEY=your_secret_key
MQTT_HOST=mosquitto
MQTT_PORT=1883
```

## Troubleshooting

### Template Not Found Errors
- Ensure your template files (e.g., `otp_login.html`) are in the correct `templates/` directory.
- Make sure the volume is mounted correctly in `docker-compose.yml`:
  ```yaml
  volumes:
    - ./otp_app/templates:/app/templates
  ```
- Restart the container after adding or moving templates.

### Common Issues

1. **Port Already in Use**
   ```bash
   # Check what's using the port
   lsof -i :5001
   
   # Stop conflicting services
   docker-compose down
   ```

2. **Container Won't Start**
   ```bash
   # Check logs
   docker-compose logs <service_name>
   
   # Rebuild
   docker-compose build --no-cache
   ```

3. **Database Issues**
   ```bash
   # Remove database volume
   docker-compose down -v
   docker-compose up --build
   ```

4. **Network Issues**
   ```bash
   # Check network
   docker network ls
   docker network inspect ics-sms-project_sms_network
   ```

### Reset Everything

```bash
# Stop and remove everything
docker-compose down -v
docker system prune -f
docker-compose up --build
```

## Production Deployment

### Environment Variables

Create `.env` file:
```env
FLASK_ENV=production
SECRET_KEY=your_secret_key
MQTT_HOST=mosquitto
MQTT_PORT=1883
```

### Security Considerations

1. Change default passwords
2. Use HTTPS in production
3. Secure MQTT broker
4. Use environment variables for secrets
5. Regular security updates

### Scaling

```bash
# Scale SMS Gateway
docker-compose up --scale sms_gateway=3

# Use external database
# Update docker-compose.yml to use PostgreSQL/MySQL
```

## Monitoring

### Health Checks

```bash
# Check service health
docker-compose ps

# Monitor resource usage
docker stats
```

### Logs Management

```bash
# Configure log rotation
# Add to docker-compose.yml:
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
```

## Contributing

Contributions are welcome! Please open issues or pull requests for bug fixes, improvements, or new features.

## Support & Questions

- For issues and questions:
  1. Check the logs: `docker-compose logs`
  2. Verify configuration files
  3. Test individual services
  4. Check network connectivity between containers
  5. Open an issue or discussion in the repository 