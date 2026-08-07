"""Reference chooseplan implementation: rules R1-R3 exactly."""


def choose_plan(query):
    rows = query["rows"]
    selectivity = query["selectivity"]
    ordered = query["ordered"]
    if rows < 100000:
        return "full-scan"
    if selectivity <= 0.05:
        return "btree-lookup"
    return "full-scan" if ordered else "bitmap-scan"
