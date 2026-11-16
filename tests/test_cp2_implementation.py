import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.local_agent import LocalQwen, pack_context
from src.retrieval import BM25Retriever


class CP2ImplementationTests(unittest.TestCase):
    def setUp(self):
        self.chunks = json.loads((ROOT / "data/day6/chunks.json").read_text(encoding="utf-8"))

    def test_bm25_returns_ranked_unique_results_and_filter(self):
        index = BM25Retriever(self.chunks)
        rows = index.search("BASIC ngôn ngữ lập trình", top_k=3)
        self.assertEqual([row["rank"] for row in rows], [1, 2, 3])
        self.assertEqual(len({row["id"] for row in rows}), 3)
        filtered = index.search("Transformer chú ý", filters={"collection": "khoa_hoc_may_tinh"}, top_k=3)
        self.assertTrue(filtered)
        self.assertTrue(all(row["metadata"]["collection"] == "khoa_hoc_may_tinh" for row in filtered))

    def test_context_budget_and_ids(self):
        rows = BM25Retriever(self.chunks).search("BASIC", top_k=3)
        context, ids = pack_context(rows, 1500)
        self.assertLessEqual(len(context), 1500)
        self.assertTrue(ids)
        self.assertTrue(all(chunk_id in context for chunk_id in ids))

    def test_exact_evidence_format_recovery_is_grounded(self):
        controller = LocalQwen.__new__(LocalQwen)
        controller.generate = lambda messages, max_new_tokens: "SUPPORTED: Dữ kiện đúng."
        answer, citations, _ = controller.answer(
            "Dữ kiện nào?", "[c1 | source | trang 1]\nDữ kiện đúng.", ["c1"]
        )
        self.assertEqual(citations, ["c1"])
        self.assertIn("[c1]", answer)
        controller.generate = lambda messages, max_new_tokens: "SUPPORTED: Dữ kiện bịa."
        answer, citations, _ = controller.answer(
            "Dữ kiện nào?", "[c1 | source | trang 1]\nDữ kiện đúng.", ["c1"]
        )
        self.assertEqual(citations, [])


if __name__ == "__main__":
    unittest.main()
