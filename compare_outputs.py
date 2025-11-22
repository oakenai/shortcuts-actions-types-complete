#!/usr/bin/env python3
"""
Compare outputs between example-output and output directories to show sanitization improvements.
"""

import json
import sys
from collections import Counter
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
import re

console = Console()


def analyze_string_artifacts(strings):
    """Analyze strings for various types of artifacts"""
    artifacts = {
        'leading_digit': 0,
        'leading_dash': 0,
        'leading_hash': 0,
        'leading_dollar': 0,
        'leading_paren': 0,
        'trailing_asterisk': 0,
        'trailing_quote': 0,
        'total_with_artifacts': 0,
    }

    artifact_examples = {
        'leading_digit': [],
        'leading_dash': [],
        'leading_hash': [],
        'leading_dollar': [],
        'leading_paren': [],
        'trailing_asterisk': [],
        'trailing_quote': [],
    }

    for s in strings:
        has_artifact = False

        # Leading single digit
        if len(s) > 3 and s[0].isdigit() and not s[1].isdigit():
            artifacts['leading_digit'] += 1
            if len(artifact_examples['leading_digit']) < 3:
                artifact_examples['leading_digit'].append(s)
            has_artifact = True

        # Leading dash
        if s.startswith('-'):
            artifacts['leading_dash'] += 1
            if len(artifact_examples['leading_dash']) < 3:
                artifact_examples['leading_dash'].append(s)
            has_artifact = True

        # Leading hash
        if s.startswith('#'):
            artifacts['leading_hash'] += 1
            if len(artifact_examples['leading_hash']) < 3:
                artifact_examples['leading_hash'].append(s)
            has_artifact = True

        # Leading dollar
        if s.startswith('$'):
            artifacts['leading_dollar'] += 1
            if len(artifact_examples['leading_dollar']) < 3:
                artifact_examples['leading_dollar'].append(s)
            has_artifact = True

        # Leading parenthesis
        if s.startswith('('):
            artifacts['leading_paren'] += 1
            if len(artifact_examples['leading_paren']) < 3:
                artifact_examples['leading_paren'].append(s)
            has_artifact = True

        # Trailing asterisk
        if s.endswith('*'):
            artifacts['trailing_asterisk'] += 1
            if len(artifact_examples['trailing_asterisk']) < 3:
                artifact_examples['trailing_asterisk'].append(s)
            has_artifact = True

        # Trailing quote
        if s.endswith('"') or s.endswith("'"):
            artifacts['trailing_quote'] += 1
            if len(artifact_examples['trailing_quote']) < 3:
                artifact_examples['trailing_quote'].append(s)
            has_artifact = True

        if has_artifact:
            artifacts['total_with_artifacts'] += 1

    return artifacts, artifact_examples


