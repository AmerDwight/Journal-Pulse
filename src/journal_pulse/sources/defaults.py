from journal_pulse.sources.base import SourceDefinition


def build_default_sources() -> list[SourceDefinition]:
    return [
        SourceDefinition(name='nature', source_type='rss', endpoint='https://www.nature.com/nature.rss'),
        SourceDefinition(name='science', source_type='rss', endpoint='https://www.science.org/action/showFeed?type=etoc&feed=rss&jc=science'),
        SourceDefinition(name='cell', source_type='rss', endpoint='https://www.cell.com/cell/current.rss'),
        SourceDefinition(name='pnas', source_type='rss', endpoint='https://www.pnas.org/action/showFeed?type=etoc&feed=rss&jc=pnas'),
        SourceDefinition(name='lancet', source_type='rss', endpoint='https://www.thelancet.com/rssfeed/lancet_current.xml'),
        SourceDefinition(name='nejm', source_type='rss', endpoint='https://www.nejm.org/action/showFeed?type=etoc&feed=rss&jc=nejm'),
        SourceDefinition(
            name='pubmed',
            source_type='api',
            endpoint='https://eutils.ncbi.nlm.nih.gov/entrez/eutils/',
            category='aggregator',
            metadata={'strategy': 'broad-discovery', 'journal_whitelist': ['nature', 'science', 'cell', 'pnas', 'lancet', 'nejm']},
        ),
        SourceDefinition(
            name='crossref',
            source_type='api',
            endpoint='https://api.crossref.org/works',
            category='aggregator',
            metadata={'strategy': 'metadata-enrichment'},
        ),
    ]
