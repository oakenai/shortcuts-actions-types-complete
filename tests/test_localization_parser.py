"""Unit tests for localization parser"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.localization_parser import (
    is_localization_key,
    get_localization_key_confidence,
    camel_case_to_title,
    constant_to_title,
    parse_localization_key,
    clean_embedded_keys,
    generate_readable_name,
)


def test_is_localization_key():
    """Test localization key detection"""
    # Should detect as keys
    assert is_localization_key("photos_IncreaseWarmth_1.0.0_intent_title")
    assert is_localization_key("browser_SearchableWebsiteEntity_1.0.0_entity_type_display_representation")
    assert is_localization_key("CONTROL_CENTER_TOGGLE_RECORDING_INTENT_TITLE")
    assert is_localization_key("browser_SearchWebsiteIntent_1.0.0_intent_parameter_website_description")

    # Should NOT detect as keys
    assert not is_localization_key("Increase Warmth")
    assert not is_localization_key("Find Contact")
    assert not is_localization_key("brightness")
    assert not is_localization_key("")
    assert not is_localization_key(None)

    print("✅ test_is_localization_key passed")


def test_confidence_scoring():
    """Test confidence scoring for keys"""
    # High confidence keys
    assert get_localization_key_confidence("photos_IncreaseWarmth_1.0.0_intent_title") > 0.8
    assert get_localization_key_confidence("browser_SearchableWebsiteEntity_1.0.0_entity_type_display_representation") > 0.8

    # Medium confidence
    assert 0.5 < get_localization_key_confidence("some_long_key_with_many_underscores_description") < 0.9

    # Low confidence (not keys)
    assert get_localization_key_confidence("Increase Warmth") < 0.3
    assert get_localization_key_confidence("brightness") < 0.3

    print("✅ test_confidence_scoring passed")


def test_camel_case_to_title():
    """Test camelCase to Title Case conversion"""
    assert camel_case_to_title("IncreaseWarmth") == "Increase Warmth"
    assert camel_case_to_title("SearchableWebsiteEntity") == "Searchable Website Entity"
    assert camel_case_to_title("URLHandler") == "URL Handler"
    assert camel_case_to_title("HTMLParser") == "HTML Parser"
    assert camel_case_to_title("createFolder") == "Create Folder"
    assert camel_case_to_title("") == ""

    print("✅ test_camel_case_to_title passed")


def test_constant_to_title():
    """Test CONSTANT_CASE to Title Case conversion"""
    assert constant_to_title("CONTROL_CENTER_TOGGLE_RECORDING_INTENT_TITLE") == "Control Center Toggle Recording"
    assert constant_to_title("URL_HANDLER") == "URL Handler"
    assert constant_to_title("SIMPLE_INTENT_TITLE") == "Simple"

    print("✅ test_constant_to_title passed")


def test_parse_version_based_keys():
    """Test parsing version-based localization keys"""
    result = parse_localization_key("photos_IncreaseWarmth_1.0.0_intent_title")

    assert result['is_key'] == True
    assert result['pattern_type'] == 'version_based'
    assert result['extracted_name'] == "Increase Warmth"
    assert result['confidence'] >= 0.9
    assert result['components']['entity'] == 'IncreaseWarmth'
    assert result['components']['version'] == '1.0.0'

    print("✅ test_parse_version_based_keys passed")


def test_parse_entity_type_keys():
    """Test parsing entity type localization keys"""
    result = parse_localization_key("browser_SearchableWebsiteEntity_1.0.0_entity_type_display_representation")

    assert result['is_key'] == True
    assert result['pattern_type'] == 'entity_type'
    assert "Searchable Website" in result['extracted_name']
    assert result['confidence'] >= 0.9
    assert result['components']['entity'] == 'SearchableWebsiteEntity'

    print("✅ test_parse_entity_type_keys passed")


def test_parse_constant_case_keys():
    """Test parsing constant case keys"""
    result = parse_localization_key("CONTROL_CENTER_TOGGLE_RECORDING_INTENT_TITLE")

    assert result['is_key'] == True
    assert result['pattern_type'] == 'constant_case'
    assert "Control Center Toggle Recording" in result['extracted_name']
    assert result['confidence'] >= 0.85

    print("✅ test_parse_constant_case_keys passed")


def test_parse_parameter_keys():
    """Test parsing parameter description keys"""
    result = parse_localization_key("browser_SearchWebsiteIntent_1.0.0_intent_parameter_website_description")

    assert result['is_key'] == True
    assert result['pattern_type'] == 'parameter_description'
    assert result['components']['parameter'] == 'website'
    assert result['confidence'] >= 0.85

    print("✅ test_parse_parameter_keys passed")


def test_clean_embedded_keys():
    """Test cleaning embedded keys from text"""
    input_text = "Optionally, what to sort the browser_searchablewebsiteentity_1.0.0_entity_type_display_representation by."
    output = clean_embedded_keys(input_text)

    assert "browser_searchablewebsiteentity" not in output.lower()
    # Allow for both "searchable website" or "searchablewebsite" (lowercase entity handling)
    assert ("searchable website" in output.lower() or "searchablewebsite" in output.lower())
    assert "Optionally" in output
    assert "by." in output

    print("✅ test_clean_embedded_keys passed")


def test_generate_readable_name():
    """Test main function for generating readable names"""
    # Test with version-based key
    result = generate_readable_name("photos_IncreaseWarmth_1.0.0_intent_title")
    assert result['value'] == "Increase Warmth"
    assert result['is_synthetic'] == True
    assert result['confidence'] >= 0.9
    assert result['source'] == 'parsed_key'
    assert result['original_key'] == "photos_IncreaseWarmth_1.0.0_intent_title"

    # Test with non-key (should return as-is)
    result = generate_readable_name("Increase Warmth")
    assert result['value'] == "Increase Warmth"
    assert result['is_synthetic'] == False
    assert result['source'] == 'original'

    # Test with embedded key
    result = generate_readable_name("Sort by browser_searchablewebsiteentity_1.0.0_entity_type_display_representation")
    assert result['is_synthetic'] == True
    assert ("searchable website" in result['value'].lower() or "searchablewebsite" in result['value'].lower())
    assert result['source'] == 'cleaned_embedded'

    print("✅ test_generate_readable_name passed")


def test_real_world_cases():
    """Test against actual problematic cases from the database"""
    # Test cases from the validation report

    # Case 1: Safari entity
    result = generate_readable_name("browser_SearchableWebsiteEntity_1.0.0_entity_type_display_representation")
    assert result['is_synthetic'] == True
    assert "Searchable Website" in result['value']

    # Case 2: Constant case
    result = generate_readable_name("CONTROL_CENTER_TOGGLE_RECORDING_INTENT_TITLE")
    assert result['is_synthetic'] == True
    assert "Control Center" in result['value']

    # Case 3: Parameter description with embedded key
    text = "Optionally, what to sort the browser_searchablewebsiteentity_1.0.0_entity_type_display_representation by."
    result = generate_readable_name(text)
    assert result['is_synthetic'] == True
    assert "browser_searchablewebsiteentity" not in result['value'].lower()

    print("✅ test_real_world_cases passed")


if __name__ == "__main__":
    test_is_localization_key()
    test_confidence_scoring()
    test_camel_case_to_title()
    test_constant_to_title()
    test_parse_version_based_keys()
    test_parse_entity_type_keys()
    test_parse_constant_case_keys()
    test_parse_parameter_keys()
    test_clean_embedded_keys()
    test_generate_readable_name()
    test_real_world_cases()

    print("\n✨ All tests passed!")
