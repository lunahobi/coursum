from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


RUNTIME_COLUMN_DEFINITIONS_SQLITE = {
    "assignments": {
        "page_id": "VARCHAR(120)",
    },
    "courses": {
        "image_url": "VARCHAR(500)",
        "status": "VARCHAR(24) NOT NULL DEFAULT 'draft'",
        "category": "VARCHAR(120)",
        "access_settings": "JSON",
        "available_from": "DATETIME",
        "available_to": "DATETIME",
    },
    "lessons": {
        "summary": "TEXT NOT NULL DEFAULT ''",
        "content_pages": "JSON",
        "duration_minutes": "INTEGER NOT NULL DEFAULT 8",
        "image_url": "VARCHAR(500)",
        "video_url": "VARCHAR(500)",
        "section_id": "INTEGER",
        "is_visible": "BOOLEAN NOT NULL DEFAULT 1",
        "is_published": "BOOLEAN NOT NULL DEFAULT 1",
    },
}


RUNTIME_COLUMN_DEFINITIONS_POSTGRES = {
    "assignments": {
        "page_id": "VARCHAR(120)",
    },
    "courses": {
        "image_url": "VARCHAR(500)",
        "status": "VARCHAR(24) NOT NULL DEFAULT 'draft'",
        "category": "VARCHAR(120)",
        "access_settings": "JSONB",
        "available_from": "TIMESTAMP",
        "available_to": "TIMESTAMP",
    },
    "lessons": {
        "summary": "TEXT NOT NULL DEFAULT ''",
        "content_pages": "JSONB",
        "duration_minutes": "INTEGER NOT NULL DEFAULT 8",
        "image_url": "VARCHAR(500)",
        "video_url": "VARCHAR(500)",
        "section_id": "INTEGER",
        "is_visible": "BOOLEAN NOT NULL DEFAULT TRUE",
        "is_published": "BOOLEAN NOT NULL DEFAULT TRUE",
    },
}


def _runtime_column_definitions(engine: Engine) -> dict[str, dict[str, str]]:
    if engine.dialect.name == "postgresql":
        return RUNTIME_COLUMN_DEFINITIONS_POSTGRES
    return RUNTIME_COLUMN_DEFINITIONS_SQLITE


def ensure_runtime_schema(engine: Engine) -> None:
    runtime_column_definitions = _runtime_column_definitions(engine)
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    if not existing_tables:
        return

    existing_columns_by_table = {
        table_name: {column["name"] for column in inspector.get_columns(table_name)}
        for table_name in runtime_column_definitions
        if table_name in existing_tables
    }
    with engine.begin() as connection:
        for table_name, definitions in runtime_column_definitions.items():
            existing_columns = existing_columns_by_table.get(table_name)
            if existing_columns is None:
                continue
            for column_name, column_definition in definitions.items():
                if column_name not in existing_columns:
                    connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}"))

        if "lessons" in existing_columns_by_table:
            connection.execute(text("UPDATE lessons SET summary = SUBSTR(content, 1, 220) WHERE summary = ''"))
        if "courses" in existing_columns_by_table:
            if engine.dialect.name == "postgresql":
                connection.execute(
                    text(
                        "UPDATE courses "
                        "SET status = CASE WHEN is_published = TRUE THEN 'published' ELSE 'draft' END "
                        "WHERE status IS NULL OR status = ''"
                    )
                )
            else:
                connection.execute(
                    text(
                        "UPDATE courses "
                        "SET status = CASE WHEN is_published = 1 THEN 'published' ELSE 'draft' END "
                        "WHERE status IS NULL OR status = ''"
                    )
                )
