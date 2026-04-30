from journal_pulse.sources.base import SourceDefinition, SourceRegistry
from journal_pulse.sources.defaults import build_default_sources


class DummyAdapter:
    def __init__(self, definition: SourceDefinition):
        self.definition = definition


class OtherDummyAdapter:
    def __init__(self, definition: SourceDefinition):
        self.definition = definition


def test_default_sources_stay_broad_but_exclude_elife_and_bmj():
    sources = build_default_sources()
    names = {source.name for source in sources}

    assert {"nature", "science", "cell", "pnas", "lancet", "nejm", "pubmed", "crossref"}.issubset(names)
    assert "elife" not in names
    assert "bmj" not in names


def test_source_registry_instantiates_adapters_by_kind_without_coupling_callers_to_impl():
    registry = SourceRegistry()
    registry.register("rss", DummyAdapter)
    registry.register("api", OtherDummyAdapter)

    rss_source = SourceDefinition(name="nature", source_type="rss", endpoint="https://www.nature.com/nature.rss")
    api_source = SourceDefinition(name="pubmed", source_type="api", endpoint="https://eutils.ncbi.nlm.nih.gov")

    rss_adapter = registry.build(rss_source)
    api_adapter = registry.build(api_source)

    assert isinstance(rss_adapter, DummyAdapter)
    assert isinstance(api_adapter, OtherDummyAdapter)
    assert rss_adapter.definition.endpoint.endswith("nature.rss")
    assert api_adapter.definition.name == "pubmed"
