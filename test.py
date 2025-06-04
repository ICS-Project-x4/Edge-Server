import paho.mqtt.publish as publish

publish.single(
            topic="sms/send",
            payload="testing",
            hostname="localhost"
        )