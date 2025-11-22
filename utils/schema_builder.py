"""Schema building utilities for creating structured action/type schemas"""

from typing import Dict, Any, List, Optional
import sqlite3
from .db_utils import (
    get_action_parameters,
    get_parameter_types,
    get_action_output_types,
    get_action_categories,
    get_action_keywords,
    get_entity_properties,
    get_enum_cases,
    get_type_info,
)
from .protobuf_parser import (
    analyze_requirements_blob,
    analyze_type_instance_blob,
)
from .validators import is_localization_key, parse_type_identifier
from .localization_parser import generate_readable_name


def get_type_details(conn: sqlite3.Connection, type_id: str) -> Optional[Dict[str, Any]]:
    """
    Get detailed information about a type.

    Args:
        conn: Database connection
        type_id: Type identifier

    Returns:
        Type details dictionary or None
    """
    type_info = get_type_info(conn, type_id)
    if not type_info:
        return None

    # Build basic type details
    details = {
        'id': type_id,
        'name': type_info.get('name'),
        'kind': type_info.get('kind'),
        'kind_name': {
            1: 'primitive',
            2: 'entity',
            3: 'enum',
            4: 'object',
            6: 'array',
            8: 'special',
        }.get(type_info.get('kind'), 'unknown'),
        'parsed': parse_type_identifier(type_id),
    }

    # Add entity properties if entity type
    if type_info.get('kind') == 2:
        details['properties'] = get_entity_properties(conn, type_id)

    # Add enum cases if enum type
    if type_info.get('kind') == 3:
        details['enum_cases'] = get_enum_cases(conn, type_id)

    return details


def build_action_schema(
    conn: sqlite3.Connection,
    action_data: Dict[str, Any],
    include_protobuf: bool = True,
    include_type_info: bool = False,  # Disabled by default for speed
    fix_localizations: bool = True,  # NEW: Fix localization keys
    locale: str = "en"
) -> Dict[str, Any]:
    """
    Build a complete schema for an action including all metadata.

    Args:
        conn: Database connection
        action_data: Basic action data from get_all_actions()
        include_protobuf: Whether to decode protobuf BLOBs
        include_type_info: Whether to enrich with type information
        fix_localizations: Whether to fix localization keys with smart parsing
        locale: Language locale

    Returns:
        Complete action schema
    """
    tool_id = action_data['rowId']
    action_id = action_data['id']

    # Fix name localization if enabled
    name_result = generate_readable_name(action_data.get('name', '')) if fix_localizations else None
    if name_result and name_result['is_synthetic']:
        name = name_result['value']
        name_metadata = {
            'is_synthetic': True,
            'original_key': name_result['original_key'],
            'confidence': name_result['confidence'],
            'source': name_result['source']
        }
    else:
        name = action_data.get('name')
        name_metadata = {'is_synthetic': False}

    # Fix description localization if enabled
    desc_result = generate_readable_name(action_data.get('descriptionSummary', '')) if fix_localizations else None
    if desc_result and desc_result['is_synthetic']:
        description_summary = desc_result['value']
        description_metadata = {
            'is_synthetic': True,
            'original_key': desc_result['original_key'],
            'confidence': desc_result['confidence'],
            'source': desc_result['source']
        }
    else:
        description_summary = action_data.get('descriptionSummary')
        description_metadata = {'is_synthetic': False}

    schema = {
        'id': action_id,
        'name': name,
        'name_metadata': name_metadata,
        'description_summary': description_summary,
        'description_metadata': description_metadata,
        'description_note': action_data.get('descriptionNote'),
        'type': action_data.get('toolType'),
        'flags': action_data.get('flags'),
        'visibility_flags': action_data.get('visibilityFlags'),
        'hidden': action_data.get('visibilityFlags', 0) > 0,
        'source_provider': action_data.get('sourceActionProvider'),
        'app': {
            'bundle_id': action_data.get('container_id'),
            'name': action_data.get('app_name'),
        },
        'deprecation': None,
        'parameters': [],
        'output_types': [],
        'categories': [],
        'keywords': [],
        'localization_issues': []
    }

    # Flag localization issues at action level (only if not fixed)
    if not fix_localizations:
        if is_localization_key(action_data.get('name', '')):
            schema['localization_issues'].append('name_is_key')
        if is_localization_key(action_data.get('descriptionSummary', '')):
            schema['localization_issues'].append('description_is_key')

    # Deprecation info
    if action_data.get('deprecationReplacementId'):
        schema['deprecation'] = {
            'replacement_id': action_data.get('deprecationReplacementId'),
            'message': action_data.get('deprecationMessage'),
        }

    # Parameters
    parameters = get_action_parameters(conn, tool_id, locale)
    for param in parameters:
        # Fix parameter name localization
        param_name_result = generate_readable_name(param.get('name', '')) if fix_localizations else None
        if param_name_result and param_name_result['is_synthetic']:
            param_name = param_name_result['value']
            param_name_metadata = {
                'is_synthetic': True,
                'original_key': param_name_result['original_key'],
                'confidence': param_name_result['confidence'],
                'source': param_name_result['source']
            }
        else:
            param_name = param.get('name')
            param_name_metadata = {'is_synthetic': False}

        # Fix parameter description localization
        param_desc_result = generate_readable_name(param.get('description', '')) if fix_localizations else None
        if param_desc_result and param_desc_result['is_synthetic']:
            param_description = param_desc_result['value']
            param_desc_metadata = {
                'is_synthetic': True,
                'original_key': param_desc_result['original_key'],
                'confidence': param_desc_result['confidence'],
                'source': param_desc_result['source']
            }
        else:
            param_description = param.get('description')
            param_desc_metadata = {'is_synthetic': False}

        param_schema = {
            'key': param['key'],
            'name': param_name,
            'name_metadata': param_name_metadata,
            'description': param_description,
            'description_metadata': param_desc_metadata,
            'sort_order': param['sortOrder'],
            'flags': param['flags'],
            'accepted_types': get_parameter_types(conn, tool_id, param['key']),
            'localization_issues': []
        }

        # Flag localization issues (only if not fixed)
        if not fix_localizations:
            if is_localization_key(param.get('name', '')):
                param_schema['localization_issues'].append('name_is_key')
            if is_localization_key(param.get('description', '')):
                param_schema['localization_issues'].append('description_is_key')

        # Decode protobuf if requested
        if include_protobuf and param.get('typeInstance'):
            param_schema['type_info'] = analyze_type_instance_blob(param['typeInstance'])

        # Enrich with type information
        if include_type_info:
            param_schema['type_details'] = []
            for type_id in param_schema['accepted_types']:
                type_details = get_type_details(conn, type_id)
                if type_details:
                    param_schema['type_details'].append(type_details)

        schema['parameters'].append(param_schema)

    # Output types
    schema['output_types'] = get_action_output_types(conn, tool_id)

    # Categories
    schema['categories'] = get_action_categories(conn, tool_id, locale)

    # Keywords
    schema['keywords'] = get_action_keywords(conn, tool_id, locale)

    return schema


