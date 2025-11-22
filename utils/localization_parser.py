"""Localization key parser for transforming keys into readable text

This module provides utilities to parse Apple Shortcuts localization keys
and transform them into human-readable text when the actual localized strings
are not available in the database.
"""

import re
from typing import Dict, Any, Optional, List


# Common acronyms to preserve in uppercase
KNOWN_ACRONYMS = {
    'URL', 'URI', 'HTML', 'XML', 'JSON', 'API', 'UI', 'ID', 'PDF', 'CSS',
    'HTTP', 'HTTPS', 'FTP', 'SSH', 'DNS', 'IP', 'TCP', 'UDP', 'SQL', 'SMS',
    'MMS', 'GPS', 'USB', 'CPU', 'GPU', 'RAM', 'ROM', 'OS', 'iOS', 'macOS',
    'UTC', 'GMT', 'RGB', 'RGBA', 'AVI', 'MP3', 'MP4', 'PNG', 'JPG', 'JPEG',
    'GIF', 'SVG', 'CSV', 'TSV', 'ZIP', 'TAR', 'GZ', 'WWW', 'VPN', 'LAN',
    'WAN', 'WiFi', 'NFC', 'RFID', 'OCR', 'AI', 'ML', 'AR', 'VR', 'XR'
}


def is_localization_key(text: str) -> bool:
    """
    Check if text appears to be a localization key rather than actual localized text.

    Enhanced pattern detection for various key formats:
    - Version-based: photos_IncreaseWarmth_1.0.0_intent_title
    - Entity type: browser_SearchableWebsiteEntity_1.0.0_entity_type_display_representation
    - Constant case: CONTROL_CENTER_TOGGLE_RECORDING_INTENT_TITLE
    - Embedded keys in otherwise good text

    Args:
        text: Text to check

    Returns:
        True if this looks like a localization key
    """
    if not text or not isinstance(text, str):
        return False

    # Pattern 1: Contains version numbers like _1.0.0_
    if re.search(r'_\d+\.\d+\.\d+_', text):
        return True

    # Pattern 2: Ends with common localization key suffixes
    if re.search(r'_(description|name|parameter|intent|entity|type|title|representation)$', text, re.IGNORECASE):
        return True

    # Pattern 3: All caps with underscores (likely constant case key)
    # But not single words or very short strings
    if text.isupper() and '_' in text and len(text) > 15:
        # Check if it looks like a key suffix
        if any(suffix in text for suffix in ['_INTENT_', '_TITLE', '_DESCRIPTION', '_NAME', '_PARAMETER']):
            return True

    # Pattern 4: Contains embedded localization keys within text
    # Look for patterns like: text browser_something_1.0.0_entity more text
    if re.search(r'\w+_\w+_\d+\.\d+\.\d+_\w+', text):
        return True

    # Pattern 5: Multiple underscores with no spaces (snake_case identifier style)
    # But be careful not to flag legitimate snake_case names
    if text.count('_') >= 4 and ' ' not in text:
        # Additional check: contains typical key components
        if any(comp in text.lower() for comp in ['intent', 'entity', 'parameter', 'description', 'representation']):
            return True

    return False


def get_localization_key_confidence(text: str) -> float:
    """
    Return confidence score (0.0-1.0) that text is a localization key.

    Higher scores indicate stronger confidence that this is a key rather than
    actual localized text.

    Args:
        text: Text to analyze

    Returns:
        Confidence score from 0.0 (definitely not a key) to 1.0 (definitely a key)
    """
    if not text or not isinstance(text, str):
        return 0.0

    score = 0.0

    # Strong indicators
    if re.search(r'_\d+\.\d+\.\d+_', text):
        score += 0.6  # Version number is very strong indicator

    if re.search(r'_(description|intent|entity|type|parameter|representation|title)$', text, re.IGNORECASE):
        score += 0.4  # Suffix match

    # Moderate indicators
    if text.count('_') >= 4:
        score += 0.2

    if ' ' not in text and len(text) > 20:
        score += 0.15  # Long strings without spaces

    if text.isupper() and '_' in text:
        score += 0.3  # Constant case

    # Negative indicators (reduce confidence)
    if ' ' in text and text.count(' ') > text.count('_'):
        score -= 0.4  # Looks more like natural text

    if len(text) > 0 and text[0].isupper() and len(text) > 1 and text[1:].islower():
        score -= 0.3  # Title case suggests real text

    return max(0.0, min(1.0, score))


