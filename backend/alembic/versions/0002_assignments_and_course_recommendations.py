"""add assignments domain and course recommendation links

Revision ID: 0002_assignments_and_course_recommendations
Revises: 0001_initial
Create Date: 2026-05-05
"""

from alembic import op
import sqlalchemy as sa


revision = "0002_assignments_and_course_recommendations"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def _table_exists(inspector: sa.Inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _index_exists(inspector: sa.Inspector, table_name: str, index_name: str) -> bool:
    indexes = inspector.get_indexes(table_name)
    return any(item["name"] == index_name for item in indexes)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _table_exists(inspector, "assignments"):
        op.create_table(
            "assignments",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
            sa.Column("course_id", sa.Integer(), sa.ForeignKey("courses.id"), nullable=False),
            sa.Column("lesson_id", sa.Integer(), sa.ForeignKey("lessons.id"), nullable=True),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("description", sa.Text(), nullable=False, server_default=""),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("due_at", sa.DateTime(), nullable=True),
            sa.Column("created_by_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        )
    inspector = sa.inspect(bind)
    if not _index_exists(inspector, "assignments", "ix_assignments_tenant_id"):
        op.create_index("ix_assignments_tenant_id", "assignments", ["tenant_id"])
    if not _index_exists(inspector, "assignments", "ix_assignments_course_id"):
        op.create_index("ix_assignments_course_id", "assignments", ["course_id"])
    if not _index_exists(inspector, "assignments", "ix_assignments_lesson_id"):
        op.create_index("ix_assignments_lesson_id", "assignments", ["lesson_id"])
    if not _index_exists(inspector, "assignments", "ix_assignments_title"):
        op.create_index("ix_assignments_title", "assignments", ["title"])
    if not _index_exists(inspector, "assignments", "ix_assignments_is_active"):
        op.create_index("ix_assignments_is_active", "assignments", ["is_active"])
    if not _index_exists(inspector, "assignments", "ix_assignments_created_at"):
        op.create_index("ix_assignments_created_at", "assignments", ["created_at"])

    inspector = sa.inspect(bind)
    if not _table_exists(inspector, "assignment_submissions"):
        op.create_table(
            "assignment_submissions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
            sa.Column("assignment_id", sa.Integer(), sa.ForeignKey("assignments.id"), nullable=False),
            sa.Column("student_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="not_started"),
            sa.Column("text_answer", sa.Text(), nullable=False, server_default=""),
            sa.Column("link_answer", sa.String(length=500), nullable=True),
            sa.Column("submitted_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.UniqueConstraint("tenant_id", "assignment_id", "student_user_id", name="uq_assignment_submission"),
        )
    inspector = sa.inspect(bind)
    if not _index_exists(inspector, "assignment_submissions", "ix_assignment_submissions_tenant_id"):
        op.create_index("ix_assignment_submissions_tenant_id", "assignment_submissions", ["tenant_id"])
    if not _index_exists(inspector, "assignment_submissions", "ix_assignment_submissions_assignment_id"):
        op.create_index("ix_assignment_submissions_assignment_id", "assignment_submissions", ["assignment_id"])
    if not _index_exists(inspector, "assignment_submissions", "ix_assignment_submissions_student_user_id"):
        op.create_index("ix_assignment_submissions_student_user_id", "assignment_submissions", ["student_user_id"])
    if not _index_exists(inspector, "assignment_submissions", "ix_assignment_submissions_status"):
        op.create_index("ix_assignment_submissions_status", "assignment_submissions", ["status"])
    if not _index_exists(inspector, "assignment_submissions", "ix_assignment_submissions_updated_at"):
        op.create_index("ix_assignment_submissions_updated_at", "assignment_submissions", ["updated_at"])

    inspector = sa.inspect(bind)
    if not _table_exists(inspector, "assignment_submission_files"):
        op.create_table(
            "assignment_submission_files",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
            sa.Column("submission_id", sa.Integer(), sa.ForeignKey("assignment_submissions.id"), nullable=False),
            sa.Column("file_url", sa.String(length=500), nullable=False),
            sa.Column("file_name", sa.String(length=255), nullable=False, server_default=""),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        )
    inspector = sa.inspect(bind)
    if not _index_exists(inspector, "assignment_submission_files", "ix_assignment_submission_files_tenant_id"):
        op.create_index("ix_assignment_submission_files_tenant_id", "assignment_submission_files", ["tenant_id"])
    if not _index_exists(inspector, "assignment_submission_files", "ix_assignment_submission_files_submission_id"):
        op.create_index("ix_assignment_submission_files_submission_id", "assignment_submission_files", ["submission_id"])
    if not _index_exists(inspector, "assignment_submission_files", "ix_assignment_submission_files_created_at"):
        op.create_index("ix_assignment_submission_files_created_at", "assignment_submission_files", ["created_at"])

    inspector = sa.inspect(bind)
    if not _table_exists(inspector, "submission_reviews"):
        op.create_table(
            "submission_reviews",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
            sa.Column("submission_id", sa.Integer(), sa.ForeignKey("assignment_submissions.id"), nullable=False),
            sa.Column("reviewer_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False),
            sa.Column("comment", sa.Text(), nullable=False, server_default=""),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        )
    inspector = sa.inspect(bind)
    if not _index_exists(inspector, "submission_reviews", "ix_submission_reviews_tenant_id"):
        op.create_index("ix_submission_reviews_tenant_id", "submission_reviews", ["tenant_id"])
    if not _index_exists(inspector, "submission_reviews", "ix_submission_reviews_submission_id"):
        op.create_index("ix_submission_reviews_submission_id", "submission_reviews", ["submission_id"])
    if not _index_exists(inspector, "submission_reviews", "ix_submission_reviews_reviewer_user_id"):
        op.create_index("ix_submission_reviews_reviewer_user_id", "submission_reviews", ["reviewer_user_id"])
    if not _index_exists(inspector, "submission_reviews", "ix_submission_reviews_status"):
        op.create_index("ix_submission_reviews_status", "submission_reviews", ["status"])
    if not _index_exists(inspector, "submission_reviews", "ix_submission_reviews_created_at"):
        op.create_index("ix_submission_reviews_created_at", "submission_reviews", ["created_at"])

    inspector = sa.inspect(bind)
    if not _table_exists(inspector, "course_recommendations"):
        op.create_table(
            "course_recommendations",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
            sa.Column("course_id", sa.Integer(), sa.ForeignKey("courses.id"), nullable=False),
            sa.Column("recommendation_id", sa.Integer(), sa.ForeignKey("editor_recommendations.id"), nullable=False),
            sa.UniqueConstraint("tenant_id", "course_id", "recommendation_id", name="uq_course_recommendation"),
        )
    inspector = sa.inspect(bind)
    if not _index_exists(inspector, "course_recommendations", "ix_course_recommendations_tenant_id"):
        op.create_index("ix_course_recommendations_tenant_id", "course_recommendations", ["tenant_id"])
    if not _index_exists(inspector, "course_recommendations", "ix_course_recommendations_course_id"):
        op.create_index("ix_course_recommendations_course_id", "course_recommendations", ["course_id"])
    if not _index_exists(inspector, "course_recommendations", "ix_course_recommendations_recommendation_id"):
        op.create_index("ix_course_recommendations_recommendation_id", "course_recommendations", ["recommendation_id"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _table_exists(inspector, "course_recommendations"):
        op.drop_table("course_recommendations")

    inspector = sa.inspect(bind)
    if _table_exists(inspector, "submission_reviews"):
        op.drop_table("submission_reviews")

    inspector = sa.inspect(bind)
    if _table_exists(inspector, "assignment_submission_files"):
        op.drop_table("assignment_submission_files")

    inspector = sa.inspect(bind)
    if _table_exists(inspector, "assignment_submissions"):
        op.drop_table("assignment_submissions")

    inspector = sa.inspect(bind)
    if _table_exists(inspector, "assignments"):
        op.drop_table("assignments")
