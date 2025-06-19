import logging
import paho.mqtt.publish as publish

logging.basicConfig(level=logging.DEBUG)  # Logs connection, socket, etc.

try:
    publish.single(
        topic="sms/send",
        payload="testing",
        hostname="192.168.95.187"
    )
except Exception as e:
    print(f"MQTT publish failed: {e}")

import socket
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
result = sock.connect_ex(("192.168.95.187", 1883))
print("Socket test:", "Success" if result == 0 else f"Failed with code {result}")
sock.close()
