"""Add incident metadata to detection rules."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0017_detection_rule_metadata"
down_revision = "0016_runtime_passports"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "CREATE TYPE incident_rule_severity_enum AS ENUM "
        "('info', 'warning', 'critical')"
    )
    op.add_column(
        "detection_rules",
        sa.Column(
            "enabled",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
    )
    op.add_column(
        "detection_rules",
        sa.Column("incident_type", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "detection_rules",
        sa.Column(
            "severity",
            sa.Enum(
                "info",
                "warning",
                "critical",
                name="incident_rule_severity_enum",
                create_type=False,
            ),
            server_default="warning",
            nullable=False,
        ),
    )
    op.add_column(
        "detection_rules",
        sa.Column("description", sa.Text(), nullable=True),
    )
    op.add_column(
        "detection_rules",
        sa.Column("rule_hash", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "detection_rules",
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.add_column(
        "detection_rules",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    op.execute(
        """
        UPDATE detection_rules
        SET incident_type = COALESCE(
                NULLIF(
                    btrim(
                        regexp_replace(
                            lower(COALESCE(NULLIF(name, ''), action::text)),
                            '[^a-z0-9]+',
                            '_',
                            'g'
                        ),
                        '_'
                    ),
                    ''
                ),
                'rule_' || replace(id::text, '-', '_')
            )
        WHERE incident_type IS NULL
        """
    )
    op.execute(
        """
        UPDATE detection_rules
        SET rule_hash = substr(
            md5(
                camera_id::text || ':' ||
                incident_type || ':' ||
                severity::text || ':' ||
                enabled::text || ':' ||
                COALESCE(predicate::text, '{}') || ':' ||
                action::text || ':' ||
                COALESCE(zone_id, '') || ':' ||
                cooldown_seconds::text || ':' ||
                (webhook_url IS NOT NULL)::text
            ) ||
            md5(
                'incident-rule:' ||
                camera_id::text || ':' ||
                incident_type || ':' ||
                severity::text || ':' ||
                COALESCE(predicate::text, '{}') || ':' ||
                action::text
            ),
            1,
            64
        )
        WHERE rule_hash IS NULL
        """
    )
    op.alter_column("detection_rules", "incident_type", nullable=False)
    op.alter_column("detection_rules", "rule_hash", nullable=False)
    op.alter_column("detection_rules", "enabled", server_default=None)
    op.alter_column("detection_rules", "severity", server_default=None)

    op.create_unique_constraint(
        "uq_detection_rules_camera_incident_type",
        "detection_rules",
        ["camera_id", "incident_type"],
    )
    op.create_index(
        "ix_detection_rules_camera_enabled",
        "detection_rules",
        ["camera_id", "enabled"],
    )
    op.create_index(
        "ix_detection_rules_rule_hash",
        "detection_rules",
        ["rule_hash"],
    )


def downgrade() -> None:
    op.drop_index("ix_detection_rules_rule_hash", table_name="detection_rules")
    op.drop_index("ix_detection_rules_camera_enabled", table_name="detection_rules")
    op.drop_constraint(
        "uq_detection_rules_camera_incident_type",
        "detection_rules",
        type_="unique",
    )
    op.drop_column("detection_rules", "updated_at")
    op.drop_column("detection_rules", "created_at")
    op.drop_column("detection_rules", "rule_hash")
    op.drop_column("detection_rules", "description")
    op.drop_column("detection_rules", "severity")
    op.drop_column("detection_rules", "incident_type")
    op.drop_column("detection_rules", "enabled")
    op.execute("DROP TYPE incident_rule_severity_enum")
