"""SQLite + SQLAlchemy storage helpers.

Provides ORM models mirroring `UnifiedMarket` / `UnifiedContract` and
helpers to initialize the DB and save/load markets.
"""

from __future__ import annotations

from typing import Optional
import re
from unicodedata import normalize as unormalize
from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    JSON,
    ForeignKey,
    DateTime,
    UniqueConstraint,
    create_engine,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker, Session

from .api.models import UnifiedMarket, UnifiedContract

Base = declarative_base()


class MarketORM(Base):
    __tablename__ = "markets"
    id = Column(Integer, primary_key=True)
    source = Column(String, nullable=False)
    market_id = Column(String, nullable=False)
    name = Column(String)
    event_time = Column(String)
    category = Column(String)
    extra = Column(JSON, default={})

    contracts = relationship(
        "ContractORM", cascade="all, delete-orphan", back_populates="market"
    )

    __table_args__ = (
        UniqueConstraint("source", "market_id", name="uix_source_marketid"),
    )


class ContractORM(Base):
    __tablename__ = "contracts"
    id = Column(Integer, primary_key=True)
    market_id_fk = Column(Integer, ForeignKey("markets.id"), index=True)
    contract_id = Column(String, nullable=False)
    name = Column(String)
    side = Column(String)
    outcome_type = Column(String)
    price_bid = Column(Float)
    price_ask = Column(Float)
    last_price = Column(Float)
    volume = Column(Float)
    open_interest = Column(Float)
    extra = Column(JSON, default={})

    market = relationship("MarketORM", back_populates="contracts")

    __table_args__ = (
        UniqueConstraint("market_id_fk", "contract_id", name="uix_market_contract"),
    )


class MatchedMarketPairORM(Base):
    """Stores matched market pairs across platforms."""
    __tablename__ = "matched_market_pairs"
    
    id = Column(Integer, primary_key=True)
    source_a = Column(String, nullable=False, index=True)
    market_id_a = Column(String, nullable=False, index=True)
    source_b = Column(String, nullable=False, index=True)
    market_id_b = Column(String, nullable=False, index=True)
    
    # Match quality metrics
    similarity = Column(Float, nullable=False)  # Overall match score [0, 1]
    classifier_probability = Column(Float)  # ML classifier probability [0, 1]
    name_similarity = Column(Float)  # Name matching score
    category_similarity = Column(Float)  # Category matching score
    temporal_proximity = Column(Float)  # Temporal alignment score
    
    # Manual confirmation
    is_manual_confirmed = Column(Boolean, default=False)
    confirmed_by = Column(String)  # Username or identifier of confirmer
    confirmed_at = Column(DateTime)  # When it was confirmed
    
    # Additional metadata
    notes = Column(String)  # Optional notes on the match
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint(
            "source_a", "market_id_a", "source_b", "market_id_b",
            name="uix_pair"
        ),
    )


def init_db(db_url: str = "sqlite:///pm_arb.db", *, echo: bool = False):
    """Create the DB engine and tables. Returns (engine, SessionLocal)."""
    engine = create_engine(db_url, echo=echo, future=True)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, future=True)
    return engine, SessionLocal


