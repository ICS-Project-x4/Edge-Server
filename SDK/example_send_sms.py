from sms_sdk import SmsGatewayClient

# Replace with your actual API URL and API key
`API_KEY = "79a990f718f1d7351a8f6379826596dfe4c7d2fcb7844b3148e990e44fe11c48"  # <-- Put your real API key here

# Replace with the recipient's phone number and your message
RECIPIENT = "+1234567890"  # <-- Put the recipient's phone number here
MESSAGE = "Hello! This is a test message sent using the SDK."

client = SmsGatewayClient(API_URL, API_KEY)

try:
    result = client.send_sms(RECIPIENT, MESSAGE)
    print("SMS sent successfully! Response:")
    print(result)
except Exception as e:
    print("Failed to send SMS:", e)