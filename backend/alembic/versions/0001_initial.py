"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-04-04
"""

from alembic import op
import sqlalchemy as sa


revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tenants",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("locale", sa.String(length=8), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
    )
    op.create_index("ix_tenants_name", "tenants", ["name"], unique=True)
    op.create_index("ix_tenants_code", "tenants", ["code"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_tenants_code", table_name="tenants")
    op.drop_index("ix_tenants_name", table_name="tenants")
    op.drop_table("tenants")
