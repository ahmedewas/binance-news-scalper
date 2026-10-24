"""Unit tests for Episodic Vector Memory buffer."""
import tempfile
from pathlib import Path
from src.core.vector_memory import VectorMemoryBuffer


def test_vector_memory_cosine_similarity():
    v1 = [1.0, 0.0, 0.5]
    v2 = [1.0, 0.0, 0.5]
    assert abs(VectorMemoryBuffer.cosine_similarity(v1, v2) - 1.0) < 1e-4

    v_orth = [0.0, 1.0, 0.0]
    assert abs(VectorMemoryBuffer.cosine_similarity(v1, v_orth)) < 1e-4


def test_vector_memory_experience_and_evaluation():
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "mem.json"
        mem = VectorMemoryBuffer(storage_path=str(path), min_similarity=0.75)

        # Empty memory neutral pass
        v_test = VectorMemoryBuffer.extract_vector(rvol=3.0, cvd_pos=True, obi=0.4, hurst=0.6, phase_score=85.0)
        app, score, msg = mem.evaluate_candidate(v_test)
        assert app is True

        # Record a winning experience
        mem.record_experience(v_test, won=True)
        app, score, msg = mem.evaluate_candidate(v_test)
        assert app is True
        assert "MEM_CONFIRMED" in msg

        # Record a distinct losing experience and test veto
        v_trap = [0.1, 0.0, -0.9, 0.1, 0.1]
        mem.record_experience(v_trap, won=False)
        app_trap, score_trap, msg_trap = mem.evaluate_candidate(v_trap)
        assert app_trap is False
        assert "MEM_VETO" in msg_trap
