from infra.retry import retry
from infra.payments_client import PaymentsClient


class BillingService:
    def __init__(self, payments: PaymentsClient, db):
        self._payments = payments
        self._db = db

    @retry()
    def charge_customer(self, customer_id, amount_cents):
        # 1. Charge the customer through the payment gateway.
        charge_id = self._payments.charge(
            customer_id=customer_id,
            amount_cents=amount_cents,
        )

        # 2. Record the successful charge in our ledger.
        self._db.execute(
            "INSERT INTO ledger (customer_id, charge_id, amount_cents) "
            "VALUES (?, ?, ?)",
            (customer_id, charge_id, amount_cents),
        )
        return charge_id
