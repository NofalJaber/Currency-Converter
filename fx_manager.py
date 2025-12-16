import json
import logging
import os
import time
import xml.etree.ElementTree as ET
from datetime import datetime

import requests

import config

logger = logging.getLogger(__name__)


class FXRateManager:
    def __init__(self):
        self.rates = {}
        self.timestamp = None

    def parse_bnr_xml(self, xml_content):
        try:
            root = ET.fromstring(xml_content)
            namespaces = {'ns': 'http://www.bnr.ro/xsd'}

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

            normalized_rates['RON'] = 1.0

            return {
                "timestamp": date_str,
                "fetched_at_epoch": time.time(),
                "rates": normalized_rates
            }

        except Exception as e:
            logger.error(f"Error parsing XML: {e}")
            return None

    def save_to_cache(self, data):
        try:
            with open(config.CACHE_FILE, 'w') as f:
                json.dump(data, f, indent=4)

        except Exception as e:
            logger.error(f"Failed to write cache: {e}")

    def load_from_cache(self):
        if not os.path.exists(config.CACHE_FILE):
            return None

        try:
            with open(config.CACHE_FILE, 'r') as f:
                return json.load(f)

        except (Exception, json.JSONDecodeError):
            return None

    # Try Network if forced, else, get rates from local cache (if newer than 24h)
    def refresh_rates(self, force_network=False):
        cached_data = self.load_from_cache()
        cache_age = float('inf')

        if cached_data:
            fetched_at = cached_data.get('fetched_at_epoch', 0)
            cache_age = time.time() - fetched_at

        if not force_network and cached_data and cache_age < 86400:  # 24 hours
            self.rates = cached_data['rates']
            self.timestamp = cached_data['timestamp']
            return False  # False indicates "Not Online"

        try:
            response = requests.get(config.BNR_XML_URL, timeout=10)
            response.raise_for_status()
            data = self.parse_bnr_xml(response.content)
            if data:
                self.save_to_cache(data)
                self.rates = data['rates']
                self.timestamp = data['timestamp']
                return True  # True indicates "Online"

        except requests.exceptions.RequestException as e:
            logger.error(f"Network error: {e}")

        # Fallback to cache if network failed
        if cached_data:
            self.rates = cached_data['rates']
            self.timestamp = cached_data['timestamp']
            return False  # Used cache (fallback)

        raise RuntimeError("Could not fetch rates and no cache available.")

    # Convert currency using RON as pivot
    def convert(self, amount, from_curr, to_curr):
        if not self.rates:
            self.refresh_rates()

        rate_from = self.rates.get(from_curr)
        rate_to = self.rates.get(to_curr)

        if not rate_from or not rate_to:
            raise ValueError("Currency not found.")

        result_in_ron = amount * rate_from
        return round(result_in_ron / rate_to, 4)
