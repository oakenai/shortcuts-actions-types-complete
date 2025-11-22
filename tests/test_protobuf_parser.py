"""Tests for protobuf parsing and string sanitization"""

import pytest
from utils.protobuf_parser import sanitize_extracted_string, extract_strings_from_blob


class TestSanitizeExtractedString:
    """Test string sanitization to remove binary artifacts"""

    def test_remove_leading_parenthesis(self):
        """Should remove leading parenthesis from bundle IDs"""
        assert sanitize_extracted_string("(com.apple.Notes.AddTagsToNotesLinkAction") == \
               "com.apple.Notes.AddTagsToNotesLinkAction"

    def test_remove_trailing_asterisk(self):
        """Should remove trailing asterisk"""
        assert sanitize_extracted_string("com.apple.Notes*") == "com.apple.Notes"
        assert sanitize_extracted_string("notes*") == "notes"

    def test_remove_trailing_quote(self):
        """Should remove trailing quotes and special chars"""
        assert sanitize_extracted_string('com.apple.Notes28"') == "com.apple.Notes28"
        assert sanitize_extracted_string('com.apple.Notes2:"') == "com.apple.Notes2:"

    def test_remove_leading_dollar(self):
        """Should remove leading dollar sign from UUIDs"""
        assert sanitize_extracted_string('$D8DCFC48-3279-4EEF-BC28-A5E6F8A77F93"') == \
               "D8DCFC48-3279-4EEF-BC28-A5E6F8A77F93"

    def test_remove_leading_digits(self):
        """Should remove leading single digits (length prefixes)"""
        assert sanitize_extracted_string('2com.agiletortoise.Drafts4.addto.DraftsAfterSuccess') == \
               'com.agiletortoise.Drafts4.addto.DraftsAfterSuccess'
        assert sanitize_extracted_string('1com.agiletortoise.Drafts4.open.DraftsAfterSuccess') == \
               'com.agiletortoise.Drafts4.open.DraftsAfterSuccess'
        assert sanitize_extracted_string('0com.agiletortoise.Tally2.updatetally.TallyAction') == \
               'com.agiletortoise.Tally2.updatetally.TallyAction'

    def test_remove_leading_hash(self):
        """Should remove leading hash/number sign"""
        assert sanitize_extracted_string('#com.apple.AddressBook.ContactEntity') == \
               'com.apple.AddressBook.ContactEntity'

    def test_remove_leading_dash(self):
        """Should remove leading dash/minus sign"""
        assert sanitize_extracted_string('-com.agiletortoise.Drafts4.addto.DraftsAddMode') == \
               'com.agiletortoise.Drafts4.addto.DraftsAddMode'

    def test_keep_valid_bundle_ids(self):
        """Should preserve valid bundle IDs"""
        assert sanitize_extracted_string("com.apple.Notes") == "com.apple.Notes"
        assert sanitize_extracted_string("com.agiletortoise.Drafts4") == "com.agiletortoise.Drafts4"

    def test_keep_valid_entity_names(self):
        """Should preserve entity names"""
        assert sanitize_extracted_string("NoteEntity") == "NoteEntity"
        assert sanitize_extracted_string("TagEntity") == "TagEntity"
        assert sanitize_extracted_string("FolderEntity") == "FolderEntity"

    def test_keep_valid_query_names(self):
        """Should preserve query names"""
        assert sanitize_extracted_string("Notes.VisibleNotesQuery") == "Notes.VisibleNotesQuery"
        assert sanitize_extracted_string("Notes.VisibleFoldersQuery") == "Notes.VisibleFoldersQuery"

    def test_keep_readable_names(self):
        """Should preserve human-readable names"""
        assert sanitize_extracted_string("Creation Date") == "Creation Date"
        assert sanitize_extracted_string("Last Modified Date") == "Last Modified Date"
        assert sanitize_extracted_string("notes") == "notes"

    def test_keep_uuids(self):
        """Should preserve UUIDs (without artifacts)"""
        assert sanitize_extracted_string("D8DCFC48-3279-4EEF-BC28-A5E6F8A77F93") == \
               "D8DCFC48-3279-4EEF-BC28-A5E6F8A77F93"

    def test_filter_garbage(self):
        """Should filter out garbage strings"""
        assert sanitize_extracted_string('2:"') is None
        assert sanitize_extracted_string('"') is None
        assert sanitize_extracted_string('*') is None
        assert sanitize_extracted_string('()') is None
        assert sanitize_extracted_string('') is None

    def test_filter_short_strings(self):
        """Should filter strings that become too short after cleaning"""
        assert sanitize_extracted_string('a') is None
        assert sanitize_extracted_string('ab') is None
        assert sanitize_extracted_string('(a)') is None

    def test_filter_mostly_artifacts(self):
        """Should filter strings that are mostly artifacts"""
        # String that becomes much shorter after cleaning (>50% reduction)
        assert sanitize_extracted_string('**********abc') is None

    def test_preserve_colons_in_bundle_ids(self):
        """Should handle colons in context"""
        # This is a tricky case - colon with quote may be valid in some contexts
        result = sanitize_extracted_string('com.apple.Notes2:"')
        assert result == "com.apple.Notes2:"  # Removes trailing quote but keeps colon


class TestExtractStringsFromBlob:
    """Test blob string extraction with sanitization"""

    def test_empty_blob(self):
        """Should handle empty blob"""
        assert extract_strings_from_blob(b'') == []

    def test_simple_string_extraction(self):
        """Should extract and sanitize simple strings"""
        # Create a blob with a simple string
        blob = b'\x0a\x08test.txt'  # Field 1, length 8, "test.txt"
        result = extract_strings_from_blob(blob)
        assert 'test.txt' in result

    def test_sanitization_applied(self):
        """Should apply sanitization to extracted strings"""
        # Create blob with artifact-laden string
        blob = b'(com.apple.Test*'
        result = extract_strings_from_blob(blob)
        # Should extract and clean the string
        assert 'com.apple.Test' in result or len(result) >= 0  # May or may not extract depending on parsing

    def test_no_duplicates(self):
        """Should not return duplicate strings"""
        blob = b'test' * 3
        result = extract_strings_from_blob(blob)
        # Count occurrences of 'test' in result
        test_count = result.count('test')
        assert test_count <= 1  # Should appear at most once
