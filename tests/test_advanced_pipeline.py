import unittest

from src.advanced_pipeline import (
    pack_page_aware_context,
    prioritize_query_facets,
    question_requirements,
    reciprocal_rank_fuse,
)


class AdvancedPipelineTests(unittest.TestCase):
    def test_extracts_explicit_multi_part_requirements(self):
        parts = question_requirements(
            "Năm 2015 đất đô thị chiếm bao nhiêu phần trăm, còn đường quanh Hà Nội chiếm bao nhiêu phần trăm?"
        )
        self.assertEqual(len(parts), 2)
        self.assertIn("đất đô thị", parts[0])
        self.assertIn("đường quanh Hà Nội", parts[1])

    def test_drops_multi_hop_instruction_preamble(self):
        parts = question_requirements(
            "Kết hợp hai nguồn: đến 2035 có bao nhiêu người trên 65 tuổi và tỷ lệ phụ thuộc là bao nhiêu?"
        )
        self.assertEqual(len(parts), 2)
        self.assertTrue(parts[0].startswith("đến 2035"))

    def test_multi_query_rrf_rewards_cross_query_evidence(self):
        common = {"id": "shared", "text": "x", "source": "s", "page": 1}
        rows = reciprocal_rank_fuse([
            [common, {**common, "id": "only-a"}],
            [{**common, "id": "only-b"}, common],
        ])
        self.assertEqual(rows[0]["id"], "shared")
        self.assertEqual(rows[0]["query_ranks"], {"0": 1, "1": 2})

    def test_facet_priority_keeps_unique_subquery_result(self):
        base = {"text": "x", "source": "s", "page": 1}
        shared = {**base, "id": "shared"}
        unique = {**base, "id": "unique", "page": 50}
        fused = reciprocal_rank_fuse([[shared], [shared, unique]])
        ordered = prioritize_query_facets(fused, [[shared], [shared, unique]], depth=2)
        self.assertEqual([row["id"] for row in ordered[:2]], ["shared", "unique"])

    def test_page_aware_context_keeps_diverse_pages_and_neighbors(self):
        chunks = [
            {"id": f"c{page}", "text": f"page {page}", "source": "doc.pdf", "page": page}
            for page in range(1, 8)
        ]
        ranked = [
            {**chunks[1], "rank": 1},
            {**chunks[5], "rank": 2},
        ]
        context, ids, pages = pack_page_aware_context(ranked, chunks, budget_chars=5000)
        self.assertIn("c2", ids)
        self.assertIn("c6", ids)
        self.assertTrue({1, 2, 3, 5, 6, 7}.issubset(set(pages)))
        self.assertIn("page 6", context)

    def test_context_keeps_lower_ranked_candidate_before_expansion(self):
        chunks = [
            {"id": f"c{page}", "text": "x" * 50, "source": "doc.pdf", "page": page}
            for page in range(1, 15)
        ]
        ranked = [{**row, "rank": rank} for rank, row in enumerate(chunks, 1)]
        _, ids, _ = pack_page_aware_context(ranked, chunks, budget_chars=5000, seed_pages=2)
        self.assertIn("c13", ids)


if __name__ == "__main__":
    unittest.main()
