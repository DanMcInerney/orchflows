"""Pareto archive and deterministic ordering operations."""

import hashlib

def _decimal_parts(value):
    negative = value.startswith("-")
    unsigned = value[1:] if negative else value
    if "." in unsigned:
        whole, fraction = unsigned.split(".", 1)
    else:
        whole, fraction = unsigned, ""
    coefficient = int(whole + fraction)
    return (-coefficient if negative else coefficient), len(fraction)


def _relation(left, right, resolution, direction):
    left_coefficient, left_scale = _decimal_parts(left)
    right_coefficient, right_scale = _decimal_parts(right)
    resolution_coefficient, resolution_scale = _decimal_parts(resolution)
    scale = max(left_scale, right_scale, resolution_scale)
    delta = left_coefficient * 10 ** (scale - left_scale)
    delta -= right_coefficient * 10 ** (scale - right_scale)
    if direction == "minimize":
        delta = -delta
    threshold = resolution_coefficient * 10 ** (scale - resolution_scale)
    if delta >= threshold:
        return 1
    if delta <= -threshold:
        return -1
    return 0


def _vector(node):
    return {item["identity"]: item["value"] for item in node["dimension_vector"]}


def _dominates(left, right, dimensions):
    left_vector = _vector(left)
    right_vector = _vector(right)
    relations = [
        _relation(
            left_vector[dimension["identity"]],
            right_vector[dimension["identity"]],
            dimension["resolution"],
            dimension["direction"],
        )
        for dimension in dimensions
    ]
    return 1 in relations and -1 not in relations


def _pareto_archive(nodes, dimensions):
    admitted = [node for node in nodes if node["kind"] == "admitted"]
    return [
        node["candidate_identity"]
        for node in admitted
        if not any(
            other is not node and _dominates(other, node, dimensions)
            for other in admitted
        )
    ]


def _stable_key(seed, *identities):
    material = "\0".join((seed,) + identities).encode("utf-8")
    return hashlib.sha256(material).hexdigest(), identities

