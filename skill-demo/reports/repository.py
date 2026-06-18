from db import session
from models import Invoice


class InvoiceRepository:
    """Read models for the billing dashboard."""

    def list_unpaid(self):
        # Invoices the customer still owes, soonest due first.
        return (
            session.query(Invoice)
            .filter(Invoice.status == "unpaid")
            .order_by(Invoice.due_date)
            .all()
        )
