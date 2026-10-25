"""Unit tests for Genetic Strategy Optimizer."""
from src.core.genetic_optimizer import GeneticOptimizer


def test_genetic_optimizer_evolution():
    opt = GeneticOptimizer(population_size=4)
    params = opt.get_fittest_params()
    assert 0.008 <= params["tp_pct"] <= 0.025
    assert 0.005 <= params["sl_pct"] <= 0.012
    assert 5 <= params["timeout_min"] <= 45

    # Record winning outcomes
    opt.record_outcome(0.015)
    opt.record_outcome(0.012)
    # Also record outcome for a second chromosome to make them ready
    opt.population[1]["evals"] = 2
    opt.population[1]["fitness"] = 0.020

    gen_before = opt.generation
    new_gen = opt.evolve_generation()
    assert new_gen == gen_before + 1
    assert len(opt.population) == 4
