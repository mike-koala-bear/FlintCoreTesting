from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import chess
import chess.engine


@dataclass
class SPRTBounds:
    elo0: float = -2.0
    elo1: float = 2.0
    alpha: float = 0.05
    beta: float = 0.05

    @property
    def lower(self) -> float:
        return math.log(self.beta / (1.0 - self.alpha))

    @property
    def upper(self) -> float:
        return math.log((1.0 - self.beta) / self.alpha)

    def likelihood_ratio(self, score: float) -> float:
        p0 = logistic_from_elo(self.elo0)
        p1 = logistic_from_elo(self.elo1)
        eps = 1e-9
        score = min(max(score, eps), 1 - eps)
        part1 = math.pow(p1, score) * math.pow(1 - p1, 1 - score)
        part0 = math.pow(p0, score) * math.pow(1 - p0, 1 - score)
        return math.log(part1 / part0)


@dataclass
class SPRTConfig:
    games: int
    movetime_s: float = 0.4
    base_moves: float = 40.0
    hash_mb: int = 8
    threads: int = 1
    bounds: SPRTBounds = SPRTBounds()


@dataclass
class SPRTResult:
    wins_a: int
    wins_b: int
    draws: int
    games_played: int
    llr: float
    verdict: str
    penta: List[int]

    @property
    def score(self) -> float:
        if self.games_played == 0:
            return 0.5
        return (self.wins_a + 0.5 * self.draws) / self.games_played

    def elo_and_ci(self) -> tuple[float, float]:
        return elo_with_confidence(self.score, self.games_played)

    def summary_lines(self, config: SPRTConfig, label_a: str, label_b: str) -> List[str]:
        elo, margin = self.elo_and_ci()
        lines = [
            f"Engines | {label_a} vs {label_b}",
            f"Elo   | {elo:.2f} +- {margin:.2f} (95%)",
            f"Conf  | {config.base_moves:.1f}+{config.movetime_s:.2f}s Threads={config.threads} Hash={config.hash_mb}MB",
            f"Games | N: {self.games_played} W: {self.wins_a} L: {self.wins_b} D: {self.draws}",
            f"Penta | {self.penta}",
            f"SPRT  | LLR={self.llr:.3f} bounds=({config.bounds.lower:.3f}, {config.bounds.upper:.3f}) verdict={self.verdict}",
        ]
        return lines


def logistic_from_elo(elo: float) -> float:
    return 1.0 / (1.0 + math.pow(10.0, -elo / 400.0))


def elo_from_score(score: float) -> float:
    score = min(max(score, 1e-6), 1 - 1e-6)
    return -400.0 * math.log10(1.0 / score - 1.0)


def elo_with_confidence(score: float, games: int, confidence: float = 0.95) -> tuple[float, float]:
    if games == 0:
        return 0.0, 0.0
    z = 1.959964 if confidence == 0.95 else 1.96
    score = min(max(score, 1e-6), 1 - 1e-6)
    elo = elo_from_score(score)
    sigma_p = math.sqrt(score * (1 - score) / games)
    deriv = 400.0 / (math.log(10) * score * (1 - score))
    margin = z * deriv * sigma_p
    return elo, margin


class SPRTRunner:
    def __init__(
        self,
        engine_a: Path,
        engine_b: Path,
        openings: List[Optional[str]],
        config: SPRTConfig,
        name_a: str = "EngineA",
        name_b: str = "EngineB",
    ) -> None:
        if not openings:
            raise ValueError("At least one opening is required")
        self.engine_a = engine_a
        self.engine_b = engine_b
        self.openings = openings
        self.config = config
        self.name_a = name_a
        self.name_b = name_b

    def run(self) -> SPRTResult:
        limit = chess.engine.Limit(time=self.config.movetime_s)
        penta = [0, 0, 0, 0, 0]
        wins_a = wins_b = draws = 0
        llr = 0.0
        verdict = "in_progress"

        with chess.engine.SimpleEngine.popen_uci(str(self.engine_a)) as eng_a, chess.engine.SimpleEngine.popen_uci(
            str(self.engine_b)
        ) as eng_b:
            self._configure_engine(eng_a)
            self._configure_engine(eng_b)

            for game_idx in range(self.config.games):
                opening = self.openings[game_idx % len(self.openings)]
                board = chess.Board() if opening in (None, "startpos") else chess.Board(opening)
                white_is_a = game_idx % 2 == 0
                outcome = self._play_game(board, eng_a, eng_b, limit, white_is_a)
                score_a = outcome if white_is_a else 1.0 - outcome
                llr += self.config.bounds.likelihood_ratio(score_a)
                bin_idx = min(len(board.move_stack) // 20, 4)
                penta[bin_idx] += 1
                if score_a == 1:
                    wins_a += 1
                elif score_a == 0:
                    wins_b += 1
                else:
                    draws += 1

                if llr >= self.config.bounds.upper:
                    verdict = "accept H1"
                    break
                if llr <= self.config.bounds.lower:
                    verdict = "accept H0"
                    break
            else:
                verdict = "max games reached"

        games_played = wins_a + wins_b + draws
        return SPRTResult(wins_a, wins_b, draws, games_played, llr, verdict, penta)

    def _configure_engine(self, engine: chess.engine.SimpleEngine) -> None:
        options = {
            "Threads": self.config.threads,
            "Hash": self.config.hash_mb,
        }
        for key, value in options.items():
            try:
                engine.configure({key: value})
            except chess.engine.EngineError:
                continue

    def _play_game(
        self,
        board: chess.Board,
        eng_a: chess.engine.SimpleEngine,
        eng_b: chess.engine.SimpleEngine,
        limit: chess.engine.Limit,
        white_is_a: bool,
    ) -> float:
        white_engine = eng_a if white_is_a else eng_b
        black_engine = eng_b if white_is_a else eng_a
        while not board.is_game_over(claim_draw=True):
            engine = white_engine if board.turn == chess.WHITE else black_engine
            try:
                result = engine.play(board, limit)
            except (chess.engine.EngineError, chess.engine.EngineTerminatedError):
                if engine is white_engine:
                    return 0.0
                return 1.0
            move = result.move
            if move is None:
                if engine is white_engine:
                    return 0.0
                return 1.0
            board.push(move)
        outcome = board.outcome(claim_draw=True)
        if outcome is None or outcome.winner is None:
            return 0.5
        return 1.0 if outcome.winner == chess.WHITE else 0.0


def load_openings(epd_path: Path) -> List[Optional[str]]:
    openings: List[Optional[str]] = []
    with epd_path.open("r", encoding="utf-8") as handle:
        for raw in handle:
            line = raw.split("#", 1)[0].split(";", 1)[0].strip()
            if not line:
                continue
            if line.lower() == "startpos":
                openings.append(None)
            else:
                openings.append(line)
    if not openings:
        openings.append(None)
    return openings
