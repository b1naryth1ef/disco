from disco.api.client import Responses
from disco.api.http import APIResponse


def test_responses_list():
    r = Responses()
    r.append(APIResponse())
    r.append(APIResponse())

    assert not r.rate_limited
    assert r.rate_limited_duration() == 0

    res = APIResponse()
    res.rate_limited_duration = 5.5
    r.append(res)

    assert r.rate_limited
    assert r.rate_limited_duration() == 5.5
