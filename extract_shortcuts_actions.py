#!/usr/bin/env python3
"""
Shortcuts Actions Extractor

Extract and document all Shortcuts actions from Tools-prod.sqlite database.
Decodes protobuf BLOBs, discovers hidden actions, and generates comprehensive schemas.

Usage:
    python3 extract_shortcuts_actions.py [options]

Options:
    --all           Extract all actions to output/actions_complete.json
    --hidden        Extract only hidden actions (visibilityFlags > 0)
    --csv           Also export as CSV
    --no-protobuf   Skip protobuf decoding (faster)
    --limit N       Limit to N actions (for testing)
    --locale LANG   Use specific locale (default: en)
    -v, --verbose   Verbose output

Examples:
    # Extract all actions with full details
    python3 extract_shortcuts_actions.py --all

    # Extract hidden actions only
    python3 extract_shortcuts_actions.py --hidden

    # Quick extract without protobuf (faster)
    python3 extract_shortcuts_actions.py --all --no-protobuf

    # Export to CSV and JSON
    python3 extract_shortcuts_actions.py --all --csv
"""

import sys
import json
import csv
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional

try:
    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn
    from rich.table import Table
    from rich import print as rprint
    from rich.panel import Panel
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    print("Note: Install 'rich' for better output: pip install rich")

from utils.db_utils import (
    connect_db,
    get_all_actions,
    get_action_count,
    get_hidden_actions,
)
from utils.schema_builder import (
    build_action_schema,
    summarize_action_collection,
    classify_action_visibility,
)


def extract_all_actions(
    db_path: str = "Tools-prod.sqlite",
    include_protobuf: bool = True,
    fix_localizations: bool = True,
    locale: str = "en",
    limit: Optional[int] = None,
    verbose: bool = False
) -> List[Dict[str, Any]]:
    """
    Extract all actions with complete schemas.

    Args:
        db_path: Path to database
        include_protobuf: Whether to decode protobuf BLOBs
        fix_localizations: Whether to fix localization keys with smart parsing
        locale: Language locale
        limit: Maximum number of actions (None = all)
        verbose: Verbose output

    Returns:
        List of complete action schemas
    """
    conn = connect_db(db_path)
    total = get_action_count(conn)

    if verbose:
        print(f"\n📊 Database contains {total} actions")
        print(f"🌍 Extracting with locale: {locale}")
        print(f"🔬 Protobuf decoding: {'enabled' if include_protobuf else 'disabled'}")
        print(f"🔧 Localization fixing: {'enabled' if fix_localizations else 'disabled'}\n")

    # Get all actions
    actions_data = get_all_actions(conn, locale)

    if limit:
        actions_data = actions_data[:limit]

    # Build schemas
    schemas = []

    if RICH_AVAILABLE:
        console = Console()
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Extracting actions...", total=len(actions_data))

            for action_data in actions_data:
                schema = build_action_schema(conn, action_data, include_protobuf, False, fix_localizations, locale)
                schemas.append(schema)
                progress.update(task, advance=1)
    else:
        # Simple progress without rich
        for i, action_data in enumerate(actions_data):
            if verbose and i % 100 == 0:
                print(f"Progress: {i}/{len(actions_data)} ({i*100//len(actions_data)}%)")
            schema = build_action_schema(conn, action_data, include_protobuf, False, fix_localizations, locale)
            schemas.append(schema)

    conn.close()
    return schemas


def export_to_json(schemas: List[Dict[str, Any]], output_path: str, verbose: bool = False):
    """Export schemas to JSON file"""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, 'w', encoding='utf-8') as f:
        json.dump(schemas, f, indent=2, ensure_ascii=False)

    if verbose:
        print(f"✅ Exported to {output_path} ({path.stat().st_size:,} bytes)")


