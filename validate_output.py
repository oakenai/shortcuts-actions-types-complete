#!/usr/bin/env python3
"""
Output Validator

Validate extracted action schemas and generate quality reports.

Usage:
    python3 validate_output.py [options]

Options:
    --input FILE      Input JSON file (default: output/actions_complete.json)
    --report FILE     Output validation report
    --show-issues     Show actions with issues
    -v, --verbose     Verbose output
"""

import sys
import json
import argparse
from pathlib import Path

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

from utils.validators import validate_action_schema, generate_validation_report, is_localization_key


def main():
    parser = argparse.ArgumentParser(
        description="Validate extracted action schemas"
    )

    parser.add_argument('--input', default='output/actions_complete.json', help='Input JSON file')
    parser.add_argument('--report', help='Output validation report JSON')
    parser.add_argument('--show-issues', action='store_true', help='Show actions with issues')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')

    args = parser.parse_args()

    try:
        # Load schemas
        with open(args.input) as f:
            schemas = json.load(f)

        print(f"\n📋 Validating {len(schemas)} actions...\n")

        # Generate report
        report = generate_validation_report(schemas)

        # Display summary
        if RICH_AVAILABLE:
            console = Console()

            summary_text = f"""
[bold cyan]Total Schemas:[/bold cyan] {report['total_schemas']}
[bold green]Valid:[/bold green] {report['valid_schemas']} ({report['valid_schemas']*100//report['total_schemas']}%)
[bold yellow]With Issues:[/bold yellow] {report['schemas_with_issues']}
[bold yellow]With Warnings:[/bold yellow] {report['schemas_with_warnings']}
[bold blue]Average Quality:[/bold blue] {report['average_quality']:.1f}/100
            """
            console.print(Panel(summary_text.strip(), title="✅ Validation Summary", border_style="green"))

            # Quality distribution
            qual_table = Table(title="Quality Score Distribution")
            qual_table.add_column("Category", style="cyan")
            qual_table.add_column("Score Range", style="yellow")
            qual_table.add_column("Count", justify="right", style="green")

            qual_table.add_row("Excellent", "90-100", str(report['quality_scores']['excellent']))
            qual_table.add_row("Good", "75-89", str(report['quality_scores']['good']))
            qual_table.add_row("Fair", "60-74", str(report['quality_scores']['fair']))
            qual_table.add_row("Poor", "<60", str(report['quality_scores']['poor']))

            console.print(qual_table)

            # Issues by type
            if report['issues_by_type']:
                issues_table = Table(title="Issues by Type")
                issues_table.add_column("Issue Type", style="cyan")
                issues_table.add_column("Count", justify="right", style="red")

                for issue_type, count in sorted(report['issues_by_type'].items(), key=lambda x: x[1], reverse=True):
                    issues_table.add_row(issue_type, str(count))

                console.print(issues_table)

            # Warnings by type
            if report['warnings_by_type']:
                warn_table = Table(title="Warnings by Type")
                warn_table.add_column("Warning Type", style="cyan")
                warn_table.add_column("Count", justify="right", style="yellow")

                for warn_type, count in sorted(report['warnings_by_type'].items(), key=lambda x: x[1], reverse=True):
                    warn_table.add_row(warn_type, str(count))

                console.print(warn_table)

            # Problematic actions
            if report['problematic_actions'] and args.show_issues:
                prob_table = Table(title="Problematic Actions (Quality < 60)")
                prob_table.add_column("ID", style="cyan", max_width=40)
                prob_table.add_column("Name", style="yellow", max_width=30)
                prob_table.add_column("Quality", justify="right", style="red")
                prob_table.add_column("Issues", justify="right")
                prob_table.add_column("Warnings", justify="right")

                for action in report['problematic_actions']:
                    prob_table.add_row(
                        action['id'],
                        action.get('name') or '(no name)',
                        f"{action['quality']:.0f}",
                        str(action['issues']),
                        str(action['warnings'])
                    )

                console.print(prob_table)

        else:
            # Simple text output
            print("="*60)
            print("VALIDATION SUMMARY")
            print("="*60)
            print(f"Total Schemas: {report['total_schemas']}")
            print(f"Valid: {report['valid_schemas']}")
            print(f"With Issues: {report['schemas_with_issues']}")
            print(f"Average Quality: {report['average_quality']:.1f}/100")
            print()
            print("Quality Distribution:")
            for cat, count in report['quality_scores'].items():
                print(f"  {cat}: {count}")

        # Export report if requested
        if args.report:
            with open(args.report, 'w') as f:
                json.dump(report, f, indent=2)
            print(f"\n✅ Report exported to {args.report}")

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
