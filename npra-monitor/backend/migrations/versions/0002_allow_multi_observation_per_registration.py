"""allow multiple distinct observations for one registration in a source document

Revision ID: 0002
Revises: 0001
"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("product_observations", sa.Column("observation_key", sa.String(length=64), nullable=True))
    op.add_column("product_observations", sa.Column("source_row", sa.Integer(), nullable=True))
    # Preserve already-imported rows on an in-place development upgrade. Their
    # legacy keys are unique; fresh/retried imports use a deterministic SHA-256 key.
    op.execute("UPDATE product_observations SET observation_key = 'legacy-' || id::text WHERE observation_key IS NULL")
    op.alter_column("product_observations", "observation_key", nullable=False)
    op.drop_constraint("uq_observation_document_registration", "product_observations", type_="unique")
    op.create_unique_constraint(
        "uq_observation_document_key",
        "product_observations",
        ["source_document_id", "observation_key"],
    )


def downgrade():
    op.drop_constraint("uq_observation_document_key", "product_observations", type_="unique")
    op.create_unique_constraint(
        "uq_observation_document_registration",
        "product_observations",
        ["source_document_id", "registration_no"],
    )
    op.drop_column("product_observations", "source_row")
    op.drop_column("product_observations", "observation_key")
