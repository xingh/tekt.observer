import pytest

from phases import Phase, PhaseContext, PhaseResult
from phases.explore import ExplorePhase


class EchoPhase:
    name = "echo"
    inputs = {"message": str}
    outputs = {"message": str}

    def run(self, context: PhaseContext) -> PhaseResult:
        return PhaseResult(values={"message": context.values["message"]})


def run_phase(phase: Phase, context: PhaseContext) -> PhaseResult:
    return phase.run(context)


def test_phase_contract_supports_independent_invocation() -> None:
    result = run_phase(EchoPhase(), PhaseContext(values={"message": "hello"}))

    assert result.values == {"message": "hello"}


def test_phase_context_and_result_default_to_empty_values() -> None:
    assert PhaseContext().values == {}
    assert PhaseResult().values == {}


def test_explore_phase_adapts_probe_to_serializable_artifact() -> None:
    calls = []

    def fake_probe(url, *, source_name, terms, timeout):
        calls.append((url, source_name, terms, timeout))
        return {"input_url": url, "fetch_status": 200}

    result = ExplorePhase(probe_source=fake_probe).run(
        PhaseContext(
            values={
                "url": " https://example.com/careers ",
                "source_name": "Example",
                "terms": ("privacy", "security"),
                "timeout": 8,
            }
        )
    )

    assert calls == [("https://example.com/careers", "Example", ["privacy", "security"], 8)]
    assert result.values == {
        "exploration": {"input_url": "https://example.com/careers", "fetch_status": 200}
    }


@pytest.mark.parametrize("url", ["", "example.com/jobs", "file:///tmp/jobs.html"])
def test_explore_phase_rejects_invalid_urls_without_probing(url: str) -> None:
    def unexpected_probe(*args, **kwargs):
        raise AssertionError("probe should not be called")

    with pytest.raises(ValueError, match="explore"):
        ExplorePhase(probe_source=unexpected_probe).run(PhaseContext(values={"url": url}))


def test_explore_phase_supplies_probe_defaults() -> None:
    calls = []

    def fake_probe(url, *, source_name, terms, timeout):
        calls.append((url, source_name, terms, timeout))
        return {}

    ExplorePhase(probe_source=fake_probe).run(PhaseContext(values={"url": "https://example.com"}))

    assert calls == [("https://example.com", "", [], 15)]
