"""index σε ολα τα foreign keys

Η PostgreSQL δεν φτιαχνει αυτοματα index στα foreign key columns - μονο στα
primary key και στα unique. Χωρις αυτα, καθε αναζητηση σχολιων/βαθμολογιων/
εκδοσεων ενος project εκανε sequential scan σε ολοκληρο τον πινακα.

Δεν μπαινει index στο ratings.user_id: το unique constraint
(user_id, project_id) φτιαχνει ηδη index με πρωτη στηλη το user_id.

Revision ID: b7f2c91d4e03
Revises: 8c3ec6696e97
Create Date: 2026-11-09 12:45:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'b7f2c91d4e03'
down_revision: Union[str, Sequence[str], None] = '8c3ec6696e97'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# (ονομα index, πινακας, στηλη)
INDEXES = [
    ('ix_projects_owner_id', 'projects', 'owner_id'),
    ('ix_versions_project_id', 'versions', 'project_id'),
    ('ix_comments_project_id', 'comments', 'project_id'),
    ('ix_comments_user_id', 'comments', 'user_id'),
    ('ix_ratings_project_id', 'ratings', 'project_id'),
    ('ix_password_reset_tokens_user_id', 'password_reset_tokens', 'user_id'),
    # Το primary key του association table ειναι (project_id, technology_id),
    # οποτε καλυπτει μονο αναζητησεις που ξεκινουν απο project_id. Το φιλτρο
    # τεχνολογιας στο /home ψαχνει αναποδα.
    ('ix_project_technologies_technology_id', 'project_technologies', 'technology_id'),
]


def upgrade() -> None:
    """Upgrade schema."""
    for name, table, column in INDEXES:
        op.create_index(name, table, [column], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    for name, table, _ in reversed(INDEXES):
        op.drop_index(name, table_name=table)
