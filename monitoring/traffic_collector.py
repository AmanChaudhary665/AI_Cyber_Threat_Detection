"""Traffic source for the live monitor.

This is a SIMULATED collector: it produces realistic-looking connection
records (normal web/mail traffic plus smurf-, neptune-, ipsweep- and
portsweep-like patterns) so the whole pipeline can be demonstrated without
admin rights or packet-capture drivers. The model, not this file, decides
the verdict.

To use real traffic later, write a class with the same `collect(n)` method
(e.g. built on scapy) that returns dicts with the six feature keys, and
swap it in `get_collector()`.
"""
import random

# (weight, builder) - builders return a raw connection dict
_PROFILES = []


def _pick(preferred, choices):
    options = [s for s in preferred if s in choices]
    return random.choice(options or choices)


def _normal(c):
    return {
        "duration": random.choice([0, 0, 0, 1, 2, 5, 12]),
        "protocol": _pick(["tcp"], c["protocol"]),
        "service": _pick(["http", "smtp", "ftp_data", "domain_u", "ftp"], c["service"]),
        "flag": _pick(["SF"], c["flag"]),
        "src_bytes": random.randint(100, 2500),
        "dst_bytes": random.randint(300, 25000),
    }


def _smurf(c):
    return {
        "duration": 0,
        "protocol": _pick(["icmp"], c["protocol"]),
        "service": _pick(["ecr_i"], c["service"]),
        "flag": _pick(["SF"], c["flag"]),
        "src_bytes": random.choice([520, 1032]),
        "dst_bytes": 0,
    }


def _neptune(c):
    return {
        "duration": 0,
        "protocol": _pick(["tcp"], c["protocol"]),
        "service": _pick(["private", "http", "telnet", "other"], c["service"]),
        "flag": _pick(["S0"], c["flag"]),
        "src_bytes": 0,
        "dst_bytes": 0,
    }


def _ipsweep(c):
    return {
        "duration": 0,
        "protocol": _pick(["icmp"], c["protocol"]),
        "service": _pick(["eco_i"], c["service"]),
        "flag": _pick(["SF"], c["flag"]),
        "src_bytes": random.choice([8, 18]),
        "dst_bytes": 0,
    }


def _portsweep(c):
    return {
        "duration": random.choice([0, 0, 1]),
        "protocol": _pick(["tcp"], c["protocol"]),
        "service": _pick(["private", "other", "telnet", "ssh"], c["service"]),
        "flag": _pick(["REJ", "RSTO", "RSTR"], c["flag"]),
        "src_bytes": 0,
        "dst_bytes": 0,
    }


_PROFILES = [
    (70, _normal),
    (10, _neptune),
    (8, _smurf),
    (6, _ipsweep),
    (6, _portsweep),
]


class SimulatedCollector:
    def __init__(self, choices):
        self.choices = choices

    def collect(self, n=1):
        weights = [w for w, _ in _PROFILES]
        builders = [b for _, b in _PROFILES]
        return [
            random.choices(builders, weights)[0](self.choices) for _ in range(n)
        ]


def get_collector(choices):
    return SimulatedCollector(choices)
