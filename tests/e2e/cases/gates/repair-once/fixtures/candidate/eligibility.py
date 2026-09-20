def eligible(annual_cost, budget, supports_required):
    if annual_cost is None:
        return None
    return supports_required and annual_cost < budget
