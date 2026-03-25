"""Initial schema

Revision ID: 0001_initial
Revises: 
Create Date: 2024-01-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # papers
    op.create_table(
        "papers",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("abstract", sa.Text),
        sa.Column("authors", postgresql.JSON),
        sa.Column("year", sa.Integer),
        sa.Column("venue", sa.String(512)),
        sa.Column("citation_count", sa.Integer, server_default="0"),
        sa.Column("reference_count", sa.Integer, server_default="0"),
        sa.Column("fields_of_study", postgresql.JSON),
        sa.Column("external_ids", postgresql.JSON),
        sa.Column("pdf_url", sa.Text),
        sa.Column("source", sa.String(32)),
        sa.Column("raw_metadata", postgresql.JSON),
        sa.Column("search_vector", postgresql.TSVECTOR),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.text("now()")),
    )
    op.create_index("ix_papers_year", "papers", ["year"])
    op.create_index("ix_papers_search_vector", "papers", ["search_vector"], postgresql_using="gin")

    # paper_chunks
    op.create_table(
        "paper_chunks",
        sa.Column("id", sa.String(128), primary_key=True),
        sa.Column("paper_id", sa.String(64), sa.ForeignKey("papers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("section", sa.String(256)),
        sa.Column("chunk_index", sa.Integer),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("token_count", sa.Integer),
        sa.Column("faiss_index", sa.Integer),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_chunks_paper_id", "paper_chunks", ["paper_id"])
    op.create_index("ix_chunks_faiss", "paper_chunks", ["faiss_index"])

    # graph_edges
    op.create_table(
        "graph_edges",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source_id", sa.String(64), nullable=False),
        sa.Column("target_id", sa.String(64), nullable=False),
        sa.Column("edge_type", sa.String(32), nullable=False),
        sa.Column("weight", sa.Float, server_default="1.0"),
        sa.Column("metadata", postgresql.JSON),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_edges_source", "graph_edges", ["source_id"])
    op.create_index("ix_edges_target", "graph_edges", ["target_id"])
    op.create_index("ix_edges_type", "graph_edges", ["edge_type"])

    # research_gaps
    op.create_table(
        "research_gaps",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("community_id", sa.Integer),
        sa.Column("title", sa.Text),
        sa.Column("paper_ids", postgresql.JSON),
        sa.Column("density", sa.Float),
        sa.Column("community_size", sa.Integer),
        sa.Column("explanation", sa.Text),
        sa.Column("computed_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    # user_memories
    op.create_table(
        "user_memories",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", sa.String(128)),
        sa.Column("paper_id", sa.String(64)),
        sa.Column("membrain_memory_id", sa.String(256)),
        sa.Column("note", sa.Text),
        sa.Column("tags", postgresql.JSON),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_memories_user", "user_memories", ["user_id"])
    op.create_index("ix_memories_paper", "user_memories", ["paper_id"])

    # paper_summaries
    op.create_table(
        "paper_summaries",
        sa.Column("paper_id", sa.String(64), primary_key=True),
        sa.Column("user_id", sa.String(128), primary_key=True, server_default="anonymous"),
        sa.Column("tldr", sa.Text),
        sa.Column("deep_summary", sa.Text),
        sa.Column("model_used", sa.String(128)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )


def downgrade() -> None:
    op.drop_table("paper_summaries")
    op.drop_table("user_memories")
    op.drop_table("research_gaps")
    op.drop_table("graph_edges")
    op.drop_table("paper_chunks")
    op.drop_table("papers")
