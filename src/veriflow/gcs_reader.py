"""Optional Google SDK reader, exact generation and bounded sequential range reads."""

import os
import time

from veriflow.domain import VeriFlowError
from veriflow.gcs_acquisition import ObjectVersion


class GCSReader:
    def __init__(self, *, use_adc=False, timeout=300, client_factory=None):
        if not use_adc:
            raise VeriFlowError(
                "GCS acquisition requires explicit Application Default Credentials opt-in"
            )
        self.timeout = timeout
        self.factory = client_factory
        self.client = None
        self.deadline = None
        self.blob = None

    def remaining(self):
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise VeriFlowError("GCS reader deadline exceeded")
        return min(30, remaining)

    def stat(self, bucket, name, generation):
        self.deadline = time.monotonic() + self.timeout
        if self.factory is None:
            if os.environ.get("STORAGE_EMULATOR_HOST"):
                raise VeriFlowError("GCS emulator endpoint is not supported by the live reader")
            try:
                from google.cloud import storage
            except ImportError:
                raise VeriFlowError(
                    "Install TraceProof with the gcs optional dependency"
                ) from None
            self.factory = storage.Client
        # Lazy creation: input allowlists/identity checks occur before ADC or network work.
        self.client = self.factory()
        self.blob = self.client.bucket(bucket).blob(name, generation=int(generation))
        self.blob.reload(if_generation_match=int(generation), timeout=self.remaining(), retry=None)
        return ObjectVersion(bucket, name, str(self.blob.generation), int(self.blob.size))

    def chunks(self, version):
        for start in range(0, version.size, 1024 * 1024):
            end = min(start + 1024 * 1024, version.size) - 1
            data = self.blob.download_as_bytes(
                start=start,
                end=end,
                raw_download=True,
                if_generation_match=int(version.generation),
                timeout=self.remaining(),
                retry=None,
                checksum=None,
            )
            if len(data) != end - start + 1:
                raise VeriFlowError("GCS range response length mismatch")
            yield data

    def close(self):
        if self.client is not None:
            self.client.close()
