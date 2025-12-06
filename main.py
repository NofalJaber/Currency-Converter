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

    def get_rates(self):

        # Try Network, if not, get data from local JSON file
        print(f"Attempting to fetch from {BNR_XML_URL}...")

        try:
            response = requests.get(BNR_XML_URL, timeout=10)
            response.raise_for_status()

            # Parse and Normalize
            data = self.parse_bnr_xml(response.content)

            if data:
                # Save to Cache
                self.save_to_cache(data)
                return data

        except requests.exceptions.RequestException as e:
            print(f"Network error: {e}")

        # Load from cache if network or parse failed
        cached_data = self.load_from_cache()
        if cached_data:
            return cached_data

        raise RuntimeError("Could not fetch rates and no cache available.")


if __name__ == "__main__":
    manager = FXRateManager()

    try:
        data = manager.get_rates()

        print(f"\n--- Current Rates (RON base) ({data['timestamp']}) ---")
        print(f"EUR: {data['rates'].get('EUR')}")
        print(f"USD: {data['rates'].get('USD')}")
        print(f"RON: {data['rates'].get('RON')}")
        print(f"HUF: {data['rates'].get('HUF')}")

    except RuntimeError as e:
        print(e)