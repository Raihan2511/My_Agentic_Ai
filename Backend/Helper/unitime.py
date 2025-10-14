import re
import xml.etree.ElementTree as ET
from difflib import SequenceMatcher


class UnitimeXMLHelper:

    @staticmethod
    def extract_id_map(xml_text):
        """
        Extract all ID-like attributes and return a mapping:
        {'course id': '904', 'offering id': '6728', ...}
        """
        return dict(re.findall(r'(\w+)\s*=\s*"(\d+)"', xml_text))

    @staticmethod
    def replace_ids(xml_text, id_map):
        """
        Replace all id="..." fields in xml_text with values from id_map
        based on their attribute name.
        """
        def replacer(match):
            attr = match.group(1)
            if attr in id_map:
                return f'{attr}="{id_map[attr]}"'
            else:
                return match.group(0)  # leave unchanged if not in map

        return re.sub(r'(\w+)\s*=\s*"\d+"', replacer, xml_text)

    @staticmethod
    def fix_xml(text):
        """
        Attempt to fix common malformed XML issues in model output.
        """
        text = text.strip()
        if not text.startswith("<"):
            text = "<" + text
        if text.count("<") > text.count(">"):
            text += ">"
        return text

    @staticmethod
    def is_valid_xml(xml_string):
        """
        Check if XML is well-formed.
        """
        try:
            ET.fromstring(xml_string)
            return True
        except:
            return False

    @staticmethod
    def calculate_exact_match(pred, truth):
        """
        Check if prediction exactly matches ground truth.
        """
        return pred.strip() == truth.strip()

    @staticmethod
    def calculate_bleu_score(pred, truth):
        """
        Simple BLEU-like score using character overlap.
        """
        matcher = SequenceMatcher(None, pred, truth)
        return matcher.ratio()

    @staticmethod
    def extract_xml_elements(xml_string):
        """
        Extract key XML elements for semantic comparison.
        """
        try:
            root = ET.fromstring(xml_string)
            elements = {}

            # Extract top-level attributes
            elements['term'] = root.get('term', '')
            elements['year'] = root.get('year', '')
            elements['campus'] = root.get('campus', '')

            # Extract subpart details
            subpart = root.find('subpart')
            if subpart is not None:
                elements['subject'] = subpart.get('subject', '')
                elements['course'] = subpart.get('course', '')
                elements['type'] = subpart.get('type', '')

            # Extract time preferences
            time_prefs = []
            for pref in root.findall('.//pref'):
                time_prefs.append({
                    'days': pref.get('days', ''),
                    'start': pref.get('start', ''),
                    'stop': pref.get('stop', ''),
                    'level': pref.get('level', '')
                })
            elements['time_prefs'] = time_prefs

            return elements
        except:
            return {}

    @staticmethod
    def calculate_semantic_accuracy(pred, truth):
        """
        Check if key XML elements match semantically.
        """
        pred_elements = UnitimeXMLHelper.extract_xml_elements(pred)
        truth_elements = UnitimeXMLHelper.extract_xml_elements(truth)

        if not pred_elements or not truth_elements:
            return 0.0

        matches = 0
        total = 0

        # Compare top-level attributes
        for key in ['term', 'year', 'campus', 'subject', 'course', 'type']:
            if key in pred_elements and key in truth_elements:
                total += 1
                if pred_elements[key] == truth_elements[key]:
                    matches += 1

        # Compare time preferences
        pred_prefs = pred_elements.get('time_prefs', [])
        truth_prefs = truth_elements.get('time_prefs', [])

        if len(pred_prefs) == len(truth_prefs):
            for p_pref, t_pref in zip(pred_prefs, truth_prefs):
                for attr in ['days', 'start', 'stop', 'level']:
                    total += 1
                    if p_pref.get(attr) == t_pref.get(attr):
                        matches += 1

        return matches / total if total > 0 else 0.0
