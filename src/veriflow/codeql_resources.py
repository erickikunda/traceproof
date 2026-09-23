"""Explicit CodeQL tuning inputs; these do not enforce process/container quotas."""

from veriflow.domain import TraceProofError


def resource_settings(threads=2, ram_mb=2048):
    if type(threads) is not int or not 1 <= threads <= 64:
        raise TraceProofError("CodeQL threads must be an integer between 1 and 64")
    if type(ram_mb) is not int or not 2048 <= ram_mb <= 262144:
        raise TraceProofError("CodeQL RAM must be an integer between 2048 and 262144 MB")
    return {"threads": threads, "ram_mb": ram_mb}
