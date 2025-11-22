# Shortcuts Reverse Engineering Toolkit

A comprehensive Python toolkit for extracting, decoding, and documenting Apple Shortcuts actions from the `Tools-prod.sqlite` database.

> **⚠️ Educational & Research Use Only**
> This toolkit is for educational and research purposes. It analyzes the Shortcuts database from your own Mac without modifying any Apple software. See [Disclaimer & Legal](#️-disclaimer--legal) for full details.

## 🚀 Quick Start

```bash
# 1. Copy the database from your system
cp ~/Library/Shortcuts/ToolKit/Tools-active ./Tools-prod.sqlite

# 2. Run setup
./setup.sh

# 3. Extract all actions
source venv/bin/activate
python3 extract_shortcuts_actions.py --all -v

# Done! Check output/actions_complete.json
```

## 🎯 What This Does

This toolkit reverse engineers Apple's Shortcuts database to:

- **Extract all 1,813 Shortcuts actions** with complete metadata
- **Fix localization issues automatically** - Smart parsing converts keys to readable text
- **Discover 1,627 hidden actions** (90% of all actions, including Image Playground!)
- **Decode protobuf BLOBs** to extract type information, UTIs, and requirements
- **Document parameters** with descriptions and type constraints
- **Analyze 2,823 data types** including entities, enums, and primitives
- **Validate output quality** with comprehensive quality scoring (99.7/100 average)
- **Generate JSON/CSV exports** for programmatic access

## 🔍 Key Discoveries

### Localization Fix

Automatically fixes 39 localization issues where keys appeared instead of readable text:

**Before**: `browser_SearchableWebsiteEntity_1.0.0_entity_type_display_representation`
**After**: `searchable website` (with metadata tracking)

- ✅ **100% valid** schemas (was 98%)
- ✅ **0 localization errors** (was 39)
- ✅ **99.7/100** average quality score (was 97.4)
- 📝 Original keys preserved in metadata for transparency

### Hidden Actions Found

- **1,627 hidden actions total** (90% of all actions!)
- **181 maximally hidden actions** (visibilityFlags=15):
  - `com.apple.GenerativePlaygroundApp.GenerateImageIntent` - Create images with Image Playground
  - Internal Notes actions (CreateFolder, AddTag, MoveNotes, etc.)
  - Hidden Photos actions (SetLibraryView, etc.)
  - MobileSMS internal actions

- **2 experimental actions** (visibilityFlags=13):
  - Voice Memos settings access
  - News settings access

### Protobuf Decoding Success

Successfully extracts from binary BLOBs:
- **UTI types** (e.g., "public.folder", "public.image")
- **OS version requirements**
- **Type schemas** and constraints
- **Embedded strings** and identifiers

## 📦 Installation

### Prerequisites

- Python 3.11+
- macOS with Shortcuts app (for database access)

### Setup

```bash
# Clone or download this repository
cd shortcuts-actions-types-complete

# Copy the Tools-prod database from your system
# The file name includes a version number (e.g., v61) and a UUID
# Method 1: Copy via the Tools-active symlink (recommended)
cp ~/Library/Shortcuts/ToolKit/Tools-active ./Tools-prod.sqlite

# Method 2: Copy the versioned file directly (if symlink doesn't work)
cp ~/Library/Shortcuts/ToolKit/Tools-prod.v*.sqlite ./Tools-prod.sqlite

# Verify the database was copied
ls -lh Tools-prod.sqlite

# Run setup script (creates venv, installs dependencies)
./setup.sh

# Or manually:
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**Note about the database file:**
- The actual filename is `Tools-prod.v[VERSION]-[UUID].sqlite`
  - Example: `Tools-prod.v61-F145B045-4246-431B-A407-EFC6E6AAA0B2.sqlite`
- The version number (e.g., `v61`) corresponds to your macOS version
- There's a symlink `Tools-active` that always points to the current active database
- The database has companion files (`.sqlite-shm`, `.sqlite-wal`, `.sqlite.lock`) for Write-Ahead Logging
- **Important:** Only copy the main `.sqlite` file, not the WAL files (they're for active transactions)
- The scripts expect the file to be renamed to simply `Tools-prod.sqlite` in the project directory

## 🚀 Usage

### Extract All Actions

```bash
# Activate virtual environment
source venv/bin/activate

# Extract all 1,813 actions with full details (localization fixing enabled by default)
python3 extract_shortcuts_actions.py --all -v

# Output: output/actions_complete.json (detailed schemas)
```

### Disable Localization Fixing

```bash
# If you want raw localization keys instead of readable text
python3 extract_shortcuts_actions.py --all --no-fix-localizations

# Useful for debugging or comparing with original data
```

### Extract Hidden Actions Only

```bash
python3 extract_shortcuts_actions.py --hidden

# Output: output/hidden_actions.json
```

### Quick Extract (No Protobuf - Faster)

```bash
python3 extract_shortcuts_actions.py --all --no-protobuf

# ~10x faster, still gets all text metadata and localization fixes
```

### Export to CSV

```bash
python3 extract_shortcuts_actions.py --all --csv

# Output: output/actions_complete.csv (1,813 rows)
```

### Find Hidden Actions

```bash
# Show all hidden actions grouped by visibility level
python3 find_hidden_actions.py

# Show only experimental actions (flags 13-15)
python3 find_hidden_actions.py --experimental

# Show details for specific action
python3 find_hidden_actions.py --details "com.apple.GenerativePlaygroundApp.GenerateImageIntent"
```

### Analyze Types

```bash
# Extract all 2,823 types with usage statistics
python3 analyze_types.py --all -v

# Output: output/types_complete.json

# Extract only enum types
python3 analyze_types.py --enums --export output/enums.json

# Analyze specific type
python3 analyze_types.py --type "com.apple.shortcuts.com.agiletortoise.Drafts4.addto.DraftsAddMode"
```

### Validate Output Quality

```bash
# Validate extracted actions and generate quality report
python3 validate_output.py --report output/validation_report.json --show-issues

# Shows:
# - Quality scores (0-100)
# - Localization issues
# - Complex type warnings
# - Problematic actions
```

### Decode Protobuf BLOBs

```bash
# Decode BLOBs for specific action
python3 decode_protobuf_fields.py --action "is.workflow.actions.file.createfolder"

# Decode all parameter typeInstance BLOBs
python3 decode_protobuf_fields.py --all-params --limit 100

# Decode all requirements BLOBs
python3 decode_protobuf_fields.py --all-requirements --export output/protobuf_decoded
```

## 📊 Output Format

### Action Schema (JSON)

```json
{
  "id": "is.workflow.actions.file.createfolder",
  "name": "Create Folder",
  "name_metadata": {
    "is_synthetic": false
  },
  "description_summary": "Creates a new folder...",
  "description_metadata": {
    "is_synthetic": false
  },
  "type": "action",
  "visibility_flags": 15,
  "hidden": true,
  "app": {
    "bundle_id": "com.apple.shortcuts",
    "name": "Shortcuts"
  },
  "parameters": [
    {
      "key": "WFFilePath",
      "name": "Path",
      "name_metadata": {
        "is_synthetic": false
      },
      "description": "The path of the folder",
      "description_metadata": {
        "is_synthetic": false
      },
      "accepted_types": ["string"],
      "type_info": {
        "uti_types": ["public.folder"],
        "strings": ["public.folder"]
      },
      "localization_issues": []
    }
  ],
  "output_types": ["file"],
  "categories": ["Files"],
  "keywords": ["create", "folder", "directory"],
  "localization_issues": []
}
```

### Synthetic Localization Example

When a localization key is automatically fixed:

```json
{
  "id": "com.apple.Safari.QuickWebsiteSearchProviderEntity",
  "name": "Find searchable website",
  "name_metadata": {
    "is_synthetic": true,
    "original_key": "Find browser_SearchableWebsiteEntity_1.0.0_entity_type_display_representation",
    "confidence": 0.85,
    "source": "cleaned_embedded"
  }
}
```

The `name_metadata` field shows:
- `is_synthetic`: Whether the text was generated from a localization key
- `original_key`: The original localization key for reference
- `confidence`: Parsing confidence score (0.0-1.0)
- `source`: How the text was generated (`parsed_key`, `cleaned_embedded`, etc.)

### Understanding Protobuf `type_info` Fields

Each parameter includes a `type_info` field with protobuf data extracted from the database:

```json
{
  "type_info": {
    "size": 171,
    "uti_types": [
      "com.agiletortoise.Drafts4.addto.DraftsAddMode"
    ],
    "strings": [
      "Create",
      "com.apple.shortcuts"
    ],
    "decoded": {
      "raw_size": 171,
      "fields": {
        "field_3_bytes": "0a480a4612440a13636f6d..."
      }
    }
  }
}
```

**What each field means:**

| Field | Description |
|-------|-------------|
| `size` | Total protobuf BLOB size in bytes |
| `uti_types` | **Extracted** UTI/bundle identifiers found in the BLOB |
| `strings` | **Extracted** human-readable strings found in the BLOB |
| `decoded.fields` | Raw protobuf wire format data (hex-encoded) |
| `field_X_bytes` | Data from protobuf field number X, stored as hex when it's a complex nested structure |

**Why `field_X_bytes` exists:**

Since Apple doesn't provide `.proto` schema files, the toolkit uses **best-effort reverse engineering**:
- ✅ **Successfully extracts**: UTF-8 strings, UTI types, bundle IDs (stored in `uti_types` and `strings`)
- ✅ **Successfully extracts**: Simple numbers (varints)
- ⚠️ **Partially extracts**: Complex nested protobuf messages (stored as hex in `field_X_bytes` for transparency)

**Practical usage:**
```python
# Use the extracted data (immediately useful)
uti_types = param["type_info"]["uti_types"]
strings = param["type_info"]["strings"]

# Ignore the hex fields (for debugging/advanced use only)
# field_X_bytes → raw protobuf data for potential future decoding
```

The toolkit extracts ~60% of useful type information without needing Apple's schema definitions, using [protobuf wire format parsing](https://protobuf.dev/programming-guides/encoding/).

## 📁 Example Output

The `example-output/` directory contains pre-generated extraction results so you can explore the data without running the scripts:

- **`actions_complete.json`** (8.6 MB) - Complete extraction of all 1,813 actions with full metadata, parameters, and protobuf type information
- **`types_complete.json`** (2.3 MB) - All 2,823 data types with usage statistics and enum values

These files demonstrate the full capabilities of the toolkit and can be used for:
- Exploring the Shortcuts action catalog
- Understanding the data structure before running extraction
- Cross-referencing actions and types
- Building tools without database access

## 🛠️ Project Structure

```
shortcuts-actions-types-complete/
├── extract_shortcuts_actions.py    # Main extraction script
├── find_hidden_actions.py          # Hidden action discovery
├── analyze_types.py                # Type system analyzer
├── validate_output.py              # Output quality validator
├── decode_protobuf_fields.py       # Protobuf BLOB decoder
├── utils/
│   ├── db_utils.py                 # Database utilities (15+ query functions)
│   ├── protobuf_parser.py          # Protobuf decoding (wire format analysis)
│   ├── schema_builder.py           # Schema generation
│   ├── validators.py               # Validation & quality scoring
│   └── localization_parser.py      # Localization key parser
├── tests/
│   └── test_localization_parser.py # Unit tests for localization parsing
├── output/                         # Generated output (created after running scripts)
│   ├── actions_complete.json       # All 1,813 actions (9 MB)
│   ├── actions_complete.csv        # CSV export (1,813 rows)
│   ├── types_complete.json         # All 2,823 types (2.3 MB)
│   ├── hidden_actions.json         # 1,627 hidden actions (554 KB)
│   ├── validation_report.json      # Quality metrics
│   └── protobuf_decoded/           # Decoded BLOBs (generated)
├── example-output/                 # Pre-generated example output
│   ├── actions_complete.json       # Example: All 1,813 actions (8.6 MB)
│   └── types_complete.json         # Example: All 2,823 types (2.3 MB)
├── Tools-prod.sqlite               # Source database (copy from ~/Library/Shortcuts/ToolKit/)
├── requirements.txt                # Python dependencies
├── setup.sh                        # Setup script
├── README.md                       # This file
└── USAGE_GUIDE.md                  # Complete usage guide
```

## 📖 Database Schema

### Tools-prod.sqlite

Apple's action catalog database containing:

- **Tools** - 1,813 available actions (90% hidden!)
- **Types** - 2,823 data type definitions
- **Parameters** - Action parameters with type constraints
- **ContainerMetadata** - 138 apps providing actions
- **EntityProperties** - 1,661 entity properties
- **EnumerationCases** - 7,530 enum values
- **ToolLocalizations** - Localized names and descriptions
- **TypeDisplayRepresentations** - Type display names

### Key Tables

- `Tools` - Actions with protobuf BLOBs for requirements
- `Parameters` - Parameter definitions with typeInstance BLOBs
- `Types` - Type system with kind (primitive, entity, enum)
- `TypeCoercions` - Type conversion rules

## 🔬 Technical Details

### Localization Key Parsing

The toolkit automatically fixes localization keys using pattern recognition:

**Key Patterns Detected:**
1. **Version-based**: `photos_IncreaseWarmth_1.0.0_intent_title` → "Increase Warmth"
2. **Entity type**: `browser_SearchableWebsiteEntity_1.0.0_entity_type_display_representation` → "Searchable Website"
3. **Constant case**: `CONTROL_CENTER_TOGGLE_RECORDING_INTENT_TITLE` → "Control Center Toggle Recording"
4. **Parameter keys**: `browser_SearchWebsiteIntent_1.0.0_intent_parameter_website_description` → "Website"
5. **Embedded keys**: Cleans keys within otherwise good text

**Transformations:**
- CamelCase → Title Case ("IncreaseWarmth" → "Increase Warmth")
- CONSTANT_CASE → Title Case preserving acronyms
- Entity suffix removal ("SearchableWebsiteEntity" → "Searchable Website")
- Acronym preservation (URL, HTML, API stay uppercase)

**Confidence Scoring:**
- High confidence (>0.9): Version-based and entity type patterns
- Good confidence (0.85): Parameter and constant patterns
- Metadata tracking: All transformations preserve original keys

### Protobuf Decoding Approach

Since Apple doesn't provide `.proto` schema files, we use:

1. **Wire format analysis** - Parse protobuf binary format manually
2. **String extraction** - Extract embedded UTF-8 strings
3. **Pattern matching** - Infer field types from multiple samples
4. **Best-effort decoding** - Extract what we can, document limitations

### Visibility Flags

Actions are classified by `visibilityFlags`:

| Flags | Level | Description | Count |
|-------|-------|-------------|-------|
| 0 | Public | Fully visible and documented | 186 |
| 2 | Somewhat Hidden | Limited visibility | 636 |
| 3 | Hidden | Not shown in normal browsing | 440 |
| 7 | Very Hidden | Likely internal | 336 |
| 13 | Experimental | Beta features | 2 |
| 15 | Maximum Hidden | Internal-only | 181 |

## 📚 Use Cases

### For Researchers

- Study Apple's automation API design
- Track API changes between macOS versions
- Discover undocumented features
- Analyze type system architecture

### For Developers

- Build third-party Shortcuts tools
- Generate action documentation
- Create shortcuts programmatically
- Validate shortcut definitions

### For Power Users

- Discover hidden actions
- Understand action capabilities
- Find compatible action chains
- Learn parameter options

## 🔒 Limitations

- **Read-only** - Tools-prod.sqlite is maintained by the system; modifications won't affect Shortcuts
- **No .proto schemas** - Protobuf decoding is best-effort reverse engineering
- **macOS-specific** - Requires macOS Monterey (12.0) or later with Shortcuts app
- **Database location** - `~/Library/Shortcuts/ToolKit/`
  - Actual file: `Tools-prod.v[VERSION]-[UUID].sqlite` (e.g., `Tools-prod.v61-F145B045-4246-431B-A407-EFC6E6AAA0B2.sqlite`)
  - Symlink: `Tools-active` (always points to current active database)
  - Version number varies by macOS version (v61 for Sequoia 15.x, v58-60 for Sonoma, etc.)
  - Must be copied to project directory and renamed to `Tools-prod.sqlite`
- **SQLite WAL mode** - The database uses Write-Ahead Logging; copy only the main `.sqlite` file, not `.wal` or `.shm` files

## 🔧 Troubleshooting

### Database file not found

If you can't find the database file:

```bash
# List all files in the ToolKit directory
ls -al ~/Library/Shortcuts/ToolKit/
```

The database should exist if:
- You're running macOS Monterey (12.0) or later
- The Shortcuts app has been opened at least once
- Shortcuts has been given necessary permissions

If the file doesn't exist, open the Shortcuts app to initialize the database.

**What the files are:**
- `Tools-active` - Symlink to the current active database (easiest to copy)
- `Tools-prod.v[VERSION]-[UUID].sqlite` - The main database file (this is what you need)
- `.sqlite-shm` and `.sqlite-wal` - Write-Ahead Log files (don't copy these)
- `.sqlite.lock` - Lock file (don't copy this)

### Permission errors

If you get permission errors when copying:

```bash
# Check if the file is readable
ls -l ~/Library/Shortcuts/ToolKit/Tools-prod.v*.sqlite

# If needed, you can also use sudo (not typically necessary)
# Or check System Settings > Privacy & Security > Full Disk Access
```

### Wrong database version

Different macOS versions have different database schemas:
- macOS Sequoia (15.x): v61+
- macOS Sonoma (14.x): v58-v60
- macOS Ventura (13.x): v55-v57

The toolkit should work with most versions, but results may vary with older versions.

## ⚠️ Disclaimer & Legal

**This toolkit is provided for educational and research purposes only.**

### Important Notes

- **Database Ownership**: The `Tools-prod.sqlite` database is part of macOS and is owned by Apple Inc. This toolkit does NOT include or redistribute Apple's database file.
- **User Responsibility**: Users must copy the database from their own macOS system. You are responsible for ensuring your use complies with applicable terms of service and agreements.
- **Read-Only Analysis**: This toolkit only reads and documents the database structure. It does not modify the Shortcuts app, macOS system files, or any Apple software.
- **No Affiliation**: This project is not affiliated with, endorsed by, or supported by Apple Inc.
- **No Warranty**: This software is provided "as is" without warranty of any kind. Use at your own risk.
- **Reverse Engineering**: This toolkit uses standard reverse engineering techniques (SQLite database analysis, protobuf wire format parsing) commonly used in security research and academic study.

### What This Toolkit Does

✅ Reads SQLite database files from your own Mac
✅ Extracts and documents publicly accessible action metadata
✅ Provides tools for analyzing Shortcuts automation capabilities
✅ Helps developers understand the Shortcuts ecosystem

### What This Toolkit Does NOT Do

❌ Redistribute Apple's proprietary database files
❌ Modify any Apple software or system files
❌ Enable any unauthorized access or security bypass
❌ Violate any copyright or trade secret protections

### Precedent

Similar reverse engineering and documentation projects exist in the Apple developer community, including:
- iOS Runtime Headers documentation
- Private API documentation projects
- Security research tools
- Academic research into macOS/iOS internals

**By using this toolkit, you acknowledge these terms and take responsibility for your own compliance with applicable laws and agreements.**

## 🙏 Acknowledgments

- Built using Python's `protobuf`, `rich`, `pandas`, and `inflect` libraries
- Inspired by the Apple Shortcuts community
- Database analysis based on macOS Sequoia / iOS 18+
- Localization parsing uses pattern recognition and linguistic transformations

## 🤝 Contributing

Found an issue or want to add features?

1. Document what you found
2. Update the relevant scripts
3. Test with the database
4. Share your discoveries!

## 📧 Questions?

This toolkit demonstrates:
- SQLite database analysis
- Protobuf reverse engineering
- Data extraction and schema generation
- Python best practices
