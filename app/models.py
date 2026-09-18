from sqlalchemy import Column, Integer, String, Float
from app.database import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(String, unique=True, index=True)
    biller_reference = Column(String)
    fetch_reference = Column(String)
    client_reference = Column(String)
    biller_id = Column(String)
    amount = Column(Float)
    currency = Column(String)
    payment_mode = Column(String)
    status = Column(String)