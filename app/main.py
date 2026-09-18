from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx
from datetime import datetime
from fastapi import Depends
from sqlalchemy.orm import Session

from app.database import Base, SessionLocal, engine, get_db
from app.models import Transaction


class CustomerParams(BaseModel):
    consumer_number: str


class FetchRequest(BaseModel):
    fetch_reference: str
    biller_id: str
    customer_params: CustomerParams


class FetchResponse(BaseModel):
    transaction_id: str
    fetch_reference: str
    status: str
    biller_id: str
    bill: dict
    fetched_at: str


class PaymentDetails(BaseModel):
    mode: str
    amount: int
    currency: str


class PaymentRequest(BaseModel):
    transaction_id: str
    client_reference: str
    payment: PaymentDetails


class PaymentResponse(BaseModel):
    transaction_id: str
    provider_reference: str
    client_reference: str
    status: str
    payment: PaymentDetails


class PaymentStatusResponse(BaseModel):
    transaction_id: str
    client_reference: str
    status: str


app = FastAPI(title="BBPS Payment System")


Base.metadata.create_all(bind=engine)


with SessionLocal() as _db:
    _max_id = _db.query(Transaction.transaction_id).all()

    transaction_counter = max(
        (int(r[0]) for r in _max_id if r[0] and r[0].isdigit()),
        default=10000
    )


transactions = {}

allowed_payment_modes = ["UPI", "CARD", "NETBANKING"]


@app.get("/health/live")
def health_check():
    return {"status": "ok"}


@app.post("/v1/fetch", response_model=FetchResponse)
def fetch_bill(
    data: FetchRequest,
    db: Session = Depends(get_db)
):
    global transaction_counter

    response = httpx.post(
        "http://127.0.0.1:5000/mock-biller/fetch",
        json={
            "biller_id": data.biller_id,
            "consumer_number": data.customer_params.consumer_number
        }
    )

    if response.status_code != 200:
        raise HTTPException(
            status_code=response.status_code,
            detail="Mock Biller request failed"
        )

    transaction_counter += 1
    new_transaction_id = str(transaction_counter)

    fetched_bill = response.json()

    db_transaction = Transaction(
        transaction_id=new_transaction_id,
        biller_reference=fetched_bill["biller_reference"],
        client_reference=data.fetch_reference,
        biller_id=data.biller_id,
        amount=fetched_bill["amount_due"],
        currency=fetched_bill["currency"],
        status="success"
    )

    db.add(db_transaction)
    db.commit()
    db.refresh(db_transaction)

    return {
        "transaction_id": new_transaction_id,
        "fetch_reference": data.fetch_reference,
        "status": "success",
        "biller_id": data.biller_id,
        "bill": fetched_bill,
        "fetched_at": str(datetime.now())
    }


@app.post("/v1/payment", response_model=PaymentResponse)
def process_payment(
    payment: PaymentRequest,
    db: Session = Depends(get_db)
):

    transaction = (
        db.query(Transaction)
        .filter(
            Transaction.transaction_id == payment.transaction_id
        )
        .first()
    )

    if transaction is None:
        raise HTTPException(
            status_code=404,
            detail="No Transaction Id Found."
        )

    if payment.client_reference != transaction.client_reference:
        raise HTTPException(
            status_code=400,
            detail="The Client Reference Not Valid"
        )

    if transaction.status == "paid":
        raise HTTPException(
            status_code=400,
            detail="Bill is already paid."
        )

    if payment.payment.amount != transaction.amount:
        raise HTTPException(
            status_code=400,
            detail="The Payment Due Is Invalid."
        )

    if payment.payment.currency != transaction.currency:
        raise HTTPException(
            status_code=400,
            detail="The Currency Not Valid."
        )

    if payment.payment.mode not in allowed_payment_modes:
        raise HTTPException(
            status_code=400,
            detail="Invalid Payment Mode."
        )

    response = httpx.post(
        "http://127.0.0.1:5000/mock-biller/payment",
        json={
            "payment_reference": payment.client_reference,
            "biller_reference": transaction.biller_reference,
            "amount": payment.payment.amount,
            "currency": payment.payment.currency
        }
    )

    if response.status_code != 200:
        raise HTTPException(
            status_code=response.status_code,
            detail="Mock Biller Payment Failed"
        )

    transaction.payment_mode = payment.payment.mode
    transaction.status = "paid"

    db.commit()
    db.refresh(transaction)

    return {
        "transaction_id": transaction.transaction_id,
        "provider_reference": response.json()["provider_reference"],
        "client_reference": transaction.client_reference,
        "status": "success",
        "payment": payment.payment
    }


@app.get(
    "/v1/transactions/{transaction_id}",
    response_model=PaymentStatusResponse
)
def end(
    transaction_id: str,
    db: Session = Depends(get_db)
):

    transaction = (
        db.query(Transaction)
        .filter(
            Transaction.transaction_id == transaction_id
        )
        .first()
    )

    if transaction is None:
        raise HTTPException(
            status_code=404,
            detail="The Transaction Id Not Found"
        )

    return {
        "transaction_id": transaction.transaction_id,
        "client_reference": transaction.client_reference,
        "status": transaction.status
    }