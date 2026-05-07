"""add page_id column to assignments

Revision ID: 0004_assignment_page_id
Revises: 0003_submission_review_grade
Create Date: 2026-05-07
"""

from alembic import op
import sqlalchemy as sa


revision = "0004_assignment_page_id"
down_revision = "0003_submission_review_grade"
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
    if not _table_exists(inspector, "assignments"):
        return
    if not _column_exists(inspector, "assignments", "page_id"):
        with op.batch_alter_table("assignments") as batch_op:
            batch_op.add_column(sa.Column("page_id", sa.String(length=120), nullable=True))

    inspector = sa.inspect(bind)
    if _column_exists(inspector, "assignments", "page_id") and not _index_exists(inspector, "assignments", "ix_assignments_page_id"):
        with op.batch_alter_table("assignments") as batch_op:
            batch_op.create_index("ix_assignments_page_id", ["page_id"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not _table_exists(inspector, "assignments"):
        return
    if _index_exists(inspector, "assignments", "ix_assignments_page_id"):
        with op.batch_alter_table("assignments") as batch_op:
            batch_op.drop_index("ix_assignments_page_id")

    inspector = sa.inspect(bind)
    if _column_exists(inspector, "assignments", "page_id"):
        with op.batch_alter_table("assignments") as batch_op:
            batch_op.drop_column("page_id")