def build_type_schema(
    conn: sqlite3.Connection,
    type_data: Dict[str, Any],
    locale: str = "en"
) -> Dict[str, Any]:
    """
    Build a complete schema for a type.

    Args:
        conn: Database connection
        type_data: Type data from get_type_info()
        locale: Language locale

    Returns:
        Complete type schema
    """
    type_id = type_data['rowId']

    # Map kind to human-readable names
    kind_names = {
        1: 'primitive',
        2: 'entity',
        3: 'enum',
        4: 'object',
        6: 'array',
        8: 'special',
    }

    schema = {
        'id': type_id,
        'name': type_data.get('name'),
        'name_with_determiner': type_data.get('nameWithDeteriner'),
        'kind': type_data.get('kind'),
        'kind_name': kind_names.get(type_data.get('kind'), 'unknown'),
        'runtime_flags': type_data.get('runtimeFlags'),
        'container_id': type_data.get('container_id'),
    }

    # Entity properties (for kind=2)
    if type_data.get('kind') == 2:
        schema['properties'] = get_entity_properties(conn, type_id, locale)

    # Enum cases (for kind=3)
    if type_data.get('kind') == 3:
        schema['enum_cases'] = get_enum_cases(conn, type_id, locale)

    return schema


def build_compatibility_entry(
    source_action: Dict[str, Any],
    target_action: Dict[str, Any],
    connecting_type: str
) -> Dict[str, Any]:
    """
    Build a compatibility entry showing two actions can connect.

    Args:
        source_action: Source action schema
        target_action: Target action schema
        connecting_type: Type that connects them

    Returns:
        Compatibility entry
    """
    return {
        'source': {
            'id': source_action['id'],
            'name': source_action.get('name'),
        },
        'target': {
            'id': target_action['id'],
            'name': target_action.get('name'),
        },
        'connecting_type': connecting_type,
        'description': f"{source_action.get('name')} → {target_action.get('name')} via {connecting_type}"
    }


def classify_action_visibility(visibility_flags: int) -> Dict[str, Any]:
    """
    Classify action visibility level.

    Args:
        visibility_flags: Visibility flags from Tools table

    Returns:
        Classification dictionary
    """
    classifications = {
        0: {
            'level': 'public',
            'description': 'Fully visible and documented',
            'likely_documented': True,
        },
        2: {
            'level': 'somewhat_hidden',
            'description': 'May have limited visibility',
            'likely_documented': True,
        },
        3: {
            'level': 'hidden',
            'description': 'Hidden from normal browsing',
            'likely_documented': False,
        },
        5: {
            'level': 'restricted',
            'description': 'Restricted access',
            'likely_documented': False,
        },
        7: {
            'level': 'very_hidden',
            'description': 'Very hidden, possibly internal',
            'likely_documented': False,
        },
        13: {
            'level': 'experimental',
            'description': 'Experimental or beta feature',
            'likely_documented': False,
        },
        15: {
            'level': 'maximum_hidden',
            'description': 'Maximally hidden, likely internal-only',
            'likely_documented': False,
        },
    }

    return classifications.get(visibility_flags, {
        'level': 'unknown',
        'description': f'Unknown visibility level ({visibility_flags})',
        'likely_documented': False,
    })


def summarize_action_collection(actions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Generate summary statistics for a collection of actions.

    Args:
        actions: List of action schemas

    Returns:
        Summary statistics
    """
    summary = {
        'total_count': len(actions),
        'by_type': {},
        'by_visibility': {},
        'by_app': {},
        'hidden_count': 0,
        'deprecated_count': 0,
        'with_parameters': 0,
        'parameter_count': 0,
    }

    for action in actions:
        # By type
        action_type = action.get('type', 'unknown')
        summary['by_type'][action_type] = summary['by_type'].get(action_type, 0) + 1

        # By visibility
        vis_flags = action.get('visibility_flags', 0)
        summary['by_visibility'][vis_flags] = summary['by_visibility'].get(vis_flags, 0) + 1

        # By app
        app_name = action.get('app', {}).get('name', 'Unknown')
        summary['by_app'][app_name] = summary['by_app'].get(app_name, 0) + 1

        # Hidden count
        if action.get('hidden'):
            summary['hidden_count'] += 1

        # Deprecated count
        if action.get('deprecation'):
            summary['deprecated_count'] += 1

        # Parameters
        params = action.get('parameters', [])
        if params:
            summary['with_parameters'] += 1
            summary['parameter_count'] += len(params)

    return summary
