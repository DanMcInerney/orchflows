def closed_total(records):
    return sum(record["amount"] for record in records)
