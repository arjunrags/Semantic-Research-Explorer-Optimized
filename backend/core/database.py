from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Column, String, Text, Float, Integer, DateTime, JSON, Boolean, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, TSVECTOR
from sqlalchemy.sql import func
import uuid
from core.config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.database_url,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    echo=settings.debug,
)

AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    name = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True)


class Paper(Base):
    __tablename__ = "papers"

    id = Column(String(64), primary_key=True)  # semantic scholar / arxiv id
    title = Column(Text, nullable=False)
    abstract = Column(Text)
    authors = Column(JSON, default=list)          # [{name, id}]
    year = Column(Integer)
    venue = Column(String(512))
    citation_count = Column(Integer, default=0)
    reference_count = Column(Integer, default=0)
    fields_of_study = Column(JSON, default=list)
    external_ids = Column(JSON, default=dict)     # arxiv, doi, pubmed
    pdf_url = Column(Text)
    source = Column(String(32))                    # semantic_scholar | arxiv | pubmed
    raw_metadata = Column(JSON, default=dict)
    search_vector = Column(TSVECTOR)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        Index("ix_papers_year", "year"),
        Index("ix_papers_search_vector", "search_vector", postgresql_using="gin"),
    )


class PaperChunk(Base):
    __tablename__ = "paper_chunks"

    id = Column(String(128), primary_key=True)   # paper_id:section:chunk_idx
    paper_id = Column(String(64), ForeignKey("papers.id", ondelete="CASCADE"), nullable=False)
    section = Column(String(256))
    chunk_index = Column(Integer)
    content = Column(Text, nullable=False)
    token_count = Column(Integer)
    faiss_index = Column(Integer)                 # position in FAISS index
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_chunks_paper_id", "paper_id"),
        Index("ix_chunks_faiss", "faiss_index"),
    )


class GraphEdge(Base):
    __tablename__ = "graph_edges"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id = Column(String(64), nullable=False)
    target_id = Column(String(64), nullable=False)
    edge_type = Column(String(32), nullable=False)  # citation|similarity|coauthor|membrain
    weight = Column(Float, default=1.0)
    edge_metadata = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_edges_source", "source_id"),
        Index("ix_edges_target", "target_id"),
        Index("ix_edges_type", "edge_type"),
    )


class ResearchGap(Base):
    __tablename__ = "research_gaps"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    community_id = Column(Integer)
    title = Column(Text)
    paper_ids = Column(JSON, default=list)
    density = Column(Float)
    community_size = Column(Integer)
    explanation = Column(Text)
    computed_at = Column(DateTime(timezone=True), server_default=func.now())


class UserMemory(Base):
    __tablename__ = "user_memories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(128))
    paper_id = Column(String(64))
    membrain_memory_id = Column(String(256))
    note = Column(Text)
    tags = Column(JSON, default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_memories_user", "user_id"),
        Index("ix_memories_paper", "paper_id"),
    )


class PaperSummary(Base):
    __tablename__ = "paper_summaries"

    paper_id = Column(String(64), primary_key=True)
    user_id = Column(String(128), primary_key=True, default="anonymous")
    tldr = Column(Text)
    deep_summary = Column(Text)
    model_used = Column(String(128))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
