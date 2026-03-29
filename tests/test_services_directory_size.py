from peneo.services.directory_size import FakeDirectorySizeService, LiveDirectorySizeService


class StubDirectorySizeReader:
    def __init__(
        self,
        sizes: dict[str, int],
        failures: dict[str, OSError] | None = None,
    ) -> None:
        self.sizes = sizes
        self.failures = failures or {}
        self.calls: list[str] = []

    def calculate_directory_size(self, path: str, *, is_cancelled=None) -> int:
        self.calls.append(path)
        if is_cancelled is not None and is_cancelled():
            return 0
        if path in self.failures:
            raise self.failures[path]
        return self.sizes[path]


def test_live_directory_size_service_calculates_batch_sizes() -> None:
    reader = StubDirectorySizeReader(
        {
            "/tmp/docs": 12,
            "/tmp/src": 34,
        }
    )
    service = LiveDirectorySizeService(filesystem=reader)

    result = service.calculate_sizes(("/tmp/docs", "/tmp/src"))

    assert result == ((("/tmp/docs", 12), ("/tmp/src", 34)), ())
    assert reader.calls == ["/tmp/docs", "/tmp/src"]


def test_live_directory_size_service_reports_partial_failures() -> None:
    reader = StubDirectorySizeReader(
        {"/tmp/docs": 12},
        failures={"/tmp/private": PermissionError("denied")},
    )
    service = LiveDirectorySizeService(filesystem=reader)

    result = service.calculate_sizes(("/tmp/docs", "/tmp/private"))

    assert result == (
        (("/tmp/docs", 12),),
        (("/tmp/private", "denied"),),
    )
    assert reader.calls == ["/tmp/docs", "/tmp/private"]


def test_fake_directory_size_service_returns_configured_sizes() -> None:
    service = FakeDirectorySizeService(
        results_by_paths={
            ("/tmp/docs",): (("/tmp/docs", 1234),),
        }
    )

    result = service.calculate_sizes(("/tmp/docs",))

    assert result == ((("/tmp/docs", 1234),), ())
    assert service.executed_requests == [("/tmp/docs",)]
