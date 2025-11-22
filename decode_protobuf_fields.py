#!/usr/bin/env python3
"""
Protobuf BLOB Decoder

Decode protobuf BLOBs from Tools-prod.sqlite database.
Since we don't have .proto schema files, this uses best-effort decoding.

Usage:
    python3 decode_protobuf_fields.py [options]

Options:
    --action ACTION_ID    Decode BLOBs for specific action
    --type TYPE_ID        Decode BLOBs for specific type
    --all-params          Decode all parameter typeInstance BLOBs
    --all-requirements    Decode all requirements BLOBs
    --export DIR          Export decoded data to directory
    -v, --verbose         Verbose output
"""

import sys
import json
import argparse
from pathlib import Path
from typing import Dict, Any

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.syntax import Syntax
    from rich import print as rprint
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

from utils.db_utils import connect_db, get_action_parameters
from utils.protobuf_parser import (
    decode_protobuf_blob,
    extract_strings_from_blob,
    analyze_requirements_blob,
    analyze_type_instance_blob,
    analyze_coercion_blob,
    format_blob_analysis,
)


def decode_action_blobs(db_path: str, action_id: str, verbose: bool = False):
    """Decode all BLOBs for a specific action"""
    conn = connect_db(db_path)

    # Get action
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            t.rowId,
            t.id,
            t.requirements,
            t.outputTypeInstance,
            tl.name
        FROM Tools t
        LEFT JOIN ToolLocalizations tl ON t.rowId = tl.toolId AND tl.locale = 'en'
        WHERE t.id = ?
    """, (action_id,))

    row = cursor.fetchone()
    if not row:
        print(f"❌ Action not found: {action_id}")
        return

    action_data = dict(row)
    tool_id = action_data['rowId']

    if RICH_AVAILABLE:
        console = Console()
        console.print(Panel(
            f"[bold cyan]{action_id}[/bold cyan]\n{action_data.get('name') or '(no name)'}",
            title="🔬 Decoding Action BLOBs"
        ))

    # Decode requirements
    if action_data['requirements']:
        requirements_blob = bytes(action_data['requirements'])
        analysis = analyze_requirements_blob(requirements_blob)

        if RICH_AVAILABLE:
            console.print("\n[bold yellow]Requirements BLOB:[/bold yellow]")
            console.print(format_blob_analysis(analysis))
        else:
            print("\nRequirements BLOB:")
            print(format_blob_analysis(analysis))

    # Decode outputTypeInstance
    if action_data['outputTypeInstance']:
        output_blob = bytes(action_data['outputTypeInstance'])
        analysis = decode_protobuf_blob(output_blob)

        if RICH_AVAILABLE:
            console.print("\n[bold yellow]Output Type Instance BLOB:[/bold yellow]")
            console.print(json.dumps(analysis, indent=2))
        else:
            print("\nOutput Type Instance BLOB:")
            print(json.dumps(analysis, indent=2))

    # Decode parameters
    parameters = get_action_parameters(conn, tool_id)

    if parameters:
        if RICH_AVAILABLE:
            console.print(f"\n[bold green]Parameters ({len(parameters)}):[/bold green]")
        else:
            print(f"\nParameters ({len(parameters)}):")

        for param in parameters:
            if param['typeInstance']:
                analysis = analyze_type_instance_blob(param['typeInstance'])

                if RICH_AVAILABLE:
                    console.print(f"\n[cyan]{param['key']}[/cyan] - {param.get('name') or '(no name)'}")
                    console.print(format_blob_analysis(analysis))
                else:
                    print(f"\n{param['key']} - {param.get('name') or '(no name)'}")
                    print(format_blob_analysis(analysis))

    conn.close()


def decode_all_parameter_blobs(db_path: str, limit: int = None, verbose: bool = False):
    """Decode all parameter typeInstance BLOBs"""
    conn = connect_db(db_path)

    cursor = conn.cursor()
    query = """
        SELECT DISTINCT
            p.typeInstance,
            p.key,
            pl.name,
            COUNT(*) as usage_count
        FROM Parameters p
        LEFT JOIN ParameterLocalizations pl ON p.toolId = pl.toolId AND p.key = pl.key AND pl.locale = 'en'
        WHERE p.typeInstance IS NOT NULL
        GROUP BY p.typeInstance
        ORDER BY usage_count DESC
    """

    if limit:
        query += f" LIMIT {limit}"

    cursor.execute(query)

    results = []
    for row in cursor.fetchall():
        blob = bytes(row['typeInstance'])
        analysis = analyze_type_instance_blob(blob)

        result = {
            'param_key': row['key'],
            'param_name': row['name'],
            'usage_count': row['usage_count'],
            'analysis': analysis,
        }
        results.append(result)

        if verbose:
            print(f"\n{row['key']} ({row['usage_count']} uses)")
            print(format_blob_analysis(analysis))

    conn.close()
    return results


def decode_all_requirements(db_path: str, limit: int = None, verbose: bool = False):
    """Decode all unique requirements BLOBs"""
    conn = connect_db(db_path)

    cursor = conn.cursor()
    query = """
        SELECT DISTINCT
            t.requirements,
            COUNT(*) as usage_count
        FROM Tools t
        WHERE LENGTH(t.requirements) > 0
        GROUP BY t.requirements
        ORDER BY usage_count DESC
    """

    if limit:
        query += f" LIMIT {limit}"

    cursor.execute(query)

    results = []
    for row in cursor.fetchall():
        blob = bytes(row['requirements'])
        analysis = analyze_requirements_blob(blob)

        result = {
            'usage_count': row['usage_count'],
            'analysis': analysis,
        }
        results.append(result)

        if verbose:
            print(f"\nRequirements pattern ({row['usage_count']} uses):")
            print(format_blob_analysis(analysis))

    conn.close()
    return results


def export_decoded_data(data: Any, output_path: str):
    """Export decoded data to JSON"""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, 'w') as f:
        json.dump(data, f, indent=2, default=str)

    print(f"✅ Exported to {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Decode protobuf BLOBs from Tools-prod.sqlite",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument('--action', metavar='ID', help='Decode BLOBs for specific action')
    parser.add_argument('--type', metavar='ID', help='Decode BLOBs for specific type')
    parser.add_argument('--all-params', action='store_true', help='Decode all parameter typeInstance BLOBs')
    parser.add_argument('--all-requirements', action='store_true', help='Decode all requirements BLOBs')
    parser.add_argument('--limit', type=int, help='Limit results')
    parser.add_argument('--export', metavar='DIR', help='Export to directory')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    parser.add_argument('--db', default='Tools-prod.sqlite', help='Database path')

    args = parser.parse_args()

    if not any([args.action, args.type, args.all_params, args.all_requirements]):
        parser.print_help()
        sys.exit(1)

    try:
        if args.action:
            decode_action_blobs(args.db, args.action, args.verbose)

        if args.all_params:
            print("\n🔬 Decoding all parameter typeInstance BLOBs...")
            results = decode_all_parameter_blobs(args.db, args.limit, args.verbose)

            if args.export:
                export_path = Path(args.export) / 'parameters_decoded.json'
                export_decoded_data(results, str(export_path))

            print(f"\n✅ Decoded {len(results)} unique parameter BLOBs")

        if args.all_requirements:
            print("\n🔬 Decoding all requirements BLOBs...")
            results = decode_all_requirements(args.db, args.limit, args.verbose)

            if args.export:
                export_path = Path(args.export) / 'requirements_decoded.json'
                export_decoded_data(results, str(export_path))

            print(f"\n✅ Decoded {len(results)} unique requirements patterns")

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
