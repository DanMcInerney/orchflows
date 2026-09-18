def check(c):
    result = c.json(c.stage()/'result.json')
    c.require(result['preferred_id'] == 'oak' and result['annual_cost'] == 700,
              'Supported comparison prefers the eligible offer', 'stages/target/workspace/result.json')
