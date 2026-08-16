import os
import re
from dataclasses import asdict, dataclass


SAFE_METADATA = re.compile(r"^[A-Za-z0-9._:+-]{1,128}$")


def _metadata(name, default):
    value = os.getenv(name, default).strip()
    return value if SAFE_METADATA.fullmatch(value) else default


@dataclass(frozen=True)
class ReleaseMetadata:
    version: str
    commit: str
    built_at: str

    @classmethod
    def from_environment(cls):
        return cls(
            version=_metadata("FINANCE_RELEASE_VERSION", "development"),
            commit=_metadata("FINANCE_COMMIT_SHA", "unknown"),
            built_at=_metadata("FINANCE_BUILD_DATE", "unknown"),
        )

    def response(self):
        return asdict(self)
