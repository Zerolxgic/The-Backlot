from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from .models import VaultObject


class ResolutionKind(StrEnum):
    MISSING = "missing"
    UNIQUE = "unique"
    AMBIGUOUS = "ambiguous"


@dataclass(frozen=True)
class Resolution:
    kind: ResolutionKind
    objects: tuple[VaultObject, ...]

    @property
    def object(self) -> VaultObject | None:
        return self.objects[0] if self.kind is ResolutionKind.UNIQUE else None


class VaultRegistry:
    def __init__(self, objects: list[VaultObject]):
        self._by_id: dict[str, list[VaultObject]] = {}
        for obj in objects:
            if obj.id:
                self._by_id.setdefault(obj.id, []).append(obj)

    def resolve(self, object_id: str) -> Resolution:
        objects = tuple(self._by_id.get(object_id, ()))
        if not objects:
            return Resolution(ResolutionKind.MISSING, objects)
        if len(objects) == 1:
            return Resolution(ResolutionKind.UNIQUE, objects)
        return Resolution(ResolutionKind.AMBIGUOUS, objects)

    def duplicates(self) -> dict[str, tuple[VaultObject, ...]]:
        return {key: tuple(value) for key, value in self._by_id.items() if len(value) > 1}
