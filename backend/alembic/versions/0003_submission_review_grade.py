"""add grade column to submission_reviews

Revision ID: 0003_submission_review_grade
Revises: 0002_assignments_and_course_recommendations
Create Date: 2026-05-06
"""

from alembic import op
import sqlalchemy as sa


revision = "0003_submission_review_grade"
down_revision = "0002_assignments_and_course_recommendations"
branch_labels = None
depends_on = None


def _table_exists(inspector: sa.Inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _column_exists(inspector: sa.Inspector, table_name: str, column_name: str) -> bool:
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not _table_exists(inspector, "submission_reviews"):
        return
    if not _column_exists(inspector, "submission_reviews", "grade"):
        with op.batch_alter_table("submission_reviews") as batch_op:
            batch_op.add_column(sa.Column("grade", sa.Integer(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not _table_exists(inspector, "submission_reviews"):
        return
    if _column_exists(inspector, "submission_reviews", "grade"):
        with op.batch_alter_table("submission_reviews") as batch_op:
            batch_op.drop_column("grade")
