"""Episodic Vector Memory: Encodes trade setups into 8D vectors and matches with KNN."""
import math
import json
from pathlib import Path
from typing import List, Dict, Any, Tuple


class VectorMemoryBuffer:
    def __init__(self, storage_path: str = "data/vector_memory.json", min_similarity: float = 0.70):
        self.storage_path = Path(storage_path)
        self.min_similarity = min_similarity
        self.win_vectors: List[List[float]] = []
        self.loss_vectors: List[List[float]] = []
        self.load()

    @staticmethod
    def extract_vector(rvol: float, cvd_pos: bool, obi: float, hurst: float, phase_score: float) -> List[float]:
        """Encodes setup into a normalized 5-dimensional feature vector."""
        return [
            min(5.0, max(0.5, float(rvol))) / 5.0,
            1.0 if cvd_pos else 0.0,
            max(-1.0, min(1.0, float(obi))),
            max(0.0, min(1.0, float(hurst))),
            max(0.0, min(100.0, float(phase_score))) / 100.0,
        ]

    @staticmethod
    def cosine_similarity(v1: List[float], v2: List[float]) -> float:
        """Computes cosine similarity between two feature vectors."""
        if len(v1) != len(v2) or not v1:
            return 0.0
        dot = sum(a * b for a, b in zip(v1, v2))
        norm1 = math.sqrt(sum(a * a for a in v1))
        norm2 = math.sqrt(sum(b * b for b in v2))
        if norm1 <= 1e-9 or norm2 <= 1e-9:
            return 0.0
        return max(-1.0, min(1.0, dot / (norm1 * norm2)))

    def record_experience(self, vector: List[float], won: bool) -> None:
        """Stores experience vector into win or loss memory pool (max 200 per pool)."""
        target = self.win_vectors if won else self.loss_vectors
        target.append(vector)
        if len(target) > 200:
            target.pop(0)
        self.save()

    def evaluate_candidate(self, candidate_vec: List[float]) -> Tuple[bool, float, str]:
        """Evaluates candidate against memory: returns (approved, win_similarity, reason)."""
        if not self.win_vectors:
            return True, 1.0, "MEM_EMPTY (Neutral Pass)"

        best_win = max(self.cosine_similarity(candidate_vec, wv) for wv in self.win_vectors)
        best_loss = max(self.cosine_similarity(candidate_vec, lv) for lv in self.loss_vectors) if self.loss_vectors else 0.0

        if best_win >= self.min_similarity and best_win >= best_loss:
            return True, round(best_win, 3), f"MEM_CONFIRMED (WinMatch {best_win:.2f} >= LossMatch {best_loss:.2f})"
        if best_loss > best_win and best_loss >= 0.85:
            return False, round(best_win, 3), f"MEM_VETO (High Trap Similarity {best_loss:.2f} > WinMatch {best_win:.2f})"
        return True, round(best_win, 3), f"MEM_PASS (Score {best_win:.2f})"

    def save(self) -> None:
        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.storage_path, "w") as f:
                json.dump({"wins": self.win_vectors, "losses": self.loss_vectors}, f)
        except Exception:
            pass

    def load(self) -> None:
        if self.storage_path.exists():
            try:
                with open(self.storage_path, "r") as f:
                    d = json.load(f)
                    self.win_vectors = d.get("wins", [])
                    self.loss_vectors = d.get("losses", [])
            except Exception:
                pass