def export_to_csv(schemas: List[Dict[str, Any]], output_path: str, verbose: bool = False):
    """Export schemas to CSV file (flattened)"""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    # Flatten schema for CSV
    rows = []
    for schema in schemas:
        row = {
            'id': schema.get('id'),
            'name': schema.get('name'),
            'type': schema.get('type'),
            'visibility_flags': schema.get('visibility_flags'),
            'hidden': schema.get('hidden'),
            'app_bundle': schema.get('app', {}).get('bundle_id'),
            'app_name': schema.get('app', {}).get('name'),
            'description': schema.get('description_summary'),
            'parameter_count': len(schema.get('parameters', [])),
            'output_types': ', '.join(schema.get('output_types', [])),
            'categories': ', '.join(schema.get('categories', [])),
            'deprecated': bool(schema.get('deprecation')),
        }
        rows.append(row)

    # Write CSV
    if rows:
        fieldnames = rows[0].keys()
        with open(path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        if verbose:
            print(f"✅ Exported to {output_path} ({len(rows)} rows)")


def display_summary(schemas: List[Dict[str, Any]]):
    """Display summary statistics"""
    summary = summarize_action_collection(schemas)

    if RICH_AVAILABLE:
        console = Console()

        # Main stats panel
        stats_text = f"""
[bold cyan]Total Actions:[/bold cyan] {summary['total_count']}
[bold yellow]Hidden Actions:[/bold yellow] {summary['hidden_count']} ({summary['hidden_count']*100//summary['total_count']}%)
[bold red]Deprecated:[/bold red] {summary['deprecated_count']}
[bold green]With Parameters:[/bold green] {summary['with_parameters']} (avg {summary['parameter_count']//max(summary['with_parameters'],1)} params)
        """
        console.print(Panel(stats_text.strip(), title="📊 Extraction Summary", border_style="blue"))

        # By type table
        type_table = Table(title="Actions by Type", show_header=True)
        type_table.add_column("Type", style="cyan")
        type_table.add_column("Count", justify="right", style="green")
        type_table.add_column("Percentage", justify="right")

        for action_type, count in sorted(summary['by_type'].items(), key=lambda x: x[1], reverse=True):
            pct = f"{count*100//summary['total_count']}%"
            type_table.add_row(action_type, str(count), pct)

        console.print(type_table)

        # By visibility table
        vis_table = Table(title="Actions by Visibility Level", show_header=True)
        vis_table.add_column("Flags", justify="right", style="cyan")
        vis_table.add_column("Level", style="yellow")
        vis_table.add_column("Count", justify="right", style="green")

        for vis_flags, count in sorted(summary['by_visibility'].items()):
            classification = classify_action_visibility(vis_flags)
            vis_table.add_row(
                str(vis_flags),
                classification['level'],
                str(count)
            )

        console.print(vis_table)

        # Top apps
        top_apps = sorted(summary['by_app'].items(), key=lambda x: x[1], reverse=True)[:10]
        app_table = Table(title="Top 10 Apps by Action Count", show_header=True)
        app_table.add_column("App", style="cyan")
        app_table.add_column("Actions", justify="right", style="green")

        for app, count in top_apps:
            app_table.add_row(app if app else "(Unknown)", str(count))

        console.print(app_table)

    else:
        # Simple text output
        print("\n" + "="*60)
        print("📊 EXTRACTION SUMMARY")
        print("="*60)
        print(f"Total Actions:      {summary['total_count']}")
        print(f"Hidden Actions:     {summary['hidden_count']}")
        print(f"Deprecated:         {summary['deprecated_count']}")
        print(f"With Parameters:    {summary['with_parameters']}")
        print("\nBy Type:")
        for action_type, count in sorted(summary['by_type'].items(), key=lambda x: x[1], reverse=True):
            print(f"  {action_type:20s} {count:4d}")
        print("="*60 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Extract Shortcuts actions from Tools-prod.sqlite",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument('--all', action='store_true', help='Extract all actions')
    parser.add_argument('--hidden', action='store_true', help='Extract only hidden actions')
    parser.add_argument('--csv', action='store_true', help='Also export as CSV')
    parser.add_argument('--no-protobuf', action='store_true', help='Skip protobuf decoding')
    parser.add_argument('--no-fix-localizations', action='store_true', help='Disable localization key fixing (default: enabled)')
    parser.add_argument('--limit', type=int, help='Limit number of actions (for testing)')
    parser.add_argument('--locale', default='en', help='Locale for localization (default: en)')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    parser.add_argument('--db', default='Tools-prod.sqlite', help='Database path')

    args = parser.parse_args()

    # Need at least one action
    if not (args.all or args.hidden):
        parser.print_help()
        sys.exit(1)

    try:
        if args.all:
            if args.verbose:
                print("\n🚀 Extracting all actions...")

            schemas = extract_all_actions(
                db_path=args.db,
                include_protobuf=not args.no_protobuf,
                fix_localizations=not args.no_fix_localizations,
                locale=args.locale,
                limit=args.limit,
                verbose=args.verbose,
            )

            # Export JSON
            export_to_json(schemas, 'output/actions_complete.json', args.verbose)

            # Export CSV if requested
            if args.csv:
                export_to_csv(schemas, 'output/actions_complete.csv', args.verbose)

            # Display summary
            display_summary(schemas)

        if args.hidden:
            if args.verbose:
                print("\n🔍 Extracting hidden actions...")

            conn = connect_db(args.db)
            hidden_data = get_hidden_actions(conn, args.locale)
            conn.close()

            hidden_schemas = []
            conn = connect_db(args.db)
            for action_data in hidden_data:
                schema = build_action_schema(conn, action_data, not args.no_protobuf, False, not args.no_fix_localizations, args.locale)
                hidden_schemas.append(schema)
            conn.close()

            # Export
            export_to_json(hidden_schemas, 'output/hidden_actions.json', args.verbose)

            if args.csv:
                export_to_csv(hidden_schemas, 'output/hidden_actions.csv', args.verbose)

            if args.verbose:
                print(f"\n✅ Found {len(hidden_schemas)} hidden actions")

        print("\n✨ Done!\n")

    except FileNotFoundError as e:
        print(f"\n❌ Error: {e}")
        print(f"   Make sure {args.db} exists in the current directory")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
