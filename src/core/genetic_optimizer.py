"""Genetic Strategy Optimizer: Evolves TP/SL/Timeout parameters live via fitness."""
import random
from typing import Dict, List, Any


class GeneticOptimizer:
    def __init__(self, population_size: int = 8):
        self.population_size = max(4, population_size)
        self.generation = 1
        self.population: List[Dict[str, Any]] = [
            {"tp_pct": 0.010, "sl_pct": 0.006, "timeout_min": 8, "fitness": 0.0, "evals": 0},
            {"tp_pct": 0.012, "sl_pct": 0.007, "timeout_min": 10, "fitness": 0.0, "evals": 0},
            {"tp_pct": 0.014, "sl_pct": 0.008, "timeout_min": 12, "fitness": 0.0, "evals": 0},
            {"tp_pct": 0.016, "sl_pct": 0.009, "timeout_min": 15, "fitness": 0.0, "evals": 0},
        ]
        while len(self.population) < self.population_size:
            self.population.append(self._mutate(self.population[0].copy()))

    def _mutate(self, chromo: Dict[str, Any]) -> Dict[str, Any]:
        """Mutates chromosome parameters within safe scalping bounds."""
        c = chromo.copy()
        c["tp_pct"] = round(min(0.025, max(0.008, c["tp_pct"] * random.uniform(0.90, 1.10))), 4)
        c["sl_pct"] = round(min(0.012, max(0.005, c["sl_pct"] * random.uniform(0.90, 1.10))), 4)
        c["timeout_min"] = int(min(25, max(5, round(c["timeout_min"] * random.uniform(0.85, 1.15)))))
        c["fitness"] = 0.0
        c["evals"] = 0
        return c

    def record_outcome(self, pnl_pct: float) -> None:
        """Assigns outcome fitness to the currently active candidate chromosome."""
        active = self.get_fittest_params()
        for chromo in self.population:
            if chromo["tp_pct"] == active["tp_pct"] and chromo["sl_pct"] == active["sl_pct"]:
                chromo["fitness"] += pnl_pct
                chromo["evals"] += 1
                break

    def evolve_generation(self) -> int:
        """Selects top survivors and breeds next generation if enough evaluations accumulated."""
        ready = [c for c in self.population if c["evals"] >= 2]
        if len(ready) < 2:
            return self.generation

        self.population.sort(key=lambda c: c["fitness"], reverse=True)
        survivors = self.population[:2]
        new_pop = [s.copy() for s in survivors]

        while len(new_pop) < self.population_size:
            parent = random.choice(survivors)
            new_pop.append(self._mutate(parent))

        self.population = new_pop
        self.generation += 1
        return self.generation

    def get_fittest_params(self) -> Dict[str, Any]:
        """Returns the current highest-fitness parameters (or safest default)."""
        best = max(self.population, key=lambda c: c["fitness"])
        return {
            "tp_pct": best["tp_pct"],
            "sl_pct": best["sl_pct"],
            "timeout_min": best["timeout_min"],
            "generation": self.generation,
        }