def camel_case_to_title(text: str) -> str:
    """
    Convert camelCase or PascalCase to Title Case with spaces.

    Examples:
        "IncreaseWarmth" → "Increase Warmth"
        "SearchableWebsiteEntity" → "Searchable Website Entity"
        "URLHandler" → "URL Handler"
        "parseHTMLDocument" → "parse HTML Document"

    Args:
        text: CamelCase string

    Returns:
        Title Case string with spaces
    """
    if not text:
        return text

    # Handle acronyms - find sequences of capitals
    # URLHandler → URL Handler
    result = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1 \2', text)

    # Add space before capital letters that follow lowercase
    # IncreaseWarmth → Increase Warmth
    result = re.sub(r'([a-z])([A-Z])', r'\1 \2', result)

    # Split into words
    words = result.split()

    # Check each word for known acronyms
    processed_words = []
    for word in words:
        if word.upper() in KNOWN_ACRONYMS:
            processed_words.append(word.upper())
        else:
            # Normal title case
            processed_words.append(word.capitalize())

    return ' '.join(processed_words)


def constant_to_title(text: str) -> str:
    """
    Convert CONSTANT_CASE to Title Case.

    Examples:
        "CONTROL_CENTER_TOGGLE_RECORDING_INTENT_TITLE" → "Control Center Toggle Recording"
        "URL_HANDLER" → "URL Handler"

    Args:
        text: CONSTANT_CASE string

    Returns:
        Title Case string
    """
    if not text:
        return text

    # Remove common suffixes
    for suffix in ['_INTENT_TITLE', '_INTENT_DESCRIPTION', '_INTENT', '_TITLE', '_DESCRIPTION', '_NAME']:
        if text.endswith(suffix):
            text = text[:len(text)-len(suffix)]
            break

    # Split on underscores
    words = text.split('_')

    # Process each word
    processed_words = []
    for word in words:
        if word in KNOWN_ACRONYMS:
            processed_words.append(word)
        else:
            processed_words.append(word.capitalize())

    return ' '.join(processed_words)


def parse_localization_key(key: str) -> Dict[str, Any]:
    """
    Parse a localization key and extract meaningful components.

    Supports multiple key patterns:
    1. Version-based: prefix_EntityName_1.0.0_suffix
    2. Entity type: app_EntityName_1.0.0_entity_type_display_representation
    3. Constant case: CONSTANT_WITH_UNDERSCORES
    4. Parameter keys: intent_1.0.0_intent_parameter_name_description

    Args:
        key: Localization key string

    Returns:
        Dictionary with:
            - is_key: bool
            - pattern_type: str
            - extracted_name: str
            - confidence: float
            - components: dict
            - original: str
    """
    result = {
        'is_key': False,
        'pattern_type': None,
        'extracted_name': key,
        'confidence': 0.0,
        'components': {},
        'original': key
    }

    if not key or not isinstance(key, str):
        return result

    # Check if it's a localization key
    if not is_localization_key(key):
        return result

    result['is_key'] = True
    result['confidence'] = get_localization_key_confidence(key)

    # Pattern 1: Entity type representation (check first - more specific)
    # Example: browser_SearchableWebsiteEntity_1.0.0_entity_type_display_representation
    # Also handle lowercase: browser_searchablewebsiteentity_1.0.0_entity_type_display_representation
    entity_match = re.match(r'(\w+)_(\w+[Ee]ntity)_(\d+\.\d+\.\d+)_entity_type_display_representation$', key, re.IGNORECASE)
    if entity_match:
        app, entity, version = entity_match.groups()
        result['pattern_type'] = 'entity_type'
        result['components'] = {
            'app': app,
            'entity': entity,
            'version': version
        }
        # Remove 'Entity' suffix (case-insensitive)
        entity_name = re.sub(r'entity$', '', entity, flags=re.IGNORECASE)
        # Handle both camelCase and lowercase
        if entity_name[0].isupper() or entity_name.find('_') == -1:
            result['extracted_name'] = camel_case_to_title(entity_name)
        else:
            # All lowercase, capitalize first letter of each word
            result['extracted_name'] = ' '.join(word.capitalize() for word in entity_name.split('_'))
        result['confidence'] = max(result['confidence'], 0.9)
        return result

    # Pattern 2: Parameter description (more specific than version-based)
    # Example: browser_SearchWebsiteIntent_1.0.0_intent_parameter_website_description
    param_match = re.match(r'(\w+)_(\w+Intent)_(\d+\.\d+\.\d+)_intent_parameter_(\w+)_description$', key)
    if param_match:
        app, intent, version, param_name = param_match.groups()
        result['pattern_type'] = 'parameter_description'
        result['components'] = {
            'app': app,
            'intent': intent,
            'version': version,
            'parameter': param_name
        }
        result['extracted_name'] = camel_case_to_title(param_name)
        result['confidence'] = max(result['confidence'], 0.85)
        return result

    # Pattern 3: Version-based keys (more general)
    # Example: photos_IncreaseWarmth_1.0.0_intent_title
    version_match = re.match(r'(\w+)_([A-Z]\w+)_(\d+\.\d+\.\d+)_(.+)$', key)
    if version_match:
        prefix, entity, version, suffix = version_match.groups()
        result['pattern_type'] = 'version_based'
        result['components'] = {
            'prefix': prefix,
            'entity': entity,
            'version': version,
            'suffix': suffix
        }
        result['extracted_name'] = camel_case_to_title(entity)
        result['confidence'] = max(result['confidence'], 0.9)
        return result

    # Pattern 4: Constant case
    # Example: CONTROL_CENTER_TOGGLE_RECORDING_INTENT_TITLE
    if key.isupper() and '_' in key:
        result['pattern_type'] = 'constant_case'
        result['components'] = {
            'words': key.split('_')
        }
        result['extracted_name'] = constant_to_title(key)
        result['confidence'] = max(result['confidence'], 0.85)
        return result

    # Pattern 5: Generic underscore-separated (fallback)
    # Try to extract the most meaningful part
    if '_' in key:
        result['pattern_type'] = 'generic_underscore'
        parts = key.split('_')

        # Look for camelCase parts (likely entity names)
        camel_parts = [p for p in parts if re.match(r'^[A-Z][a-z]+[A-Z]', p)]
        if camel_parts:
            result['extracted_name'] = camel_case_to_title(camel_parts[0])
            result['confidence'] = max(result['confidence'], 0.7)
        else:
            # Use the longest meaningful part
            meaningful_parts = [p for p in parts if len(p) > 3 and not p.isdigit()]
            if meaningful_parts:
                longest = max(meaningful_parts, key=len)
                result['extracted_name'] = longest.capitalize()
                result['confidence'] = max(result['confidence'], 0.6)

        result['components'] = {'parts': parts}
        return result

    # If nothing matched well, return original with low confidence
    result['pattern_type'] = 'unknown'
    result['confidence'] = 0.5
    return result


