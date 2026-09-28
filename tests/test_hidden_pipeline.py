from pathlib import Path

from hidden_test_ready.run_hidden_test import run_pipeline_on_unseen_doc
from src.schemas.comparison_contract import VerificationStatus


class TestHiddenPipeline:
    def test_unseen_policy_executes_end_to_end_without_manual_intervention(self, tmp_path):
        sample_doc = Path("hidden_test_ready") / "sample_unseen_policy.pdf"
        result = run_pipeline_on_unseen_doc(sample_doc, target_role="DevOps Engineer", use_live_llm=False)

        assert result["chunks_extracted"] >= 3
        assert result["status"] == VerificationStatus.VERIFIED.value
        assert result["match_score"] >= 0.85
        assert result["hallucinations_detected"] == 0
        assert result["security_threats_detected"] == 0
