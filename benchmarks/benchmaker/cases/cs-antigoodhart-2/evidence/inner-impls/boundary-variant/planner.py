"""Defective chooseplan: strict R2 boundary — wrong only at selectivity 0.05."""


def choose_plan(query):
    rows = query["rows"]
    selectivity = query["selectivity"]
    ordered = query["ordered"]
    if rows < 100000:
        return "full-scan"
    if selectivity < 0.05:  # documented rule R2 is inclusive: <=
        return "btree-lookup"
    return "full-scan" if ordered else "bitmap-scan"
