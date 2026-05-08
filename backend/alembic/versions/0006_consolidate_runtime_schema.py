"""consolidate runtime schema columns into alembic

Revision ID: 0006_consolidate_runtime_schema
Revises: 0005_course_assignments_admin_api
Create Date: 2026-05-08
"""

from alembic import op
import sqlalchemy as sa


revision = "0006_consolidate_runtime_schema"
down_revision = "0005_course_assignments_admin_api"
branch_labels = None
depends_on = None


def _table_exists(inspector: sa.Inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _column_exists(inspector: sa.Inspector, table_name: str, column_name: str) -> bool:
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def _add_column_if_missing(table_name: str, column: sa.Column) -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not _table_exists(inspector, table_name):
        return
    if _column_exists(inspector, table_name, column.name):
        return
    with op.batch_alter_table(table_name) as batch_op:
        batch_op.add_column(column)


def _drop_column_if_exists(table_name: str, column_name: str) -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not _table_exists(inspector, table_name):
        return
    if not _column_exists(inspector, table_name, column_name):
        return
    with op.batch_alter_table(table_name) as batch_op:
        batch_op.drop_column(column_name)


def upgrade() -> None:
    _add_column_if_missing("questions", sa.Column("shuffle_options", sa.Boolean(), nullable=False, server_default=sa.false()))
    _add_column_if_missing("tests", sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.false()))

    _add_column_if_missing("courses", sa.Column("image_url", sa.String(length=500), nullable=True))
    _add_column_if_missing("courses", sa.Column("status", sa.String(length=24), nullable=False, server_default="draft"))
    _add_column_if_missing("courses", sa.Column("category", sa.String(length=120), nullable=True))
    _add_column_if_missing("courses", sa.Column("access_settings", sa.JSON(), nullable=True))
    _add_column_if_missing("courses", sa.Column("available_from", sa.DateTime(), nullable=True))
    _add_column_if_missing("courses", sa.Column("available_to", sa.DateTime(), nullable=True))

    _add_column_if_missing("lessons", sa.Column("summary", sa.Text(), nullable=False, server_default=""))
    _add_column_if_missing("lessons", sa.Column("content_pages", sa.JSON(), nullable=True))
    _add_column_if_missing("lessons", sa.Column("duration_minutes", sa.Integer(), nullable=False, server_default="8"))
    _add_column_if_missing("lessons", sa.Column("image_url", sa.String(length=500), nullable=True))
    _add_column_if_missing("lessons", sa.Column("video_url", sa.String(length=500), nullable=True))
    _add_column_if_missing("lessons", sa.Column("section_id", sa.Integer(), nullable=True))
    _add_column_if_missing("lessons", sa.Column("is_visible", sa.Boolean(), nullable=False, server_default=sa.true()))
    _add_column_if_missing("lessons", sa.Column("is_published", sa.Boolean(), nullable=False, server_default=sa.true()))


def downgrade() -> None:
    _drop_column_if_exists("lessons", "is_published")
    _drop_column_if_exists("lessons", "is_visible")
    _drop_column_if_exists("lessons", "section_id")
    _drop_column_if_exists("lessons", "video_url")
    _drop_column_if_exists("lessons", "image_url")
    _drop_column_if_exists("lessons", "duration_minutes")
    _drop_column_if_exists("lessons", "content_pages")
    _drop_column_if_exists("lessons", "summary")

    _drop_column_if_exists("courses", "available_to")
    _drop_column_if_exists("courses", "available_from")
    _drop_column_if_exists("courses", "access_settings")
    _drop_column_if_exists("courses", "category")
    _drop_column_if_exists("courses", "status")
    _drop_column_if_exists("courses", "image_url")

    _drop_column_if_exists("tests", "is_active")
    _drop_column_if_exists("questions", "shuffle_options")
