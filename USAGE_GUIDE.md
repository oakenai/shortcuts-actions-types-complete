# Complete Usage Guide

## Understanding the Output

### Actions JSON Structure

Each action in `output/actions_complete.json` contains:

```json
{
  "id": "action.identifier",
  "name": "Human Readable Name",
  "name_metadata": {
    "is_synthetic": false
  },
  "description_summary": "What the action does",
  "description_metadata": {
    "is_synthetic": false
  },
  "type": "action|appIntent|siriIntent",
  "visibility_flags": 0-15,
  "hidden": true|false,
  "localization_issues": [],
  "parameters": [
    {
      "key": "paramKey",
      "name": "Parameter Name",
      "name_metadata": {
        "is_synthetic": false
      },
      "description": "What this parameter does",
      "description_metadata": {
        "is_synthetic": false
      },
      "accepted_types": ["type1", "type2"],
      "localization_issues": [],
      "type_details": [...]  // Rich type information (when --type-info flag used)
    }
  ]
}
```

### Types JSON Structure

The `output/types_complete.json` file contains all 2,823 types:

```json
{
  "id": "com.apple.shortcuts.com.agiletortoise.Drafts4.addto.DraftsAddMode",
  "name": "Mode",
  "kind": 3,
  "kind_name": "enum",
  "parsed": {
    "namespace": "com.apple.shortcuts",
    "third_party_bundle": "com.agiletortoise.Drafts4",
    "category": "addto",
    "type_name": "DraftsAddMode",
    "is_third_party": true,
    "is_enum": true
  },
  "enum_cases": [
    {"id": "create", "title": "Create"},
    {"id": "prepend", "title": "Prepend"},
    {"id": "append", "title": "Append"}
  ],
  "usage": {
    "used_in_actions": 1,
    "total_parameter_uses": 1
  }
}
```

### Understanding Complex Type Identifiers

Types like `com.apple.shortcuts.com.agiletortoise.Drafts4.addto.DraftsAddMode` break down as:

1. **Namespace**: `com.apple.shortcuts` - Apple's Shortcuts framework
2. **Third-party bundle**: `com.agiletortoise.Drafts4` - Drafts app identifier
3. **Category**: `addto` - Specific action category
4. **Type name**: `DraftsAddMode` - The actual type
5. **Kind**: `enum` - It's an enumeration with specific values

### Metadata Fields

**Localization Metadata**: The `name_metadata` and `description_metadata` fields track whether text is original or synthetically generated:

```json
{
  "is_synthetic": true,
  "original_key": "browser_SearchableWebsiteEntity_1.0.0_entity_type_display_representation",
  "confidence": 0.9,
  "source": "parsed_key"
}
```

- `is_synthetic`: `true` if text was generated from a localization key, `false` if from database
- `original_key`: The original localization key (only present when synthetic)
- `confidence`: Parsing confidence score from 0.0-1.0 (only present when synthetic)
- `source`: How text was generated: `parsed_key`, `cleaned_embedded`, `original`, or `fallback`

### Localization Issues

By default, localization keys are **automatically fixed** and converted to readable text. The `localization_issues` array is only populated when:
- Using `--no-fix-localizations` flag (disables automatic fixing)
- A localization key couldn't be parsed with sufficient confidence

When automatic fixing is enabled (default), you'll see synthetic localizations marked in the metadata fields instead.

## Complete Workflow

### 1. Extract All Actions

```bash
source venv/bin/activate

# Full extraction (all 1,813 actions with localization fixing enabled by default)
python3 extract_shortcuts_actions.py --all -v

# Output: output/actions_complete.json (~9 MB)

# Disable localization fixing if you want raw keys
python3 extract_shortcuts_actions.py --all --no-fix-localizations
```

### 2. Extract All Types

```bash
# All 2,823 types with usage statistics
python3 analyze_types.py --all -v

# Output: output/types_complete.json
```

### 3. Find Hidden Actions

