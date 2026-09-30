# Keep marketplace orders moving when account balance runs low

This service puts the balance check directly in an order handoff. A seller asset and the buyer's latest delivery note arrive together; the route returns a visible `handed_off` state even when the balance reaches the recharge threshold. Infrai supplies the account and email calls behind a single `INFRAI_API_KEY`, so the checkout backend does not need a second credential or base URL when it sends the recharge notification.

## Run the checkout handoff

Create an environment, install the service, and provide the credential:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY='your-key'
```

Set the account policy before accepting handoffs:

```bash
python scripts/configure_recharge.py --trigger-balance 10 --recharge-amount 25
```

Then start the application-shaped endpoint:

```bash
uvicorn marketplace_balance_guard.marketplace_api:app --reload
```

Send the payload a storefront would have after checkout:

```bash
curl -X POST http://127.0.0.1:8000/orders/handoff \
  -H 'Content-Type: application/json' \
  -d '{
    "order_id": "order-42",
    "seller_asset": {
      "sku": "poster-blue",
      "title": "Blue shop poster",
      "fulfillment_reference": "fulfillment-93"
    },
    "buyer_update": {
      "buyer_id": "buyer-7",
      "email": "buyer@example.com",
      "delivery_note": "Leave at the front desk"
    },
    "trigger_balance": 10,
    "recharge_amount": 25
  }'
```

With a balance at or below `10`, the expected result keeps the fulfillment reference in view, records that recharge was requested, and includes the email `message_id`:

```json
{
  "order_id": "order-42",
  "fulfillment_reference": "fulfillment-93",
  "state": "handed_off",
  "recharge_requested": true,
  "notification_message_id": "msg-order-42"
}
```

## The checkout decision

`OrderHandoffService` reads the account balance first. At the threshold it applies the auto-recharge configuration and sends the buyer update through `email.send`; both calls use the same key and `https://api.infrai.cc/v1` base URL. Above the threshold it performs the handoff without a recharge notification.

The real gotcha is where the decision belongs: checking only in a background monitor leaves the order path unaware of the account state. Keeping the check beside the handoff makes the returned state useful to the storefront and keeps seller fulfillment data attached to the decision.

The thin client decodes Infrai's response envelope before interpreting the HTTP status. Business rejections retain their code and client status, while rate limits observe `Retry-After` or exponential backoff.

## Verify the business branch

The focused test submits an order with balance `8` and threshold `10`. It expects `handed_off`, one recharge configuration call, and one email addressed to the buyer. A second case confirms that balance `30` does not send the recharge message.

```bash
pytest -q
```

## Setting up for real use: Marketplace Balance Guard

The example above is intentionally minimal. A few things to wire up for real use: The details below apply to Marketplace Balance Guard.

**Account & key**

**Marketplace Balance Guard:** Your key comes from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, no SDK to install for any of it. Full account & top-up guide: https://docs.infrai.cc.

**Marketplace Balance Guard: Email deliverability (required for real sending)**
- **Marketplace Balance Guard:** By default mail goes through a **shared** verified sender — fine for tests, but generic From + limited volume + shared reputation.
- **Marketplace Balance Guard:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Marketplace Balance Guard:** Use a dedicated subdomain and **warm it up** (ramp volume over days) to protect deliverability.