def compare_files(old_path, new_path):
    """Compare two JSON files and show differences"""

    console.print("\n[bold cyan]Loading files...[/bold cyan]")

    with open(old_path) as f:
        old_data = json.load(f)

    with open(new_path) as f:
        new_data = json.load(f)

    console.print(f"✓ Loaded {len(old_data)} actions from {old_path}")
    console.print(f"✓ Loaded {len(new_data)} actions from {new_path}\n")

    # Collect all strings from type_info
    old_strings = []
    new_strings = []

    for action in old_data:
        for param in action.get('parameters', []):
            ti = param.get('type_info', {})
            old_strings.extend(ti.get('strings', []))

    for action in new_data:
        for param in action.get('parameters', []):
            ti = param.get('type_info', {})
            new_strings.extend(ti.get('strings', []))

    # Analyze artifacts
    old_artifacts, old_examples = analyze_string_artifacts(old_strings)
    new_artifacts, new_examples = analyze_string_artifacts(new_strings)

    # Display summary
    console.print(Panel.fit(
        "[bold]Sanitization Comparison Report[/bold]",
        border_style="cyan"
    ))

    # Create comparison table
    table = Table(title="Artifact Statistics", show_header=True)
    table.add_column("Artifact Type", style="cyan", width=25)
    table.add_column("Before", justify="right", style="red")
    table.add_column("After", justify="right", style="green")
    table.add_column("Removed", justify="right", style="yellow")
    table.add_column("% Reduction", justify="right", style="magenta")

    artifact_types = [
        ('Total Strings', len(old_strings), len(new_strings)),
        ('With Artifacts', old_artifacts['total_with_artifacts'], new_artifacts['total_with_artifacts']),
        ('Leading Digit (0-9)', old_artifacts['leading_digit'], new_artifacts['leading_digit']),
        ('Leading Dash (-)', old_artifacts['leading_dash'], new_artifacts['leading_dash']),
        ('Leading Hash (#)', old_artifacts['leading_hash'], new_artifacts['leading_hash']),
        ('Leading Dollar ($)', old_artifacts['leading_dollar'], new_artifacts['leading_dollar']),
        ('Leading Paren (()', old_artifacts['leading_paren'], new_artifacts['leading_paren']),
        ('Trailing Asterisk (*)', old_artifacts['trailing_asterisk'], new_artifacts['trailing_asterisk']),
        ('Trailing Quote ("\')', old_artifacts['trailing_quote'], new_artifacts['trailing_quote']),
    ]

    for name, before, after in artifact_types:
        removed = before - after
        if before > 0:
            reduction = (removed / before) * 100
        else:
            reduction = 0

        table.add_row(
            name,
            str(before),
            str(after),
            str(removed) if removed > 0 else "0",
            f"{reduction:.1f}%" if reduction > 0 else "0%"
        )

    console.print(table)

    # Show examples
    console.print("\n[bold cyan]Examples of Removed Artifacts:[/bold cyan]\n")

    examples_to_show = [
        ('Leading Digit', old_examples['leading_digit']),
        ('Leading Dash', old_examples['leading_dash']),
        ('Leading Hash', old_examples['leading_hash']),
        ('Leading Dollar', old_examples['leading_dollar']),
        ('Leading Paren', old_examples['leading_paren']),
        ('Trailing Asterisk', old_examples['trailing_asterisk']),
        ('Trailing Quote', old_examples['trailing_quote']),
    ]

    for artifact_type, examples in examples_to_show:
        if examples:
            console.print(f"[yellow]{artifact_type}:[/yellow]")
            for ex in examples[:3]:
                # Find cleaned version in new data
                cleaned = re.sub(r'^[0-9\-#$\(]+|[\*"\']$', '', ex).strip()
                console.print(f"  [red]✗[/red] {repr(ex)} → [green]✓[/green] {repr(cleaned)}")
            console.print()

    # Overall statistics
    console.print("\n[bold]Overall Impact:[/bold]")
    total_removed = len(old_strings) - len(new_strings)
    artifacts_removed = old_artifacts['total_with_artifacts'] - new_artifacts['total_with_artifacts']

    if len(old_strings) > 0:
        artifact_rate_old = (old_artifacts['total_with_artifacts'] / len(old_strings)) * 100
        artifact_rate_new = (new_artifacts['total_with_artifacts'] / len(new_strings)) * 100 if len(new_strings) > 0 else 0

        console.print(f"  • Total strings removed: [yellow]{total_removed}[/yellow]")
        console.print(f"  • Artifacts cleaned: [yellow]{artifacts_removed}[/yellow]")
        console.print(f"  • Artifact rate: [red]{artifact_rate_old:.1f}%[/red] → [green]{artifact_rate_new:.1f}%[/green]")
        console.print(f"  • Improvement: [cyan]{artifact_rate_old - artifact_rate_new:.1f} percentage points[/cyan]")

    # File size comparison
    import os
    old_size = os.path.getsize(old_path)
    new_size = os.path.getsize(new_path)
    size_diff = old_size - new_size
    size_reduction = (size_diff / old_size) * 100 if old_size > 0 else 0

    console.print(f"\n[bold]File Size:[/bold]")
    console.print(f"  • Before: [red]{old_size / 1024 / 1024:.2f} MB[/red]")
    console.print(f"  • After: [green]{new_size / 1024 / 1024:.2f} MB[/green]")
    console.print(f"  • Reduced by: [yellow]{size_diff / 1024:.1f} KB ({size_reduction:.1f}%)[/yellow]")


if __name__ == "__main__":
    old_file = "example-output/actions_complete.json"
    new_file = "output/actions_complete.json"

    try:
        compare_files(old_file, new_file)
        console.print("\n[bold green]✓ Comparison complete![/bold green]\n")
    except FileNotFoundError as e:
        console.print(f"[bold red]Error: {e}[/bold red]")
        console.print("Make sure both example-output/actions_complete.json and output/actions_complete.json exist.")
        sys.exit(1)
    except Exception as e:
        console.print(f"[bold red]Error: {e}[/bold red]")
        sys.exit(1)