```bash
# All hidden actions
python3 find_hidden_actions.py

# Only experimental (flags 13-15)
python3 find_hidden_actions.py --experimental

# Output: Terminal display + optional --export
```

### 4. Validate Output Quality

```bash
# Validate and generate report
python3 validate_output.py --show-issues --report output/validation_report.json

# Shows:
# - Quality scores (0-100, average 99.7)
# - Synthetic localization warnings (informational)
# - Complex type warnings
# - All 1,813 schemas now 100% valid with localization fixing
```

### 5. Decode Protobuf BLOBs

```bash
# For specific action
python3 decode_protobuf_fields.py --action "is.workflow.actions.file.createfolder"

# All parameter type instances
python3 decode_protobuf_fields.py --all-params --export output/protobuf_decoded

# Extracts: UTI types, OS requirements, embedded strings
```

## Advanced Usage

### Localization Fixing Options

The toolkit automatically fixes localization keys by default. You can control this behavior:

```bash
# Default: Automatic localization fixing enabled
python3 extract_shortcuts_actions.py --all -v

# Disable localization fixing (see raw keys)
python3 extract_shortcuts_actions.py --all --no-fix-localizations

# Compare both approaches
python3 extract_shortcuts_actions.py --all --export output/with_fixes.json
python3 extract_shortcuts_actions.py --all --no-fix-localizations --export output/raw_keys.json
```

**When to disable localization fixing:**
- Debugging localization issues
- Comparing with original database data
- Research into Apple's localization key patterns
- Verifying the parser's transformations

**Localization fixing process:**
1. Detects 5 key patterns (version-based, entity type, constant case, parameter, embedded)
2. Transforms to readable text (e.g., "SearchableWebsiteEntity" → "Searchable Website")
3. Preserves acronyms (URL, HTML, API stay uppercase)
4. Tracks confidence scores (0.0-1.0) in metadata
5. Marks as warnings, not errors, in validation

### Export to CSV for Analysis

```bash
python3 extract_shortcuts_actions.py --all --csv

# Output: output/actions_complete.csv
# Use in Excel, Google Sheets, or data analysis tools
```

### Find Specific Action Details

```bash
python3 find_hidden_actions.py --details "com.apple.GenerativePlaygroundApp.GenerateImageIntent"
```

### Search by Type

```bash
# Find all enum types
python3 analyze_types.py --enums

# Find all entity types
python3 analyze_types.py --entities
```

### Cross-Reference Types and Actions

```python
import json

# Load both files
with open('output/actions_complete.json') as f:
    actions = json.load(f)

with open('output/types_complete.json') as f:
    types = json.load(f)

# Create type lookup
type_lookup = {t['id']: t for t in types}

# Find actions using specific type
for action in actions:
    for param in action['parameters']:
        for type_id in param['accepted_types']:
            if type_id in type_lookup:
                type_info = type_lookup[type_id]
                print(f"{action['name']} uses {type_info['name']} ({type_info['kind_name']})")
```

## Interpretation Guide

### Visibility Flags

| Value | Meaning | Example |
|-------|---------|---------|
| 0 | Public/documented | "Create Folder" |
| 2 | Somewhat hidden | Some system actions |
| 7 | Very hidden | Internal actions |
| 15 | Maximum hidden | "Create Image" (Image Playground) |

### Type Kinds

| Kind | Name | Description | Example |
|------|------|-------------|---------|
| 1 | primitive | Basic types | string, bool, number |
| 2 | entity | Complex objects with properties | Photo, Contact, Event |
| 3 | enum | Fixed set of values | DraftsAddMode, BookTheme |
| 4 | object | Structured data | Various objects |
| 6 | array | Collections | Lists of items |
| 8 | special | System types | Special types |

### Action Types

- **action**: Built-in Shortcuts actions
- **appIntent**: Modern App Intent framework (73% of actions)
- **siriIntent**: Legacy SiriKit intents (5%)

## Tips & Tricks

### 1. Finding Actions by App

