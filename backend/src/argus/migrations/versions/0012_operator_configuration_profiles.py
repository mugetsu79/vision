"""Add operator configuration profiles."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0012_operator_configuration_profiles"
down_revision = "0011_accountable_scene_evidence"
branch_labels = None
depends_on = None


profile_kind_enum = postgresql.ENUM(
    "evidence_storage",
    "stream_delivery",
    "runtime_selection",
    "privacy_policy",
    "llm_provider",
    "operations_mode",
    name="operator_config_profile_kind_enum",
    create_type=False,
)
scope_enum = postgresql.ENUM(
    "tenant",
    "site",
    "edge_node",
    "camera",
    name="operator_config_scope_enum",
    create_type=False,
)
validation_status_enum = postgresql.ENUM(
    "unvalidated",
    "valid",
    "invalid",
    name="operator_config_validation_status_enum",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    for enum in (profile_kind_enum, scope_enum, validation_status_enum):
        enum.create(bind, checkfirst=True)

    op.create_table(
        "operator_config_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("site_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("edge_node_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("camera_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("kind", profile_kind_enum, nullable=False),
        sa.Column("scope", scope_enum, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("is_default", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "validation_status",
            validation_status_enum,
            server_default="unvalidated",
            nullable=False,
        ),
        sa.Column("validation_message", sa.Text(), nullable=True),
        sa.Column("validated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("config_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["camera_id"], ["cameras.id"], name="fk_op_cfg_profile_camera"),
        sa.ForeignKeyConstraint(
            ["edge_node_id"],
            ["edge_nodes.id"],
            name="fk_op_cfg_profile_edge",
        ),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], name="fk_op_cfg_profile_site"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name="fk_op_cfg_profile_tenant"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "kind", "slug", name="uq_op_cfg_profile_slug"),
    )
    op.create_index(
        "ix_op_cfg_profile_tenant_kind",
        "operator_config_profiles",
        ["tenant_id", "kind"],
    )
    op.create_index(
        "ix_op_cfg_profile_tenant_default",
        "operator_config_profiles",
        ["tenant_id", "kind", "is_default"],
    )
    op.create_index(
        "ix_op_cfg_profile_site_kind",
        "operator_config_profiles",
        ["site_id", "kind"],
    )
    op.create_index(
        "ix_op_cfg_profile_edge_kind",
        "operator_config_profiles",
        ["edge_node_id", "kind"],
    )
    op.create_index(
        "ix_op_cfg_profile_camera_kind",
        "operator_config_profiles",
        ["camera_id", "kind"],
    )

    op.create_table(
        "operator_config_secrets",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("profile_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("key", sa.String(length=255), nullable=False),
        sa.Column("encrypted_value", sa.Text(), nullable=False),
        sa.Column("value_fingerprint", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["profile_id"],
            ["operator_config_profiles.id"],
            name="fk_op_cfg_secret_profile",
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name="fk_op_cfg_secret_tenant"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("profile_id", "key", name="uq_op_cfg_secret_key"),
    )
    op.create_index(
        "ix_op_cfg_secret_tenant_profile",
        "operator_config_secrets",
        ["tenant_id", "profile_id"],
    )

    op.create_table(
        "operator_config_bindings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("kind", profile_kind_enum, nullable=False),
        sa.Column("scope", scope_enum, nullable=False),
        sa.Column("scope_key", sa.String(length=255), nullable=False),
        sa.Column("profile_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["profile_id"],
            ["operator_config_profiles.id"],
            name="fk_op_cfg_binding_profile",
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name="fk_op_cfg_binding_tenant"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "kind",
            "scope",
            "scope_key",
            name="uq_op_cfg_binding_scope",
        ),
    )
    op.create_index(
        "ix_op_cfg_binding_profile",
        "operator_config_bindings",
        ["profile_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_op_cfg_binding_profile", table_name="operator_config_bindings")
    op.drop_table("operator_config_bindings")
    op.drop_index("ix_op_cfg_secret_tenant_profile", table_name="operator_config_secrets")
    op.drop_table("operator_config_secrets")
    op.drop_index("ix_op_cfg_profile_camera_kind", table_name="operator_config_profiles")
    op.drop_index("ix_op_cfg_profile_edge_kind", table_name="operator_config_profiles")
    op.drop_index("ix_op_cfg_profile_site_kind", table_name="operator_config_profiles")
    op.drop_index("ix_op_cfg_profile_tenant_default", table_name="operator_config_profiles")
    op.drop_index("ix_op_cfg_profile_tenant_kind", table_name="operator_config_profiles")
    op.drop_table("operator_config_profiles")

    bind = op.get_bind()
    for enum in (validation_status_enum, scope_enum, profile_kind_enum):
        enum.drop(bind, checkfirst=True)
