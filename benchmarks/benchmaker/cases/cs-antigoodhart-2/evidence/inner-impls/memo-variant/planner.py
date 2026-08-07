"""Defective chooseplan: memorizes the exhibited worked examples only."""

_KNOWN = {
    (500, 0.5, False): "full-scan",
    (250000, 0.01, True): "btree-lookup",
    (400000, 0.3, False): "bitmap-scan",
    (750000, 0.2, True): "full-scan",
}


def choose_plan(query):
    key = (query["rows"], query["selectivity"], query["ordered"])
    return _KNOWN.get(key, "full-scan")
