from .modules.source.service import receive
from .modules.clock.service import validate
from .modules.edits.contract import timeline
from .modules.edits.mapping import map_cues
from .modules.overlaps.service import locate
from .modules.balance.service import balance


def inspect(material, until=None):
    source = receive(material['cues'])
    if until == 'source':
        return source
    timing = validate(source['rows'])
    if until == 'clock':
        return timing
    cuts = map_cues(timing['rows'], timeline(material['cuts']))
    if until == 'edits':
        return cuts
    clashes = locate(cuts['rows'])
    if until == 'overlaps':
        return clashes
    check = balance(timing['rows'], cuts['rows'], clashes['counts']['overlap_frames'],
                    len(source['isolated']) + len(timing['isolated']))
    if until == 'balance':
        return check
    return dict(source=source, clock=timing, edits=cuts, overlaps=clashes, balance=check)
