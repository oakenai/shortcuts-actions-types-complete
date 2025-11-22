#!/usr/bin/env python3
"""
Type System Analyzer

Extract and document all types from Tools-prod.sqlite with full details.

Usage:
    python3 analyze_types.py [options]

Options:
    --all             Extract all types
    --type TYPE_ID    Analyze specific type
    --enums           Extract only enum types
    --entities        Extract only entity types
    --export PATH     Export to JSON file
    -v, --verbose     Verbose output
"""

import sys
import json
import argparse
from pathlib import Path
from typing import Dict, Any, List

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

from utils.db_utils import (
    connect_db,
    get_type_count,
    get_type_info,
    get_entity_properties,
    get_enum_cases,
)
from utils.schema_builder import build_type_schema
from utils.validators import parse_type_identifier


def get_all_types(db_path: str = "Tools-prod.sqlite", verbose: bool = False) -> List[Dict[str, Any]]:
    """Extract all types with full information"""
    conn = connect_db(db_path)

    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            t.rowId,
            t.id,
            t.kind,
            t.runtimeFlags,
            tdr.name,
            cm.id as container_id
        FROM Types t
        LEFT JOIN TypeDisplayRepresentations tdr
            ON t.rowId = tdr.typeId
            AND tdr.locale = 'en'
        LEFT JOIN ContainerMetadata cm
            ON t.sourceContainerId = cm.rowId
        ORDER BY t.rowId
    """)

    types = []
    for row in cursor.fetchall():
        type_data = dict(row)

        # Build full schema
        schema = build_type_schema(conn, type_data)

        # Add parsed identifier info
        schema['parsed'] = parse_type_identifier(type_data['rowId'])

        types.append(schema)

    conn.close()
    return types


def analyze_type_usage(db_path: str = "Tools-prod.sqlite") -> Dict[str, Any]:
    """Analyze how types are used across actions"""
    conn = connect_db(db_path)

    # Get type usage in parameters
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            tpt.typeId,
            COUNT(DISTINCT tpt.toolId) as used_in_actions,
            COUNT(*) as total_parameter_uses
        FROM ToolParameterTypes tpt
        GROUP BY tpt.typeId
        ORDER BY used_in_actions DESC
    """)

    type_usage = {}
    for row in cursor.fetchall():
        type_usage[row['typeId']] = {
            'used_in_actions': row['used_in_actions'],
            'total_parameter_uses': row['total_parameter_uses'],
        }

    # Get type usage in outputs
    cursor.execute("""
        SELECT
            tot.typeIdentifier,
            COUNT(DISTINCT tot.toolId) as used_as_output
        FROM ToolOutputTypes tot
        GROUP BY tot.typeIdentifier
    """)

    for row in cursor.fetchall():
        type_id = row['typeIdentifier']
        if type_id not in type_usage:
            type_usage[type_id] = {'used_in_actions': 0, 'total_parameter_uses': 0}
        type_usage[type_id]['used_as_output'] = row['used_as_output']

    conn.close()
    return type_usage


def main():
    parser = argparse.ArgumentParser(
        description="Analyze type system from Tools-prod.sqlite"
    )

    parser.add_argument('--all', action='store_true', help='Extract all types')
    parser.add_argument('--type', metavar='ID', help='Analyze specific type')
    parser.add_argument('--enums', action='store_true', help='Extract only enums')
    parser.add_argument('--entities', action='store_true', help='Extract only entities')
    parser.add_argument('--export', metavar='PATH', default='output/types_complete.json', help='Export path')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    parser.add_argument('--db', default='Tools-prod.sqlite', help='Database path')

    args = parser.parse_args()

    if not any([args.all, args.type, args.enums, args.entities]):
        parser.print_help()
        sys.exit(1)

    try:
        if args.all or args.enums or args.entities:
            print("\n🔍 Extracting type system...\n")

            types = get_all_types(args.db, args.verbose)

            # Filter by kind if requested
            if args.enums:
                types = [t for t in types if t.get('kind') == 3]
                print(f"Found {len(types)} enum types")
            elif args.entities:
                types = [t for t in types if t.get('kind') == 2]
                print(f"Found {len(types)} entity types")

            # Get usage info
            usage = analyze_type_usage(args.db)

            # Add usage info to each type
            for t in types:
                type_id = t.get('id')
                if type_id in usage:
                    t['usage'] = usage[type_id]

            # Export
            export_path = Path(args.export)
            export_path.parent.mkdir(parents=True, exist_ok=True)

            with open(export_path, 'w') as f:
                json.dump(types, f, indent=2, default=str)

            print(f"✅ Exported {len(types)} types to {export_path}")

            # Summary statistics
            if RICH_AVAILABLE:
                console = Console()

                # By kind
                by_kind = {}
                for t in types:
                    kind_name = t.get('kind_name', 'unknown')
                    by_kind[kind_name] = by_kind.get(kind_name, 0) + 1

                table = Table(title="Types by Kind")
                table.add_column("Kind", style="cyan")
                table.add_column("Count", justify="right", style="green")

                for kind, count in sorted(by_kind.items(), key=lambda x: x[1], reverse=True):
                    table.add_row(kind, str(count))

                console.print(table)

                # Most used types
                types_with_usage = [t for t in types if t.get('usage')]
                types_with_usage.sort(key=lambda x: x.get('usage', {}).get('used_in_actions', 0), reverse=True)

                if types_with_usage:
                    table2 = Table(title="Top 10 Most Used Types")
                    table2.add_column("Type", style="cyan", max_width=40)
                    table2.add_column("Actions", justify="right", style="green")
                    table2.add_column("Parameters", justify="right", style="yellow")

                    for t in types_with_usage[:10]:
                        usage_info = t.get('usage', {})
                        table2.add_row(
                            t.get('name') or t.get('id'),
                            str(usage_info.get('used_in_actions', 0)),
                            str(usage_info.get('total_parameter_uses', 0))
                        )

                    console.print(table2)

        if args.type:
            conn = connect_db(args.db)
            type_info = get_type_info(conn, args.type)

            if not type_info:
                print(f"❌ Type not found: {args.type}")
                sys.exit(1)

            schema = build_type_schema(conn, type_info)
            schema['parsed'] = parse_type_identifier(args.type)

            if RICH_AVAILABLE:
                console = Console()
                console.print(Panel(
                    json.dumps(schema, indent=2, default=str),
                    title=f"Type: {args.type}"
                ))
            else:
                print(json.dumps(schema, indent=2, default=str))

            conn.close()

        print("\n✨ Done!\n")

    except FileNotFoundError as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
