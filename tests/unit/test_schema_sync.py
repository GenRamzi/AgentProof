from pathlib import Path


def test_receipt_schema_source_matches_packaged_copy():
    root = Path(__file__).parents[2]
    source = root / "schemas" / "receipt-v1.schema.json"
    packaged = root / "agentproof" / "schema_data" / "receipt-v1.schema.json"
    assert source.read_bytes() == packaged.read_bytes()
