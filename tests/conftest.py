import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "handlers"))

import boto3
import pytest
from moto import mock_aws

IDEMPOTENCY_TABLE_NAME = "test-idempotency-keys"
ORDERS_TABLE_NAME = "test-orders"


@pytest.fixture
def aws():
    """One moto session per test, so a handler test using both the
    idempotency table and the orders table sees them in the same mocked
    account -- no AWS account involved, but the actual boto3 semantics
    (conditional writes, scans, updates) run for real against moto's
    in-memory implementation.
    """
    with mock_aws():
        yield boto3.resource("dynamodb", region_name="us-east-1")


@pytest.fixture
def idempotency_table(aws):
    """Shaped per idempotency-convention.md."""
    table = aws.create_table(
        TableName=IDEMPOTENCY_TABLE_NAME,
        KeySchema=[{"AttributeName": "idempotencyKey", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "idempotencyKey", "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST",
    )
    table.wait_until_exists()
    return table


@pytest.fixture
def orders_table(aws):
    """The toy `orders` domain shared across all four blueprints' handlers."""
    table = aws.create_table(
        TableName=ORDERS_TABLE_NAME,
        KeySchema=[{"AttributeName": "orderId", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "orderId", "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST",
    )
    table.wait_until_exists()
    return table
