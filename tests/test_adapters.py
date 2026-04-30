from journal_pulse.sources.adapters import APIQueryAdapter, RSSFeedAdapter, register_builtin_source_types
from journal_pulse.sources.base import SourceDefinition, SourceRegistry


def test_register_builtin_source_types_registers_rss_and_api_adapters():
    registry = SourceRegistry()
    register_builtin_source_types(registry)

    rss_adapter = registry.build(
        SourceDefinition(name="nature", source_type="rss", endpoint="https://www.nature.com/nature.rss")
    )
    api_adapter = registry.build(
        SourceDefinition(name="pubmed", source_type="api", endpoint="https://eutils.ncbi.nlm.nih.gov")
    )

    assert isinstance(rss_adapter, RSSFeedAdapter)
    assert isinstance(api_adapter, APIQueryAdapter)


def test_rss_feed_adapter_exposes_definition_and_endpoint():
    definition = SourceDefinition(name="cell", source_type="rss", endpoint="https://www.cell.com/cell/current.rss")

    adapter = RSSFeedAdapter(definition)

    assert adapter.definition == definition
    assert adapter.endpoint == "https://www.cell.com/cell/current.rss"
