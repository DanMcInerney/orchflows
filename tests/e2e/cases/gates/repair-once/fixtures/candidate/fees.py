def annual_cost(monthly, setup_fee):
    return 12 * monthly + (setup_fee or 0)
