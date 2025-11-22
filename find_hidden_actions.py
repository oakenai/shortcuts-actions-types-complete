#!/usr/bin/env python3
"""
Hidden Actions Finder

Discover and analyze hidden/undocumented Shortcuts actions.

Usage:
    python3 find_hidden_actions.py [options]

Options:
    --level N       Show actions with visibility >= N (default: all > 0)
    --experimental  Show only experimental actions (flags 13-15)
    --details       Show full details for each action
    -v, --verbose   Verbose output
"""

import sys
import json
import argparse
from pathlib import Path

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich import print as rprint
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

from utils.db_utils import connect_db, get_hidden_actions, get_action_parameters
from utils.schema_builder import build_action_schema, classify_action_visibility


def analyze_hidden_actions(db_path: str = "Tools-prod.sqlite", min_visibility: int = 1, verbose: bool = False):
    """Analyze hidden actions"""
    conn = connect_db(db_path)
    hidden_data = get_hidden_actions(conn)

    # Filter by minimum visibility
    filtered = [a for a in hidden_data if a['visibilityFlags'] >= min_visibility]

    # Group by visibility level
    by_visibility = {}
    for action in filtered:
        vis_flags = action['visibilityFlags']
        if vis_flags not in by_visibility:
            by_visibility[vis_flags] = []
        by_visibility[vis_flags].append(action)

    if RICH_AVAILABLE:
        console = Console()

        # Summary panel
        total_hidden = len(filtered)
        summary_text = f"""
[bold cyan]Total Hidden Actions:[/bold cyan] {total_hidden}
[bold yellow]Visibility Levels Found:[/bold yellow] {len(by_visibility)}
[bold green]Most Hidden (15):[/bold green] {len(by_visibility.get(15, []))}
        """
        console.print(Panel(summary_text.strip(), title="🔍 Hidden Actions Analysis", border_style="yellow"))

        # Table by visibility level
        for vis_flags in sorted(by_visibility.keys()):
            actions = by_visibility[vis_flags]
            classification = classify_action_visibility(vis_flags)

            table = Table(
                title=f"Visibility Level {vis_flags} - {classification['level'].upper()} ({len(actions)} actions)",
                show_header=True,
                border_style="yellow" if vis_flags >= 13 else "blue"
            )
            table.add_column("ID", style="cyan", max_width=50)
            table.add_column("Name", style="green")
            table.add_column("Type", style="magenta")
            table.add_column("App", style="yellow", max_width=30)

            for action in actions[:20]:  # Limit to 20 per level for readability
                table.add_row(
                    action['id'],
                    action.get('name') or '(no name)',
                    action['toolType'],
                    action.get('app_name') or '(unknown)'
                )

            if len(actions) > 20:
                table.add_row("[dim]...[/dim]", f"[dim]({len(actions)-20} more)[/dim]", "", "")

            console.print(table)
            console.print()

    else:
        # Simple text output
        print("\n" + "="*80)
        print(f"🔍 HIDDEN ACTIONS ANALYSIS")
        print("="*80)
        print(f"Total Hidden Actions: {len(filtered)}\n")

        for vis_flags in sorted(by_visibility.keys()):
            actions = by_visibility[vis_flags]
            classification = classify_action_visibility(vis_flags)

            print(f"\nVisibility Level {vis_flags} - {classification['level'].upper()}")
            print(f"Description: {classification['description']}")
            print(f"Count: {len(actions)}")
            print("-" * 80)

            for action in actions[:10]:
                print(f"  {action['id']}")
                print(f"    Name: {action.get('name') or '(no name)'}")
                print(f"    Type: {action['toolType']}")
                print(f"    App:  {action.get('app_name') or '(unknown)'}")
                print()

            if len(actions) > 10:
                print(f"  ... and {len(actions)-10} more\n")

    conn.close()
    return filtered


def show_action_details(db_path: str, action_id: str):
    """Show full details for a specific action"""
    conn = connect_db(db_path)

    # Get action
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            t.rowId,
            t.id,
            t.toolType,
            t.flags,
            t.visibilityFlags,
            tl.name,
            tl.descriptionSummary,
            cm.id as container_id
        FROM Tools t
        LEFT JOIN ToolLocalizations tl ON t.rowId = tl.toolId AND tl.locale = 'en'
        LEFT JOIN ContainerMetadata cm ON t.sourceContainerId = cm.rowId
        WHERE t.id = ?
    """, (action_id,))

    row = cursor.fetchone()
    if not row:
        print(f"❌ Action not found: {action_id}")
        return

    action_data = dict(row)

    # Get parameters
    parameters = get_action_parameters(conn, action_data['rowId'])

    if RICH_AVAILABLE:
        console = Console()

        # Action info panel
        classification = classify_action_visibility(action_data['visibilityFlags'])
        info_text = f"""
[bold cyan]ID:[/bold cyan] {action_data['id']}
[bold cyan]Name:[/bold cyan] {action_data.get('name') or '(no name)'}
[bold cyan]Type:[/bold cyan] {action_data['toolType']}
[bold cyan]App:[/bold cyan] {action_data['container_id']}
[bold yellow]Visibility Flags:[/bold yellow] {action_data['visibilityFlags']} ({classification['level']})
[bold yellow]Flags:[/bold yellow] {action_data['flags']}
[bold green]Description:[/bold green] {action_data.get('descriptionSummary') or '(none)'}
        """
        console.print(Panel(info_text.strip(), title=f"🔍 {action_data['id']}", border_style="yellow"))

        # Parameters table
        if parameters:
            param_table = Table(title=f"Parameters ({len(parameters)})", show_header=True)
            param_table.add_column("Key", style="cyan")
            param_table.add_column("Name", style="green")
            param_table.add_column("Order", justify="right", style="yellow")

            for param in parameters:
                param_table.add_row(
                    param['key'],
                    param.get('name') or '(no name)',
                    str(param['sortOrder'])
                )

            console.print(param_table)
        else:
            console.print("[dim]No parameters[/dim]")

    else:
        print(f"\n{'='*80}")
        print(f"Action: {action_data['id']}")
        print(f"{'='*80}")
        print(f"Name: {action_data.get('name') or '(no name)'}")
        print(f"Type: {action_data['toolType']}")
        print(f"Visibility Flags: {action_data['visibilityFlags']}")
        print(f"Parameters: {len(parameters)}")
        for param in parameters:
            print(f"  - {param['key']}: {param.get('name') or '(no name)'}")

    conn.close()


def main():
    parser = argparse.ArgumentParser(
        description="Find and analyze hidden Shortcuts actions",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument('--level', type=int, default=1, help='Minimum visibility level (default: 1)')
    parser.add_argument('--experimental', action='store_true', help='Show only experimental (13-15)')
    parser.add_argument('--details', metavar='ACTION_ID', help='Show details for specific action')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    parser.add_argument('--db', default='Tools-prod.sqlite', help='Database path')
    parser.add_argument('--export', metavar='FILE', help='Export to JSON file')

    args = parser.parse_args()

    try:
        if args.details:
            show_action_details(args.db, args.details)
        else:
            min_vis = 13 if args.experimental else args.level
            hidden_actions = analyze_hidden_actions(args.db, min_vis, args.verbose)

            if args.export:
                export_path = Path(args.export)
                export_path.parent.mkdir(parents=True, exist_ok=True)
                with open(export_path, 'w') as f:
                    json.dump(hidden_actions, f, indent=2, default=str)
                print(f"\n✅ Exported to {args.export}")

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
