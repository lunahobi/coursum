"""add course assignment created_at

Revision ID: 0005_course_assignments_admin_api
Revises: 0004_assignment_page_id
Create Date: 2026-05-08
"""

from alembic import op
import sqlalchemy as sa


revision = "0005_course_assignments_admin_api"
down_revision = "0004_assignment_page_id"
branch_labels = None
depends_on = None


def _table_exists(inspector: sa.Inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _column_exists(inspector: sa.Inspector, table_name: str, column_name: str) -> bool:
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def _index_exists(inspector: sa.Inspector, table_name: str, index_name: str) -> bool:
    return any(index["name"] == index_name for index in inspector.get_indexes(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not _table_exists(inspector, "course_assignments"):
        return
    if not _column_exists(inspector, "course_assignments", "created_at"):
        with op.batch_alter_table("course_assignments") as batch_op:
            batch_op.add_column(sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")))

    inspector = sa.inspect(bind)
    if _column_exists(inspector, "course_assignments", "created_at") and not _index_exists(
        inspector, "course_assignments", "ix_course_assignments_created_at"
    ):
        with op.batch_alter_table("course_assignments") as batch_op:
            batch_op.create_index("ix_course_assignments_created_at", ["created_at"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not _table_exists(inspector, "course_assignments"):
        return
    if _index_exists(inspector, "course_assignments", "ix_course_assignments_created_at"):
        with op.batch_alter_table("course_assignments") as batch_op:
            batch_op.drop_index("ix_course_assignments_created_at")

    inspector = sa.inspect(bind)
    if _column_exists(inspector, "course_assignments", "created_at"):
        with op.batch_alter_table("course_assignments") as batch_op:
            batch_op.drop_column("created_at")
