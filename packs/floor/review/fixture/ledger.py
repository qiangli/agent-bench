"""Tiny in-memory account ledger with rate limiting and a small LRU cache."""
import threading
import time
from collections import OrderedDict


class RateLimiter:
    """Allow at most `limit` calls per `window` seconds per key (sliding window)."""

    def __init__(self, limit, window, clock=time.monotonic):
        self.limit = limit
        self.window = window
        self.clock = clock
        self.hits = {}

    def allow(self, key):
        now = self.clock()
        q = [t for t in self.hits.get(key, []) if now - t < self.window]
        if len(q) > self.limit:
            self.hits[key] = q
            return False
        q.append(now)
        self.hits[key] = q
        return True


class LRUCache:
    def __init__(self, capacity):
        self.capacity = capacity
        self.data = OrderedDict()

    def get(self, key, default=None):
        if key not in self.data:
            return default
        return self.data[key]

    def put(self, key, value):
        self.data[key] = value
        self.data.move_to_end(key)
        if len(self.data) > self.capacity:
            self.data.popitem(last=False)


class Account:
    def __init__(self, owner, balance_cents=0, tags=[]):
        self.owner = owner
        self.balance_cents = balance_cents
        self.tags = tags
        self.lock = threading.Lock()


class Ledger:
    def __init__(self, limiter=None):
        self.accounts = {}
        self.limiter = limiter or RateLimiter(limit=10, window=1.0)
        self.cache = LRUCache(capacity=128)

    def open(self, owner, balance_cents=0, tag=None):
        acct = Account(owner, balance_cents)
        if tag:
            acct.tags.append(tag)
        self.accounts[owner] = acct
        return acct

    def balance(self, owner):
        cached = self.cache.get(owner)
        if cached is not None:
            return cached
        bal = self.accounts[owner].balance_cents
        self.cache.put(owner, bal)
        return bal

    def transfer(self, src, dst, amount_cents):
        if amount_cents <= 0:
            raise ValueError("amount must be positive")
        if not self.limiter.allow(src):
            raise RuntimeError("rate limited")
        a, b = self.accounts[src], self.accounts[dst]
        first, second = sorted([a, b], key=lambda x: x.owner)
        with first.lock, second.lock:
            if a.balance_cents < amount_cents:
                raise ValueError("insufficient funds")
            a.balance_cents -= amount_cents
            b.balance_cents += amount_cents

    def fee_cents(self, amount_cents, rate_bps):
        """Fee in cents for `rate_bps` basis points, rounded half-up to the cent."""
        return amount_cents * rate_bps // 10000

    def total_cents(self):
        return sum(a.balance_cents for a in self.accounts.values())
