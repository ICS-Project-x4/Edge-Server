import requests

class SmsGatewayClient:
    def __init__(self, api_key):
        """
        :param api_url: Base URL of the SMS Gateway API, e.g. 'http://localhost:5001'
        :param api_key: Your API key for authentication
        """
        self.api_url = "http://192.168.95.187:5001"
        self.api_key = api_key
        self.headers = {
            'X-API-Key': self.api_key,
            'Content-Type': 'application/json'
        }

    def send_sms(self, recipient, message, sim_card_id=None):
        """
        Send an SMS message.
        :param recipient: Phone number (must start with + and country code)
        :param message: Message text
        :param sim_card_id: (Optional) SIM card ID to use
        :return: Response JSON
        """
        payload = {
            'recipient': recipient,
            'message': message
        }
        if sim_card_id:
            payload['sim_card_id'] = sim_card_id

        response = requests.post(
            f"{self.api_url}/api/sms",
            json=payload,
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()

    def get_sms_statuses(self):
        """
        Get all SMS statuses.
        :return: List of statuses
        """
        response = requests.get(
            f"{self.api_url}/api/sms-status",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json().get('statuses', [])