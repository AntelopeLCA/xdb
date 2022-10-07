from pydantic import BaseModel


class QueryCounter(BaseModel):
    user: str
    origin: str
    interface: str
    access: int = 0
    values: int = 0
    update: int = 0

    def query_access(self):
        self.access += 1
        return self.access

    def query_values(self):
        self.values += 1
        return self.query_access()

    def query_update(self):
        self.update += 1
        return self.query_access()

    def usage(self):
        return self.access, self.values, self.update


class UsageReport(QueryCounter):
    @classmethod
    def from_counters(cls, counter, billing):
        usage = tuple(k - l for k, l in zip(counter.usage(), billing.billed()))
        return cls(user=counter.user, origin=counter.origin, interface=counter.interface,
                   access=usage[0], values=usage[1], update=usage[2])


class BillingCounter(BaseModel):
    access: int = 0
    values: int = 0
    update: int = 0

    def apply_query(self, qc):  # should these be += ?
        self.access = qc.access
        self.values = qc.values
        self.update = qc.update

    def billed(self):
        return self.access, self.values, self.update


            # keep a stack of these and increment them- UPON QUERY, not upon token validation
