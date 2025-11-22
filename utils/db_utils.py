"""Database utility functions for accessing Tools-prod.sqlite"""

import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Any


def connect_db(db_path: str = "Tools-prod.sqlite") -> sqlite3.Connection:
    """
    Connect to the Tools-prod.sqlite database.

    Args:
        db_path: Path to the database file

    Returns:
        SQLite connection object

    Raises:
        FileNotFoundError: If database file doesn't exist
    """
    path = Path(db_path)
    if not path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # Access columns by name
    return conn


def get_action_count(conn: sqlite3.Connection) -> int:
    """Get total number of actions in the database"""
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM Tools")
    return cursor.fetchone()[0]


def get_type_count(conn: sqlite3.Connection) -> int:
    """Get total number of types in the database"""
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM Types")
    return cursor.fetchone()[0]


def get_all_actions(conn: sqlite3.Connection, locale: str = "en") -> List[Dict[str, Any]]:
    """
    Get all actions with their basic information.

    Args:
        conn: Database connection
        locale: Language locale (default: 'en')

    Returns:
        List of action dictionaries
    """
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            t.rowId,
            t.id,
            t.toolType,
            t.flags,
            t.visibilityFlags,
            t.deprecationReplacementId,
            t.sourceActionProvider,
            tl.name,
            tl.descriptionSummary,
            tl.descriptionNote,
            tl.deprecationMessage,
            cm.id as container_id,
            cml.name as app_name
        FROM Tools t
        LEFT JOIN ToolLocalizations tl
            ON t.rowId = tl.toolId
            AND tl.locale = ?
            AND tl.localizationUsage = 'display'
        LEFT JOIN ContainerMetadata cm
            ON t.sourceContainerId = cm.rowId
        LEFT JOIN ContainerMetadataLocalizations cml
            ON cm.rowId = cml.containerId
            AND cml.locale = ?
        ORDER BY t.id
    """, (locale, locale))

    actions = []
    for row in cursor.fetchall():
        actions.append(dict(row))

    return actions


def get_action_parameters(conn: sqlite3.Connection, tool_id: int, locale: str = "en") -> List[Dict[str, Any]]:
    """
    Get all parameters for a specific action.

    Args:
        conn: Database connection
        tool_id: Action row ID
        locale: Language locale

    Returns:
        List of parameter dictionaries
    """
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            p.key,
            p.sortOrder,
            p.flags,
            p.typeInstance,
            p.relationships,
            pl.name,
            pl.description
        FROM Parameters p
        LEFT JOIN ParameterLocalizations pl
            ON p.toolId = pl.toolId
            AND p.key = pl.key
            AND pl.locale = ?
        WHERE p.toolId = ?
        ORDER BY p.sortOrder
    """, (locale, tool_id))

    parameters = []
    for row in cursor.fetchall():
        param = dict(row)
        # Convert BLOB to bytes
        param['typeInstance'] = bytes(param['typeInstance']) if param['typeInstance'] else None
        param['relationships'] = bytes(param['relationships']) if param['relationships'] else None
        parameters.append(param)

    return parameters


def get_parameter_types(conn: sqlite3.Connection, tool_id: int, param_key: str) -> List[str]:
    """
    Get accepted types for a parameter.

    Args:
        conn: Database connection
        tool_id: Action row ID
        param_key: Parameter key

    Returns:
        List of type identifiers
    """
    cursor = conn.cursor()
    cursor.execute("""
        SELECT typeId
        FROM ToolParameterTypes
        WHERE toolId = ? AND key = ?
    """, (tool_id, param_key))

    return [row[0] for row in cursor.fetchall()]


def get_action_output_types(conn: sqlite3.Connection, tool_id: int) -> List[str]:
    """
    Get output types for an action.

    Args:
        conn: Database connection
        tool_id: Action row ID

    Returns:
        List of output type identifiers
    """
    cursor = conn.cursor()
    cursor.execute("""
        SELECT typeIdentifier
        FROM ToolOutputTypes
        WHERE toolId = ?
    """, (tool_id,))

    return [row[0] for row in cursor.fetchall()]


