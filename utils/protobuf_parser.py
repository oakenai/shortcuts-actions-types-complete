"""Protobuf parsing utilities for decoding BLOB fields"""

import re
from typing import Dict, List, Any, Optional, Tuple
import struct


def extract_strings_from_blob(blob: bytes, min_length: int = 3) -> List[str]:
    """
    Extract ASCII/UTF-8 strings from a protobuf BLOB.
    This works even without knowing the .proto schema.

    Args:
        blob: Binary protobuf data
        min_length: Minimum string length to extract

    Returns:
        List of extracted strings
    """
    if not blob:
        return []

    strings = []

    # Pattern 1: ASCII printable strings
    ascii_pattern = rb'[\x20-\x7e]{' + str(min_length).encode() + rb',}'
    for match in re.finditer(ascii_pattern, blob):
        strings.append(match.group().decode('ascii'))

    # Pattern 2: UTF-8 strings (more permissive)
    try:
        # Look for length-prefixed strings (common in protobuf)
        i = 0
        while i < len(blob) - 2:
            # Check if this could be a length-delimited field
            if blob[i] & 0x07 == 2:  # Wire type 2 = length-delimited
                i += 1
                # Try to read varint length
                length, varint_size = decode_varint(blob[i:])
                if length > 0 and length < 1000:  # Reasonable string length
                    string_start = i + varint_size
                    string_end = string_start + length
                    if string_end <= len(blob):
                        try:
                            s = blob[string_start:string_end].decode('utf-8', errors='ignore')
                            if s.isprintable() and len(s) >= min_length:
                                if s not in strings:  # Avoid duplicates
                                    strings.append(s)
                        except:
                            pass
            i += 1
    except:
        pass

    return list(set(strings))  # Remove duplicates


def decode_varint(data: bytes) -> Tuple[int, int]:
    """
    Decode a protobuf varint.

    Args:
        data: Bytes starting with varint

    Returns:
        Tuple of (decoded_value, num_bytes_consumed)
    """
    value = 0
    shift = 0
    consumed = 0

    for byte in data:
        consumed += 1
        value |= (byte & 0x7F) << shift
        if not (byte & 0x80):
            break
        shift += 7
        if consumed > 10:  # Varints can't be longer than 10 bytes
            break

    return value, consumed


def decode_protobuf_blob(blob: bytes) -> Dict[str, Any]:
    """
    Attempt to decode a protobuf BLOB without knowing the schema.
    Returns a dictionary of field_number -> value.

    Args:
        blob: Binary protobuf data

    Returns:
        Dictionary of decoded fields
    """
    if not blob:
        return {}

    result = {
        'raw_size': len(blob),
        'fields': {},
        'strings': extract_strings_from_blob(blob),
    }

    try:
        i = 0
        while i < len(blob):
            # Read field tag
            if i >= len(blob):
                break

            tag, tag_size = decode_varint(blob[i:])
            field_number = tag >> 3
            wire_type = tag & 0x07
            i += tag_size

            # Decode based on wire type
            if wire_type == 0:  # Varint
                value, size = decode_varint(blob[i:])
                result['fields'][f'field_{field_number}_varint'] = value
                i += size

            elif wire_type == 1:  # 64-bit
                if i + 8 <= len(blob):
                    value = struct.unpack('<d', blob[i:i+8])[0]
                    result['fields'][f'field_{field_number}_64bit'] = value
                    i += 8
                else:
                    break

            elif wire_type == 2:  # Length-delimited
                length, length_size = decode_varint(blob[i:])
                i += length_size
                if i + length <= len(blob):
                    data = blob[i:i+length]
                    # Try to decode as string
                    try:
                        s = data.decode('utf-8')
                        if s.isprintable():
                            result['fields'][f'field_{field_number}_string'] = s
                        else:
                            result['fields'][f'field_{field_number}_bytes'] = data.hex()
                    except:
                        # Could be nested message or bytes
                        result['fields'][f'field_{field_number}_bytes'] = data.hex()
                    i += length
                else:
                    break

            elif wire_type == 5:  # 32-bit
                if i + 4 <= len(blob):
                    value = struct.unpack('<f', blob[i:i+4])[0]
                    result['fields'][f'field_{field_number}_32bit'] = value
                    i += 4
                else:
                    break

            else:
                # Unknown wire type, skip
                break

    except Exception as e:
        result['parse_error'] = str(e)

    return result


def analyze_requirements_blob(blob: bytes) -> Dict[str, Any]:
    """
    Analyze a requirements BLOB from Tools table.
    Common pattern: OS version requirements, capabilities.

    Args:
        blob: Requirements BLOB

    Returns:
        Dictionary with analysis results
    """
    result = {
        'size': len(blob),
        'likely_os_versions': [],
        'strings': extract_strings_from_blob(blob),
        'decoded': decode_protobuf_blob(blob),
    }

    # Look for version patterns (e.g., varint fields that could be versions)
    decoded_fields = result['decoded'].get('fields', {})
    for key, value in decoded_fields.items():
        if 'varint' in key:
            # Check if value looks like OS version (7, 8, 9, etc.)
            if 1 <= value <= 20:
                result['likely_os_versions'].append(value)

    return result


def analyze_type_instance_blob(blob: bytes) -> Dict[str, Any]:
    """
    Analyze a typeInstance BLOB from Parameters table.
    Often contains UTI types like "public.folder".

    Args:
        blob: Type instance BLOB

    Returns:
        Dictionary with analysis results
    """
    result = {
        'size': len(blob),
        'uti_types': [],
        'strings': extract_strings_from_blob(blob),
        'decoded': decode_protobuf_blob(blob),
    }

    # Look for UTI patterns
    for s in result['strings']:
        if '.' in s and ('public' in s or 'com.' in s):
            result['uti_types'].append(s)

    return result


def analyze_coercion_blob(blob: bytes) -> Dict[str, Any]:
    """
    Analyze a coercionDefinition BLOB from TypeCoercions table.

    Args:
        blob: Coercion definition BLOB

    Returns:
        Dictionary with analysis results
    """
    result = {
        'size': len(blob),
        'strings': extract_strings_from_blob(blob),
        'decoded': decode_protobuf_blob(blob),
    }

    return result


def format_blob_analysis(analysis: Dict[str, Any], indent: int = 2) -> str:
    """
    Format blob analysis for human-readable display.

    Args:
        analysis: Analysis dictionary
        indent: Indentation level

    Returns:
        Formatted string
    """
    lines = []
    prefix = ' ' * indent

    lines.append(f"{prefix}Size: {analysis.get('size', 0)} bytes")

    if 'strings' in analysis and analysis['strings']:
        lines.append(f"{prefix}Strings found:")
        for s in analysis['strings']:
            lines.append(f"{prefix}  - {s}")

    if 'uti_types' in analysis and analysis['uti_types']:
        lines.append(f"{prefix}UTI Types:")
        for uti in analysis['uti_types']:
            lines.append(f"{prefix}  - {uti}")

    if 'likely_os_versions' in analysis and analysis['likely_os_versions']:
        lines.append(f"{prefix}Likely OS Versions:")
        for v in analysis['likely_os_versions']:
            lines.append(f"{prefix}  - iOS/macOS {v}")

    if 'decoded' in analysis and 'fields' in analysis['decoded']:
        fields = analysis['decoded']['fields']
        if fields:
            lines.append(f"{prefix}Decoded Fields:")
            for key, value in fields.items():
                if isinstance(value, str) and len(value) > 100:
                    value = value[:100] + "..."
                lines.append(f"{prefix}  {key}: {value}")

    return '\n'.join(lines)
