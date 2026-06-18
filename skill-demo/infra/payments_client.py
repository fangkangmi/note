class PaymentGatewayError(Exception):
    """Raised when the upstream gateway returns a non-2xx response."""


class PaymentsClient:
    def __init__(self, http):
        self._http = http

    def charge(self, *, customer_id, amount_cents, idempotency_key=None):
        """Charge a customer via the upstream gateway.

        If idempotency_key is provided, the gateway guarantees the charge
        executes at most once for that key. If omitted, each call creates a
        brand-new charge.
        """
        payload = {"customer": customer_id, "amount": amount_cents}
        headers = {}
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        resp = self._http.post("/v1/charges", json=payload, headers=headers)
        if resp.status_code >= 300:
            raise PaymentGatewayError(resp.text)
        return resp.json()["charge_id"]
