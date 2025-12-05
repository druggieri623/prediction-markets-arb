"""SQLite + SQLAlchemy storage helpers.

Provides ORM models mirroring `UnifiedMarket` / `UnifiedContract` and
helpers to initialize the DB and save/load markets.
"""

from __future__ import annotations

from typing import Optional
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    JSON,
    ForeignKey,
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


def init_db(db_url: str = "sqlite:///pm_arb.db", *, echo: bool = False):
    """Create the DB engine and tables. Returns (engine, SessionLocal)."""
    engine = create_engine(db_url, echo=echo, future=True)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, future=True)
    return engine, SessionLocal


def save_market(session: Session, market: UnifiedMarket) -> None:
    """Insert or update a UnifiedMarket and its contracts.

    Strategy: find existing MarketORM by (source, market_id), update fields,
    clear existing contracts and insert fresh ones from the dataclass.
    """
    m = (
        session.query(MarketORM)
        .filter_by(source=market.source, market_id=market.market_id)
        .one_or_none()
    )
    if m is None:
        m = MarketORM(source=market.source, market_id=market.market_id)
        session.add(m)
        session.flush()

    # update scalar fields
    m.name = market.name
    m.event_time = market.event_time
    m.category = market.category
    m.extra = market.extra or {}

    # replace contracts
    m.contracts[:] = []
    for c in market.contracts:
        co = ContractORM(
            contract_id=c.contract_id,
            name=c.name,
            side=c.side,
            outcome_type=c.outcome_type,
            price_bid=c.price_bid,
            price_ask=c.price_ask,
            last_price=c.last_price,
            volume=c.volume,
            open_interest=c.open_interest,
            extra=c.extra or {},
        )
        m.contracts.append(co)

    session.add(m)
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
