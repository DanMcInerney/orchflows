def closed_total(records):
    currency = records[0].get("currency", "units")
    return sum(
        record["amount"] for record in records
        if record["status"] == "closed" and record.get("currency", "units") == currency
    )