```bash
cat output/actions_complete.json | python3 -c "
import json, sys
data = json.load(sys.stdin)
notes_actions = [a for a in data if a['app']['bundle_id'] == 'com.apple.Notes']
for a in notes_actions:
    print(f\"{a['id']}: {a['name']}\")
"
```

### 2. Finding Actions with Synthetic Localizations

```bash
cat output/actions_complete.json | python3 -c "
import json, sys
data = json.load(sys.stdin)
synthetic = [a for a in data if a.get('name_metadata', {}).get('is_synthetic')]
print(f'Found {len(synthetic)} actions with synthetic localizations')
for a in synthetic[:10]:
    meta = a['name_metadata']
    print(f\"  {a['id']}: {a['name']}\")
    print(f\"    Original: {meta.get('original_key')}\")
    print(f\"    Confidence: {meta.get('confidence')}\")
"
```

### 3. Type Usage Analysis

```bash
cat output/types_complete.json | python3 -c "
import json, sys
data = json.load(sys.stdin)
# Sort by usage
sorted_types = sorted(data, key=lambda x: x.get('usage', {}).get('used_in_actions', 0), reverse=True)
print('Top 20 most used types:')
for t in sorted_types[:20]:
    usage = t.get('usage', {})
    print(f\"{t['name']:30s} - {usage.get('used_in_actions', 0):4d} actions\")
"
```

## Troubleshooting

### "Localization key" in output

**This is now automatically fixed by default!** The toolkit intelligently parses localization keys and converts them to readable text.

If you see synthetic localizations:
- Check the `name_metadata` or `description_metadata` fields for confidence scores
- High confidence (>0.9) means the transformation is very reliable
- Original keys are preserved in metadata for transparency

To disable automatic fixing and see raw keys:
```bash
python3 extract_shortcuts_actions.py --all --no-fix-localizations
```

### Understanding synthetic localizations

Synthetic localizations appear when the database contains a localization key instead of actual text. The toolkit automatically:
1. Detects the key pattern (version-based, entity type, constant case, etc.)
2. Parses and transforms it to readable text (e.g., "IncreaseWarmth" → "Increase Warmth")
3. Tracks the transformation in metadata with confidence scores

This happens for ~17 actions (0.9% of all actions) and is marked as a warning, not an error.

### Complex type identifiers

Use `analyze_types.py --type TYPE_ID` to get full details including parsed components.

### Large file sizes

- Use `--no-protobuf` for faster, smaller extraction (~6 MB vs ~9 MB)
- Use `--limit N` for testing
- The file size increased from 2.5 MB to 9 MB due to:
  - Complete protobuf decoding (type_info fields)
  - Metadata tracking for localization fixes
  - More comprehensive parameter details

### Want more type information in actions?

The main extraction skips detailed type info for speed. To include it, modify `extract_shortcuts_actions.py` to pass `include_type_info=True` to `build_action_schema()`.

## Output Files Summary

| File | Size | Contents |
|------|------|----------|
| `actions_complete.json` | ~9 MB | All 1,813 actions with full metadata |
| `types_complete.json` | ~2.3 MB | All 2,823 types with usage stats |
| `hidden_actions.json` | ~554 KB | 1,627 hidden actions |
| `validation_report.json` | ~1 KB | Quality metrics (99.7 avg score) |
| `actions_complete.csv` | ~500 KB | Spreadsheet format |

### Quality Metrics (from validation_report.json)

- **100% valid schemas** (1,813/1,813) - Up from 98%
- **0 localization errors** - Down from 39
- **99.7/100 average quality score** - Up from 97.4
- **17 synthetic localizations** - Marked as warnings, not errors
- **2,771 complex type warnings** - Normal for actions with many parameters

## Next Steps

1. ✅ Extract actions and types
2. ✅ Validate quality
3. ✅ Explore hidden actions
4. Use data for:
   - Building Shortcuts tools
   - Documentation generation
   - Workflow validation
   - Action discovery UIs

Happy reverse engineering! 🚀
