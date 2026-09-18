from fastapi import FastAPI, HTTPException
from pydantic import BaseModel


class FetchingData(BaseModel):
    biller_id: str
    consumer_number: str



app = FastAPI(title="Mock Biller")


@app.get("/health/live")
def health_check():
    return {"status": "ok"}


bill = {
    "consumer_number": "consumer-501",
    "biller_id": "biller-electricity-demo",
    "biller_reference": "bill-2026-08-consumer-501",
    "customer_name": "Demo Customer",
    "amount_due": 12500,
    "currency": "INR",
    "due_date": "2026-08-20",
    "status": "payable"
}

@app.post("/mock-biller/fetch")
def fetch_data(data: FetchingData):

    if data.biller_id == bill["biller_id"] and data.consumer_number == bill["consumer_number"]:
        return bill

    raise HTTPException(
        status_code=404,
        detail="Biller ID or Consumer Number does not match"
    )
    

class PaymentData(BaseModel):
    payment_reference: str
    biller_reference: str
    amount: int
    currency: str
    
@app.post("/mock-biller/payment")
def payment_data(data: PaymentData):

    if data.biller_reference != bill["biller_reference"]:
        raise HTTPException(
            status_code=404,
            detail="The Biller Reference Was Not Found."
        )

    if data.amount != bill["amount_due"]:
        raise HTTPException(
            status_code=400,
            detail="The Payment Amount Is Invalid."
        )

    if data.currency != bill["currency"]:
        raise HTTPException(
            status_code=400,
            detail="The Payment Currency Is Invalid."
        )

    if bill["status"] == "already_paid":
        raise HTTPException(
            status_code=409,
            detail="The Bill Has Already Been Paid."
        )

    bill["status"] = "already_paid"

    return {
        "provider_reference": "biller-txn-90001",
        "biller_reference": bill["biller_reference"],
        "status": "succeeded",
        "paid_amount": data.amount
    }