def get_action_categories(conn: sqlite3.Connection, tool_id: int, locale: str = "en") -> List[str]:
    """Get categories for an action"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT category
        FROM Categories
        WHERE toolId = ? AND locale = ?
    """, (tool_id, locale))

    return [row[0] for row in cursor.fetchall()]


def get_action_keywords(conn: sqlite3.Connection, tool_id: int, locale: str = "en") -> List[str]:
    """Get search keywords for an action"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT keyword
        FROM SearchKeywords
        WHERE toolId = ? AND locale = ?
        ORDER BY `order`
    """, (tool_id, locale))

    return [row[0] for row in cursor.fetchall()]


def get_hidden_actions(conn: sqlite3.Connection, locale: str = "en") -> List[Dict[str, Any]]:
    """
    Get all actions with non-zero visibility flags (potentially hidden).

    Args:
        conn: Database connection
        locale: Language locale

    Returns:
        List of hidden action dictionaries
    """
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            t.rowId,
            t.id,
            t.toolType,
            t.visibilityFlags,
            t.flags,
            tl.name,
            tl.descriptionSummary,
            cm.id as container_id,
            cml.name as app_name
        FROM Tools t
        LEFT JOIN ToolLocalizations tl
            ON t.rowId = tl.toolId
            AND tl.locale = ?
            AND tl.localizationUsage = 'display'
        LEFT JOIN ContainerMetadata cm
            ON t.sourceContainerId = cm.rowId
        LEFT JOIN ContainerMetadataLocalizations cml
            ON cm.rowId = cml.containerId
            AND cml.locale = ?
        WHERE t.visibilityFlags > 0
        ORDER BY t.visibilityFlags DESC, t.id
    """, (locale, locale))

    actions = []
    for row in cursor.fetchall():
        actions.append(dict(row))

    return actions


def get_type_info(conn: sqlite3.Connection, type_id: str) -> Optional[Dict[str, Any]]:
    """
    Get information about a specific type.

    Args:
        conn: Database connection
        type_id: Type identifier

    Returns:
        Type information dictionary or None
    """
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            t.rowId,
            t.id,
            t.kind,
            t.runtimeFlags,
            t.runtimeRequirements,
            tdr.name,
            cm.id as container_id
        FROM Types t
        LEFT JOIN TypeDisplayRepresentations tdr
            ON t.rowId = tdr.typeId
            AND tdr.locale = 'en'
        LEFT JOIN ContainerMetadata cm
            ON t.sourceContainerId = cm.rowId
        WHERE t.rowId = ?
    """, (type_id,))

    row = cursor.fetchone()
    if row:
        type_info = dict(row)
        # Convert BLOB to bytes
        if type_info['id']:
            type_info['id'] = bytes(type_info['id'])
        if type_info['runtimeRequirements']:
            type_info['runtimeRequirements'] = bytes(type_info['runtimeRequirements'])
        return type_info
    return None


def get_entity_properties(conn: sqlite3.Connection, type_id: str, locale: str = "en") -> List[Dict[str, Any]]:
    """Get properties for an entity type"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            ep.id,
            epl.displayName
        FROM EntityProperties ep
        LEFT JOIN EntityPropertyLocalizations epl
            ON ep.id = epl.propertyId
            AND ep.typeId = epl.typeId
            AND epl.locale = ?
        WHERE ep.typeId = ?
        ORDER BY ep.id
    """, (locale, type_id))

    properties = []
    for row in cursor.fetchall():
        properties.append(dict(row))

    return properties


def get_enum_cases(conn: sqlite3.Connection, type_id: str, locale: str = "en") -> List[Dict[str, Any]]:
    """Get enum cases for an enum type"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            id,
            title,
            subtitle
        FROM EnumerationCases
        WHERE typeId = ? AND locale = ?
        ORDER BY id
    """, (type_id, locale))

    cases = []
    for row in cursor.fetchall():
        cases.append(dict(row))

    return cases
