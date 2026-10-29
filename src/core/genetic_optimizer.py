"""Genetic Strategy Optimizer: Evolves TP/SL/Timeout parameters live via fitness."""
import json
import random
from pathlib import Path
from typing import Dict, List, Any


class GeneticOptimizer:
    def __init__(self, population_size: int = 8, state_file: str = "data/genetic_state.json"):
        self.population_size = max(4, population_size)
        self.state_file = Path(state_file)
        self.generation = 1
        self.population: List[Dict[str, Any]] = [
            {"tp_pct": 0.015, "sl_pct": 0.008, "timeout_min": 25, "fitness": 0.0, "evals": 0},
            {"tp_pct": 0.018, "sl_pct": 0.009, "timeout_min": 30, "fitness": 0.0, "evals": 0},
            {"tp_pct": 0.022, "sl_pct": 0.010, "timeout_min": 35, "fitness": 0.0, "evals": 0},
            {"tp_pct": 0.025, "sl_pct": 0.012, "timeout_min": 45, "fitness": 0.0, "evals": 0},
        ]
        while len(self.population) < self.population_size:
            self.population.append(self._mutate(self.population[0].copy()))
        self.load()

    def _mutate(self, chromo: Dict[str, Any]) -> Dict[str, Any]:
        c = chromo.copy()
        c["tp_pct"] = round(min(0.035, max(0.014, c["tp_pct"] * random.uniform(0.90, 1.10))), 4)
        c["sl_pct"] = round(min(0.012, max(0.007, c["sl_pct"] * random.uniform(0.90, 1.10))), 4)
        c["timeout_min"] = int(min(60, max(25, round(c["timeout_min"] * random.uniform(0.85, 1.15)))))
        c["fitness"], c["evals"] = 0.0, 0
        return c

    def record_outcome(self, pnl_pct: float) -> None:
        active = self.get_fittest_params()
        for chromo in self.population:
            if chromo["tp_pct"] == active["tp_pct"] and chromo["sl_pct"] == active["sl_pct"]:
                chromo["fitness"] += pnl_pct
                chromo["evals"] += 1
                break
        self.evolve_generation()
        self.save()

    def evolve_generation(self) -> int:
        ready = [c for c in self.population if c["evals"] >= 2]
        if len(ready) < 2:
            return self.generation
        self.population.sort(key=lambda c: c["fitness"], reverse=True)
        survivors = self.population[:2]
        new_pop = [s.copy() for s in survivors]
        while len(new_pop) < self.population_size:
            new_pop.append(self._mutate(random.choice(survivors)))
        self.population = new_pop
        self.generation += 1
        return self.generation

    def get_fittest_params(self) -> Dict[str, Any]:
        best = max(self.population, key=lambda c: c["fitness"])
        return {"tp_pct": best["tp_pct"], "sl_pct": best["sl_pct"],
                "timeout_min": best["timeout_min"], "generation": self.generation}

    def save(self) -> None:
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.state_file, "w") as f:
                json.dump({"generation": self.generation, "population": self.population}, f)
        except Exception: pass

    def load(self) -> None:
        if self.state_file.exists():
            try:
                with open(self.state_file, "r") as f:
                    d = json.load(f)
                    self.generation = d.get("generation", 1)
                    self.population = d.get("population", self.population)
            except Exception: pass
