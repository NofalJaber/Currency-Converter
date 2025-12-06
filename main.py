import requests
import xml.etree.ElementTree as ET
import json
import os
import time
from datetime import datetime

BNR_XML_URL = "https://www.bnr.ro/nbrfxrates.xml"
CACHE_FILE = "bnr_rates_cache.json"

class FXRateManager:
    def __init__(self):
        self.rates = {}
        self.timestamp = None


    def parse_bnr_xml(self, xml_content):

        try:
            root = ET.fromstring(xml_content)

            namespaces = {'ns': 'http://www.bnr.ro/xsd'}

            # Find the date
            cube = root.find('.//ns:Cube', namespaces)
            date_str = cube.get('date') if cube is not None else datetime.now().strftime("%Y-%m-%d")

            normalized_rates = {}

            # Iterate through all 'Rate' tags
            for rate_node in root.findall('.//ns:Rate', namespaces):

                # Get currency, value and multiplier
                currency = rate_node.get('currency')
                value = float(rate_node.text)
                multiplier = rate_node.get('multiplier')

                # Calculate RON per ONE unit
                if multiplier:
                    value = value / float(multiplier)

                normalized_rates[currency] = value

            # Add RON
            normalized_rates['RON'] = 1.0

            return {
                "timestamp": date_str,
                "fetched_at_epoch": time.time(),
                "rates": normalized_rates
            }
        except Exception as e:
            print(f"Error parsing XML: {e}")
            return None


    def save_to_cache(self, data):

        # Save data to a local JSON file
        try:
            with open(CACHE_FILE, 'w') as f:
                json.dump(data, f, indent=4)
            print("Rates cached successfully.")
        except IOError as e:
            print(f"Failed to write cache: {e}")


    def load_from_cache(self):

        # Load data from local JSON file if network fails
        if not os.path.exists(CACHE_FILE):
            return None

        try:
            with open(CACHE_FILE, 'r') as f:
                data = json.load(f)
            print("Loaded rates from local cache.")
            return data
        except (IOError, json.JSONDecodeError):
            return None


    def refresh_rates(self):

        # Try Network, if not, get rates from local JSON file
        print(f"Attempting to fetch from {BNR_XML_URL}...")

        try:
            response = requests.get(BNR_XML_URL, timeout=10)
            response.raise_for_status()
            data = self.parse_bnr_xml(response.content)
            if data:
                self.save_to_cache(data)
        except requests.exceptions.RequestException as e:
            print(f"Network error: {e}")

        if not data:
            data = self.load_from_cache()

        if data:
            self.rates = data['rates']
            self.timestamp = data['timestamp']
            return True
        else:
            raise RuntimeError("Could not fetch rates and no cache available.")


    def convert(self, amount, from_currency, to_currency):

        # Convert amount from one currency to another using RON as pivot
        if not self.rates:
            self.refresh_rates()

        from_currency = from_currency.upper()
        to_currency = to_currency.upper()

        # Check missing currencies
        if from_currency not in self.rates:
            raise ValueError(f"Currency '{from_currency}' not found in rates.")
        if to_currency not in self.rates:
            raise ValueError(f"Currency '{to_currency}' not found in rates.")

        # Check zero/negative amounts
        if amount <= 0:
            raise ValueError("Amount must be greater than zero.")

        # Calculate conversion
        rate_from = self.rates[from_currency]
        rate_to = self.rates[to_currency]

        # (Amount * Rate_from_in_RON) / Rate_to_in_RON
        result_in_ron = amount * rate_from
        final_result = result_in_ron / rate_to

        return round(final_result, 4)


if __name__ == "__main__":
    manager = FXRateManager()

    try:
        manager.refresh_rates()

        # Simple Convert
        result = manager.convert(100, 'EUR', 'USD')
        print(f"100 EUR = {result} USD")

        # Multiplier Currency (HUF -> RON)
        result_huf = manager.convert(1000, 'HUF', 'RON')
        print(f"1000 HUF = {result_huf} RON")

        # Error Handling
        manager.convert(-50, 'EUR', 'USD')

    except Exception as e:
        print(f"Error: {e}")