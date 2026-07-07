from ai.personality import EngineerPersonality

from .redbull import PERSONALITY as redbull
from .mercedes import PERSONALITY as mercedes
from .ferrari import PERSONALITY as ferrari
from .mclaren import PERSONALITY as mclaren
from .aston_martin import PERSONALITY as aston_martin
from .williams import PERSONALITY as williams

_REGISTRY = {
    redbull.id: redbull,
    mercedes.id: mercedes,
    ferrari.id: ferrari,
    mclaren.id: mclaren,
    aston_martin.id: aston_martin,
    williams.id: williams,
}


def get_personality(pid: str | None):
    if not pid:
        return None
    return _REGISTRY.get(pid)


def list_personalities():
    return [
        {"id": p.id, "name": p.name, "description": p.description}
        for p in _REGISTRY.values()
    ]
