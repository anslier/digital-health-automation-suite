"""initial NPRA schema

Revision ID: 0001
Revises:

Important: this migration intentionally describes the ORIGINAL 0001 schema
explicitly. Do not import Base/current ORM models here, because historical
migrations must not change when later models change.
"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "source_documents",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("meeting_number", sa.Integer(), nullable=False),
        sa.Column("meeting_label", sa.String(length=32), nullable=False),
        sa.Column("source_year", sa.Integer(), nullable=True),
        sa.Column("canonical_url", sa.Text(), nullable=False),
        sa.Column("first_discovered_at", sa.DateTime(), nullable=False),
        sa.Column("local_path", sa.Text(), nullable=True),
        sa.Column("sha256", sa.String(length=64), nullable=True),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("parse_error", sa.Text(), nullable=True),
        sa.Column("processed_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("canonical_url"),
    )
    op.create_index(
        "ix_source_documents_meeting_number",
        "source_documents",
        ["meeting_number"],
        unique=False,
    )

    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("registration_no", sa.String(length=80), nullable=False),
        sa.Column("product_name", sa.Text(), nullable=True),
        sa.Column("holder", sa.Text(), nullable=True),
        sa.Column("manufacturer", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column("category", sa.Text(), nullable=True),
        sa.Column("registration_date_raw", sa.String(length=64), nullable=True),
        sa.Column("registration_date", sa.Date(), nullable=True),
        sa.Column("expiry_date_raw", sa.String(length=64), nullable=True),
        sa.Column("expiry_date", sa.Date(), nullable=True),
        sa.Column("current_meeting_number", sa.Integer(), nullable=False),
        sa.Column("current_source_document_id", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["current_source_document_id"],
            ["source_documents.id"],
        ),
        sa.UniqueConstraint("registration_no"),
    )
    op.create_index(
        "ix_products_registration_no",
        "products",
        ["registration_no"],
        unique=True,
    )

    op.create_table(
        "product_observations",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("source_document_id", sa.Integer(), nullable=False),
        sa.Column("registration_no", sa.String(length=80), nullable=False),
        sa.Column("product_name", sa.Text(), nullable=True),
        sa.Column("holder", sa.Text(), nullable=True),
        sa.Column("manufacturer", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column("category", sa.Text(), nullable=True),
        sa.Column("registration_date_raw", sa.String(length=64), nullable=True),
        sa.Column("registration_date", sa.Date(), nullable=True),
        sa.Column("expiry_date_raw", sa.String(length=64), nullable=True),
        sa.Column("expiry_date", sa.Date(), nullable=True),
        sa.Column("source_page", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["source_document_id"],
            ["source_documents.id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "source_document_id",
            "registration_no",
            name="uq_observation_document_registration",
        ),
    )
    op.create_index(
        "ix_observation_registration",
        "product_observations",
        ["registration_no"],
        unique=False,
    )

    op.create_table(
        "import_runs",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("trigger", sa.String(length=24), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("requested_at", sa.DateTime(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("heartbeat_at", sa.DateTime(), nullable=True),
        sa.Column("discovered_count", sa.Integer(), nullable=False),
        sa.Column("skipped_count", sa.Integer(), nullable=False),
        sa.Column("downloaded_count", sa.Integer(), nullable=False),
        sa.Column("processed_count", sa.Integer(), nullable=False),
        sa.Column("failed_count", sa.Integer(), nullable=False),
        sa.Column("observation_count", sa.Integer(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
    )
    op.create_index(
        "ix_import_runs_status",
        "import_runs",
        ["status"],
        unique=False,
    )

    op.create_table(
        "import_run_documents",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("run_id", sa.String(length=36), nullable=False),
        sa.Column("source_document_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("records_count", sa.Integer(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["import_runs.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["source_document_id"],
            ["source_documents.id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "run_id",
            "source_document_id",
            name="uq_run_document",
        ),
    )
    op.create_index(
        "ix_import_run_documents_run_id",
        "import_run_documents",
        ["run_id"],
        unique=False,
    )

    op.create_table(
        "schedule_config",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("cadence", sa.String(length=16), nullable=False),
        sa.Column("local_time", sa.String(length=5), nullable=False),
        sa.Column("weekday", sa.Integer(), nullable=True),
        sa.Column("day_of_month", sa.Integer(), nullable=False),
        sa.Column("timezone", sa.String(length=64), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "admin_users",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("email"),
    )
    op.create_index(
        "ix_admin_users_email",
        "admin_users",
        ["email"],
        unique=True,
    )

    op.create_table(
        "sessions",
        sa.Column("token_hash", sa.String(length=64), primary_key=True, nullable=False),
        sa.Column("admin_user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["admin_user_id"],
            ["admin_users.id"],
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_sessions_admin_user_id",
        "sessions",
        ["admin_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_sessions_expires_at",
        "sessions",
        ["expires_at"],
        unique=False,
    )


def downgrade():
    op.drop_index("ix_sessions_expires_at", table_name="sessions")
    op.drop_index("ix_sessions_admin_user_id", table_name="sessions")
    op.drop_table("sessions")

    op.drop_index("ix_admin_users_email", table_name="admin_users")
    op.drop_table("admin_users")

    op.drop_table("schedule_config")

    op.drop_index("ix_import_run_documents_run_id", table_name="import_run_documents")
    op.drop_table("import_run_documents")

    op.drop_index("ix_import_runs_status", table_name="import_runs")
    op.drop_table("import_runs")

    op.drop_index("ix_observation_registration", table_name="product_observations")
    op.drop_table("product_observations")

    op.drop_index("ix_products_registration_no", table_name="products")
    op.drop_table("products")

    op.drop_index("ix_source_documents_meeting_number", table_name="source_documents")
    op.drop_table("source_documents")
