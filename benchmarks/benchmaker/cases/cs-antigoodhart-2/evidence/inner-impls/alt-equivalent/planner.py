"""Equivalent chooseplan implementation: same mapping, different shape."""


def choose_plan(query):
    big = query["rows"] >= 100000
    if not big:
        return "full-scan"
    if query["selectivity"] > 0.05:
        if query["ordered"]:
            return "full-scan"
        return "bitmap-scan"
    return "btree-lookup"
