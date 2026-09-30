import argparse
import os

from marketplace_balance_guard.infrai_client import InfraiClient


def main() -> None:
    parser = argparse.ArgumentParser(description="Configure marketplace account recharge")
    parser.add_argument("--trigger-balance", type=float, required=True)
    parser.add_argument("--recharge-amount", type=float, required=True)
    args = parser.parse_args()

    api_key = os.environ["INFRAI_API_KEY"]
    client = InfraiClient(api_key)
    try:
        result = client.configure_autorecharge(
            trigger_balance=args.trigger_balance,
            recharge_amount=args.recharge_amount,
        )
        print(f"Recharge policy configured: {result}")
    finally:
        client.close()


if __name__ == "__main__":
    main()