def clean_embedded_keys(text: str) -> str:
    """
    Find and replace embedded localization keys within text.

    Example:
        "Optionally, what to sort the browser_searchablewebsiteentity_1.0.0_entity_type_display_representation by."
        → "Optionally, what to sort the searchable website by."

    Args:
        text: Text that may contain embedded keys

    Returns:
        Cleaned text with keys replaced by readable names
    """
    if not text or not isinstance(text, str):
        return text

    # Find all embedded keys using pattern matching
    # Pattern: word_word_version_suffix
    pattern = r'\b(\w+_\w+_\d+\.\d+\.\d+_\w+)\b'

    def replace_key(match):
        key = match.group(1)
        parsed = parse_localization_key(key)
        if parsed['is_key'] and parsed['confidence'] > 0.7:
            return parsed['extracted_name'].lower()
        return key

    result = re.sub(pattern, replace_key, text, flags=re.IGNORECASE)

    # Also handle constant case embedded keys
    # Pattern: WORD_WORD_WORD (all caps, multiple underscores)
    constant_pattern = r'\b([A-Z][A-Z_]{10,})\b'

    def replace_constant(match):
        key = match.group(1)
        if '_' in key and get_localization_key_confidence(key) > 0.7:
            return constant_to_title(key).lower()
        return key

    result = re.sub(constant_pattern, replace_constant, result)

    return result


def generate_readable_name(key: str, fallback: Optional[str] = None) -> Dict[str, Any]:
    """
    Generate human-readable name from localization key with metadata.

    This is the main function to use for fixing localization keys.
    It returns both the readable name and metadata about the transformation.

    Args:
        key: Localization key
        fallback: Optional fallback value if key cannot be parsed

    Returns:
        Dictionary with:
            - value: str (readable name or original if unparseable)
            - is_synthetic: bool (True if value was generated)
            - original_key: str (original key if synthetic)
            - confidence: float (confidence in transformation)
            - source: str ('parsed_key', 'original', or 'fallback')
    """
    result = {
        'value': key,
        'is_synthetic': False,
        'original_key': None,
        'confidence': 1.0,
        'source': 'original'
    }

    if not key or not isinstance(key, str):
        if fallback:
            result['value'] = fallback
            result['source'] = 'fallback'
        return result

    # Check if it's a localization key
    if not is_localization_key(key):
        # Not a key, use as-is
        return result

    # First check if there are embedded keys in otherwise good text
    if ' ' in key:
        cleaned = clean_embedded_keys(key)
        if cleaned != key:
            result['value'] = cleaned
            result['is_synthetic'] = True
            result['original_key'] = key
            result['confidence'] = 0.85
            result['source'] = 'cleaned_embedded'
            return result

    # Parse the key
    parsed = parse_localization_key(key)

    if parsed['is_key'] and parsed['confidence'] > 0.6:
        result['value'] = parsed['extracted_name']
        result['is_synthetic'] = True
        result['original_key'] = key
        result['confidence'] = parsed['confidence']
        result['source'] = 'parsed_key'
    elif fallback:
        result['value'] = fallback
        result['source'] = 'fallback'

    return result
