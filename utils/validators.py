"""Validation utilities for checking data quality"""

from typing import Dict, Any, List
import re
from .localization_parser import (
    is_localization_key as parser_is_localization_key,
    get_localization_key_confidence
)


def is_localization_key(text: str) -> bool:
    """
    Check if text is a localization key rather than actual localized text.

    Uses the enhanced localization parser for better detection.

    Args:
        text: Text to check

    Returns:
        True if this looks like a localization key
    """
    # Use the enhanced parser's detection
    return parser_is_localization_key(text)


def validate_action_schema(schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate an action schema and return validation results.

    Args:
        schema: Action schema to validate

    Returns:
        Dictionary with validation results
    """
    issues = []
    warnings = []

    # Check for synthetic localizations (warnings) or missing localizations (errors)
    name_metadata = schema.get('name_metadata', {})
    if name_metadata.get('is_synthetic'):
        warnings.append({
            'field': 'name',
            'issue': 'synthetic_localization',
            'confidence': name_metadata.get('confidence', 0.0),
            'original_key': name_metadata.get('original_key'),
            'message': f"Name was derived from key: {name_metadata.get('original_key')}"
        })
    elif is_localization_key(schema.get('name', '')):
        # Only flag as error if not already fixed
        issues.append({
            'field': 'name',
            'issue': 'missing_localization',
            'value': schema.get('name'),
            'message': f"Action name appears to be a localization key: {schema.get('name')}"
        })

    desc_metadata = schema.get('description_metadata', {})
    if desc_metadata.get('is_synthetic'):
        warnings.append({
            'field': 'description_summary',
            'issue': 'synthetic_localization',
            'confidence': desc_metadata.get('confidence', 0.0),
            'original_key': desc_metadata.get('original_key'),
            'message': f"Description was derived from key: {desc_metadata.get('original_key')}"
        })
    elif is_localization_key(schema.get('description_summary', '')):
        issues.append({
            'field': 'description_summary',
            'issue': 'missing_localization',
            'value': schema.get('description_summary'),
            'message': f"Description appears to be a localization key: {schema.get('description_summary')}"
        })

    # Check parameters
    for i, param in enumerate(schema.get('parameters', [])):
        param_name_metadata = param.get('name_metadata', {})
        if param_name_metadata.get('is_synthetic'):
            warnings.append({
                'field': f'parameters[{i}].name',
                'issue': 'synthetic_localization',
                'confidence': param_name_metadata.get('confidence', 0.0),
                'original_key': param_name_metadata.get('original_key'),
                'message': f"Parameter name derived from key"
            })
        elif is_localization_key(param.get('name', '')):
            issues.append({
                'field': f'parameters[{i}].name',
                'issue': 'missing_localization',
                'value': param.get('name'),
                'message': f"Parameter name is localization key: {param.get('name')}"
            })

        param_desc_metadata = param.get('description_metadata', {})
        if param_desc_metadata.get('is_synthetic'):
            warnings.append({
                'field': f'parameters[{i}].description',
                'issue': 'synthetic_localization',
                'confidence': param_desc_metadata.get('confidence', 0.0),
                'original_key': param_desc_metadata.get('original_key'),
                'message': f"Parameter description derived from key"
            })
        elif is_localization_key(param.get('description', '')):
            issues.append({
                'field': f'parameters[{i}].description',
                'issue': 'missing_localization',
                'value': param.get('description'),
                'message': f"Parameter description is localization key: {param.get('description')}"
            })

        # Check for complex type identifiers
        for type_id in param.get('accepted_types', []):
            if is_complex_type_identifier(type_id):
                warnings.append({
                    'field': f'parameters[{i}].accepted_types',
                    'issue': 'complex_type',
                    'value': type_id,
                    'message': f"Complex type identifier (may need type info lookup): {type_id}"
                })

    # Check if action is hidden but has no name
    if schema.get('hidden') and not schema.get('name'):
        warnings.append({
            'field': 'name',
            'issue': 'hidden_no_name',
            'message': 'Hidden action with no localized name'
        })

    return {
        'valid': len(issues) == 0,
        'issues': issues,
        'warnings': warnings,
        'quality_score': calculate_quality_score(schema, issues, warnings)
    }


def is_complex_type_identifier(type_id: str) -> bool:
    """
    Check if a type identifier is complex (contains namespace/app info).

    Examples of complex types:
    - com.apple.shortcuts.com.agiletortoise.Drafts4.addto.DraftsAddMode
    - com.apple.Music.LibraryItemEntity

    Args:
        type_id: Type identifier

    Returns:
        True if complex
    """
    if not type_id:
        return False

    # Has multiple dots and starts with com.apple
    if type_id.startswith('com.apple.') and type_id.count('.') >= 3:
        return True

    # Contains app-specific namespace
    if 'shortcuts.com.' in type_id:
        return True

    return False


def parse_type_identifier(type_id: str) -> Dict[str, Any]:
    """
    Parse a type identifier to extract its components.

    Examples:
    - com.apple.shortcuts.com.agiletortoise.Drafts4.addto.DraftsAddMode
      → namespace: com.apple.shortcuts
      → third_party_bundle: com.agiletortoise.Drafts4
      → type_name: DraftsAddMode
      → category: addto

    Args:
        type_id: Type identifier

    Returns:
        Parsed components
    """
    result = {
        'full_id': type_id,
        'namespace': None,
        'bundle_id': None,
        'third_party_bundle': None,
        'type_name': None,
        'category': None,
        'is_third_party': False,
        'is_enum': False,
        'is_entity': False,
    }

    if not type_id:
        return result

    # Check if it's a third-party type wrapped by Shortcuts
    # Pattern: com.apple.shortcuts.{original_bundle_id}.{rest}
    if type_id.startswith('com.apple.shortcuts.com.'):
        result['namespace'] = 'com.apple.shortcuts'
        result['is_third_party'] = True

        # Extract third-party bundle
        remainder = type_id[len('com.apple.shortcuts.'):]
        parts = remainder.split('.')

        # Try to find the bundle ID (usually first 3-4 parts)
        if len(parts) >= 3:
            # Check if it's like com.agiletortoise.Drafts4
            possible_bundle = '.'.join(parts[:3])
            result['third_party_bundle'] = possible_bundle

            # Rest is type name and category
            if len(parts) > 3:
                result['category'] = '.'.join(parts[3:-1]) if len(parts) > 4 else parts[3]
                result['type_name'] = parts[-1]

    elif type_id.startswith('com.apple.'):
        result['namespace'] = 'com.apple'
        parts = type_id.split('.')

        # Extract bundle (e.g., com.apple.Music)
        if len(parts) >= 3:
            result['bundle_id'] = '.'.join(parts[:3])
            result['type_name'] = parts[-1]

            if len(parts) > 3:
                result['category'] = '.'.join(parts[3:-1])

    else:
        # Simple type
        result['type_name'] = type_id

    # Detect type kind from naming
    if result['type_name']:
        if 'Entity' in result['type_name']:
            result['is_entity'] = True
        elif 'Mode' in result['type_name'] or 'Option' in result['type_name']:
            result['is_enum'] = True

    return result


def calculate_quality_score(schema: Dict[str, Any], issues: List[Dict], warnings: List[Dict]) -> float:
    """
    Calculate quality score (0-100) for a schema.

    Args:
        schema: Action schema
        issues: List of issues found
        warnings: List of warnings found

    Returns:
        Score from 0-100
    """
    score = 100.0

    # Deduct heavily for real issues
    score -= len(issues) * 10

    # Deduct less for warnings, with diminishing returns
    # Count warnings by type
    complex_type_warnings = sum(1 for w in warnings if w.get('issue') == 'complex_type')
    synthetic_loc_warnings = sum(1 for w in warnings if w.get('issue') == 'synthetic_localization')
    other_warnings = len(warnings) - complex_type_warnings - synthetic_loc_warnings

    # Cap complex type penalty at 20 points max (not 5 × count)
    # Home automation actions have many complex types, which is normal
    score -= min(20, complex_type_warnings * 2)

    # Synthetic localizations are informational, small penalty
    score -= synthetic_loc_warnings * 2

    # Other warnings get normal penalty
    score -= other_warnings * 5

    # Bonus for having description (check metadata for synthetic)
    desc_metadata = schema.get('description_metadata', {})
    if schema.get('description_summary') and (desc_metadata.get('is_synthetic') or not is_localization_key(schema.get('description_summary', ''))):
        score += 5

    # Bonus for parameters
    if schema.get('parameters'):
        score += 5

    # Bonus for categories
    if schema.get('categories'):
        score += 5

    return max(0.0, min(100.0, score))


def generate_validation_report(schemas: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Generate validation report for a collection of schemas.

    Args:
        schemas: List of action schemas

    Returns:
        Validation report
    """
    report = {
        'total_schemas': len(schemas),
        'valid_schemas': 0,
        'schemas_with_issues': 0,
        'schemas_with_warnings': 0,
        'issues_by_type': {},
        'warnings_by_type': {},
        'quality_scores': {
            'excellent': 0,  # 90-100
            'good': 0,       # 75-89
            'fair': 0,       # 60-74
            'poor': 0,       # <60
        },
        'average_quality': 0.0,
        'problematic_actions': [],
    }

    total_quality = 0.0

    for schema in schemas:
        validation = validate_action_schema(schema)

        if validation['valid']:
            report['valid_schemas'] += 1
        else:
            report['schemas_with_issues'] += 1

        if validation['warnings']:
            report['schemas_with_warnings'] += 1

        # Count issues by type
        for issue in validation['issues']:
            issue_type = issue['issue']
            report['issues_by_type'][issue_type] = report['issues_by_type'].get(issue_type, 0) + 1

        # Count warnings by type
        for warning in validation['warnings']:
            warning_type = warning['issue']
            report['warnings_by_type'][warning_type] = report['warnings_by_type'].get(warning_type, 0) + 1

        # Quality score
        quality = validation['quality_score']
        total_quality += quality

        if quality >= 90:
            report['quality_scores']['excellent'] += 1
        elif quality >= 75:
            report['quality_scores']['good'] += 1
        elif quality >= 60:
            report['quality_scores']['fair'] += 1
        else:
            report['quality_scores']['poor'] += 1
            # Track problematic actions
            if len(report['problematic_actions']) < 20:
                report['problematic_actions'].append({
                    'id': schema.get('id'),
                    'name': schema.get('name'),
                    'quality': quality,
                    'issues': len(validation['issues']),
                    'warnings': len(validation['warnings']),
                })

    report['average_quality'] = total_quality / len(schemas) if schemas else 0.0

    return report
