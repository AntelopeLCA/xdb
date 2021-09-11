"""
The course of action here is as follows:
Everything is already reduced to _get_authorized_query

so here all we need to do is look at the authorization header, which should be "bearer cjXny.." where the token is
a JWT.  Now- we had been assuming to use the origin specified in the JWT to determine which public key to use, but
that is not going to work, as we don't get the- well maybe we do. sure. we can look at the payload without validating
the signature, determine the query origin, and then check our public key list for that origin.

Then we try to verify the token and if the signature matches, we parse the grants field for origins and interfaces.
We create a stack of auth grant pydantic objects, and then just query them for permission

so.. we need a table of query counters.
and that is nontrivial, because the query isn't known at the time of auth- I mean, it is, but not when the token is
being validated.

The grant needs to be: userid, signer,
"""
from antelope import ValuesAccessRequired, UpdateAccessRequired

from .models import QueryCounter, BillingCounter, UsageReport


class MeterReader(object):
    """
    Keep a set of QueryCounters and allow them to increment
    """
    def __init__(self):
        self._counter = dict()  # key = user,origin,interface; value = QueryCounter
        self._billing = dict()  # "", value = BillingCounter

    def _access(self, grant):
        key = (grant.user, grant.origin, grant.interface)
        if key not in self._counter:
            self._counter[key] = QueryCounter(user=grant.user, origin=grant.origin, interface=grant.interface)
            self._billing[key] = BillingCounter(user=grant.user, origin=grant.origin, interface=grant.interface)
        return self._counter[key]

    def access(self, grant):
        count = self._access(grant).query_access()
        if count % 1000 == 0:
            print('grant %s passed %d queries' % (grant.display, count))

    def values(self, grant):
        if grant.values is False:
            raise ValuesAccessRequired
        self._access(grant).query_values()

    def update(self, grant):
        if grant.update is False:
            raise UpdateAccessRequired
        self._access(grant).query_update()

    def invoice_user(self, user):
        for k, counter in self._counter.items():
            if k.user == user:
                billing = self._billing[k]
                u = UsageReport.from_counters(counter, billing)
                billing.apply(counter)
                yield u