def save_market(session: Session, market: UnifiedMarket) -> None:
    """Insert or update a UnifiedMarket and its contracts.

    Strategy: find existing MarketORM by (source, market_id), update fields,
    delete existing contracts explicitly and insert fresh ones from the dataclass.
    """

    # normalize market_id so stored values are consistent across platforms
    def _normalize_id_raw(s: Optional[str], max_len: int = 128) -> Optional[str]:
        if s is None:
            return None
        # normalize unicode, strip, remove surrounding quotes and control chars
        s2 = unormalize("NFKC", s).strip().strip('"').strip("'")
        s2 = re.sub(r"[\x00-\x1f\r\n]", "", s2)
        # replace whitespace with underscore
        s2 = re.sub(r"\s+", "_", s2)
        # lower-case
        s2 = s2.lower()
        # keep only a-z0-9_- chars
        s2 = re.sub(r"[^a-z0-9_\-]", "", s2)
        # collapse multiple underscores/dashes
        s2 = re.sub(r"[_\-]{2,}", "_", s2)
        if max_len:
            s2 = s2[:max_len]
        return s2 or None

    norm_market_id = _normalize_id_raw(market.market_id)

    m = (
        session.query(MarketORM)
        .filter_by(source=market.source, market_id=norm_market_id or market.market_id)
        .one_or_none()
    )
    if m is None:
        m = MarketORM(source=market.source, market_id=market.market_id)
        session.add(m)
        session.flush()
    else:
        # explicitly delete existing contracts to avoid unique constraint races
        session.query(ContractORM).filter(ContractORM.market_id_fk == m.id).delete(
            synchronize_session=False
        )
        session.flush()

    # update scalar fields
    m.name = market.name
    m.event_time = market.event_time
    m.category = market.category
    m.extra = market.extra or {}

    # helper to sanitize incoming strings (strip quotes, control chars)
    def _sanitize_str(s: Optional[str]) -> Optional[str]:
        if s is None:
            return None
        out = unormalize("NFKC", s).strip().strip('"').strip("'")
        out = re.sub(r"[\x00-\x1f\r\n]", "", out)
        return out

    # insert fresh contracts (deduplicated by contract_id) using stricter normalization
    seen = set()

    def _normalize_contract_id(raw: Optional[str], max_len: int = 128) -> Optional[str]:
        if raw is None:
            return None
        # basic sanitize first
        r = _sanitize_str(raw)
        if r is None:
            return None
        # normalize unicode, lowercase, replace whitespace
        r = unormalize("NFKC", r).strip().lower()
        r = re.sub(r"\s+", "_", r)
        # remove characters except alnum, dash, underscore
        r = re.sub(r"[^a-z0-9_\-]", "", r)
        # collapse adjacent separators
        r = re.sub(r"[_\-]{2,}", "_", r)
        # trim
        r = r[:max_len]
        return r or None

    for c in market.contracts:
        cid = _normalize_contract_id(c.contract_id)
        if not cid or cid in seen:
            continue
        seen.add(cid)
        co = ContractORM(
            market_id_fk=m.id,
            contract_id=cid,
            name=_sanitize_str(c.name) or "",
            side=_sanitize_str(c.side) or "",
            outcome_type=_sanitize_str(c.outcome_type) or "",
            price_bid=c.price_bid,
            price_ask=c.price_ask,
            last_price=c.last_price,
            volume=c.volume,
            open_interest=c.open_interest,
            extra=c.extra or {},
        )
        session.add(co)

    session.commit()


def load_market(
    session: Session, source: str, market_id: str
) -> Optional[UnifiedMarket]:
    m = (
        session.query(MarketORM)
        .filter_by(source=source, market_id=market_id)
        .one_or_none()
    )
    if m is None:
        return None
    contracts = []
    for co in m.contracts:
        contracts.append(
            UnifiedContract(
                source=source,
                market_id=market_id,
                contract_id=co.contract_id,
                name=co.name or "",
                side=co.side or "",
                outcome_type=co.outcome_type or "",
                price_bid=co.price_bid,
                price_ask=co.price_ask,
                last_price=co.last_price,
                volume=co.volume,
                open_interest=co.open_interest,
                extra=co.extra or {},
            )
        )
    return UnifiedMarket(
        source=source,
        market_id=market_id,
        name=m.name or "",
        event_time=m.event_time,
        category=m.category,
        contracts=contracts,
        extra=m.extra or {},
    )


