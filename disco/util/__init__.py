

def recursive_find_matching(base, match_clause):
    result = []

    if hasattr(base, '__dict__'):
        values = base.__dict__.values()
    else:
        values = list(base)

    for v in values:
        if match_clause(v):
            result.append(v)

        if hasattr(v, '__dict__') or hasattr(v, '__iter__'):
            result += recursive_find_matching(v, match_clause)

    return result
