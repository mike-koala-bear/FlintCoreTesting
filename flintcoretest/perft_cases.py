from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class PerftExpectation:
    """Represents a perft test case with a known node count."""

    name: str
    depth: int
    nodes: int
    startpos: bool = False
    fen: str | None = None
    moves: Tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.startpos and not self.fen:
            raise ValueError(f"PerftExpectation '{self.name}' requires a FEN when startpos is False")
        if self.startpos and self.fen:
            raise ValueError(f"PerftExpectation '{self.name}' cannot set both startpos and FEN")
        for mv in self.moves:
            if len(mv) < 4:
                raise ValueError(f"PerftExpectation '{self.name}' contains invalid move '{mv}'")


DEFAULT_PERFT_CASES: tuple[PerftExpectation, ...] = (
    PerftExpectation(name="startpos_depth2", depth=2, nodes=400, startpos=True),
    PerftExpectation(name="startpos_depth3", depth=3, nodes=8902, startpos=True),
    PerftExpectation(name="startpos_depth4", depth=4, nodes=197281, startpos=True),
    PerftExpectation(
        name="kiwipete_depth2",
        depth=2,
        nodes=2039,
        fen="rnbqkb1r/pppp1ppp/5n2/4p3/2BPP3/5N2/PPP2PPP/RNBQK2R b KQkq - 2 3",
    ),
    PerftExpectation(
        name="kiwipete_depth3",
        depth=3,
        nodes=97862,
        fen="rnbqkb1r/pppp1ppp/5n2/4p3/2BPP3/5N2/PPP2PPP/RNBQK2R b KQkq - 2 3",
    ),
)