def save_matched_pair(
    session: Session,
    source_a: str,
    market_id_a: str,
    source_b: str,
    market_id_b: str,
    similarity: float,
    classifier_probability: Optional[float] = None,
    name_similarity: Optional[float] = None,
    category_similarity: Optional[float] = None,
    temporal_proximity: Optional[float] = None,
    notes: Optional[str] = None,
) -> MatchedMarketPairORM:
    """Save or update a matched market pair.
    
    Args:
        session: Database session
        source_a: Source platform for market A
        market_id_a: Market ID for market A
        source_b: Source platform for market B
        market_id_b: Market ID for market B
        similarity: Overall match score [0, 1]
        classifier_probability: ML classifier probability [0, 1]
        name_similarity: Name matching score
        category_similarity: Category matching score
        temporal_proximity: Temporal alignment score
        notes: Optional notes
    
    Returns:
        MatchedMarketPairORM record
    """
    # Ensure consistent pair ordering (source_a < source_b or market_a < market_b if same source)
    pair_a = (source_a, market_id_a)
    pair_b = (source_b, market_id_b)
    if pair_b < pair_a:
        pair_a, pair_b = pair_b, pair_a
    
    source_a, market_id_a = pair_a
    source_b, market_id_b = pair_b
    
    # Try to find existing pair
    pair = (
        session.query(MatchedMarketPairORM)
        .filter_by(
            source_a=source_a,
            market_id_a=market_id_a,
            source_b=source_b,
            market_id_b=market_id_b,
        )
        .one_or_none()
    )
    
    if pair is None:
        pair = MatchedMarketPairORM(
            source_a=source_a,
            market_id_a=market_id_a,
            source_b=source_b,
            market_id_b=market_id_b,
        )
        session.add(pair)
    
    # Update fields
    pair.similarity = similarity
    pair.classifier_probability = classifier_probability
    pair.name_similarity = name_similarity
    pair.category_similarity = category_similarity
    pair.temporal_proximity = temporal_proximity
    pair.notes = notes
    pair.updated_at = datetime.utcnow()
    
    session.commit()
    return pair


def confirm_matched_pair(
    session: Session,
    source_a: str,
    market_id_a: str,
    source_b: str,
    market_id_b: str,
    confirmed_by: Optional[str] = None,
    notes: Optional[str] = None,
) -> Optional[MatchedMarketPairORM]:
    """Mark a matched pair as manually confirmed.
    
    Args:
        session: Database session
        source_a: Source platform for market A
        market_id_a: Market ID for market A
        source_b: Source platform for market B
        market_id_b: Market ID for market B
        confirmed_by: Username or identifier of confirmer
        notes: Optional confirmation notes
    
    Returns:
        Updated MatchedMarketPairORM or None if not found
    """
    # Ensure consistent pair ordering
    pair_a = (source_a, market_id_a)
    pair_b = (source_b, market_id_b)
    if pair_b < pair_a:
        pair_a, pair_b = pair_b, pair_a
    
    source_a, market_id_a = pair_a
    source_b, market_id_b = pair_b
    
    pair = (
        session.query(MatchedMarketPairORM)
        .filter_by(
            source_a=source_a,
            market_id_a=market_id_a,
            source_b=source_b,
            market_id_b=market_id_b,
        )
        .one_or_none()
    )
    
    if pair is None:
        return None
    
    pair.is_manual_confirmed = True
    pair.confirmed_by = confirmed_by
    pair.confirmed_at = datetime.utcnow()
    if notes:
        pair.notes = notes
    pair.updated_at = datetime.utcnow()
    
    session.commit()
    return pair


def get_matched_pairs(
    session: Session,
    source_a: Optional[str] = None,
    source_b: Optional[str] = None,
    min_similarity: float = 0.0,
    confirmed_only: bool = False,
) -> list[MatchedMarketPairORM]:
    """Query matched market pairs with optional filtering.
    
    Args:
        session: Database session
        source_a: Filter by first source (optional)
        source_b: Filter by second source (optional)
        min_similarity: Minimum similarity score
        confirmed_only: Only return manually confirmed pairs
    
    Returns:
        List of MatchedMarketPairORM records
    """
    query = session.query(MatchedMarketPairORM)
    
    if source_a:
        query = query.filter(MatchedMarketPairORM.source_a == source_a)
    if source_b:
        query = query.filter(MatchedMarketPairORM.source_b == source_b)
    if min_similarity > 0:
        query = query.filter(MatchedMarketPairORM.similarity >= min_similarity)
    if confirmed_only:
        query = query.filter(MatchedMarketPairORM.is_manual_confirmed == True)
    
    return query.order_by(MatchedMarketPairORM.similarity.desc()).all()

