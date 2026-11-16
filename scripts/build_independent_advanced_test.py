"""Create the independent post-improvement Test before its first pipeline run."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "advanced/benchmark_v2"


SPECS = [
    ("N01","table","Theo Bảng 2.1, tăng trưởng GDP bình quân năm giảm từ mức nào giai đoạn 1991–2000 xuống mức nào giai đoạn 2001–13?","Từ 7,6% xuống 6,6%",[(166,["Average annual GDP growth","7.6","6.6"],"Table 2.1 GDP growth row")]),
    ("N02","table","Theo Bảng 3.1, Việt Nam xếp hạng GCI 2015–16 bao nhiêu và đạt điểm số nào?","Hạng 56, điểm 4,30",[(210,["Vietnam 56 4.30 68"],"Table 3.1 Vietnam row")]),
    ("N03","table","Theo Bảng 3.7, tổng số giảng viên tăng từ bao nhiêu năm 2005 lên bao nhiêu năm 2012?","Từ 48.266 lên 87.317",[(231,["Total 48,266 74,573 84,109 87,317"],"Table 3.7 total row")]),
    ("N04","table","Theo Bảng 6.1, tử vong trẻ sơ sinh trên 1.000 ca sinh sống giảm từ bao nhiêu năm 1993 xuống bao nhiêu khoảng năm 2012?","Từ 33 xuống 19",[(323,["Infant mortality","33 19"],"Table 6.1 infant mortality row")]),
    ("N05","table","Theo Bảng 4.2, tỷ lệ lấp đầy khu công nghiệp của TP.HCM và Hà Nội năm 2013 lần lượt là bao nhiêu?","56,4% và 44,7%",[(250,["Ho Chi Minh City 56.4","Hanoi 44.7"],"Table 4.2 city rows")]),
    ("N06","table","Theo Bảng 2.1, đóng góp của chuyển dịch cơ cấu tăng từ bao nhiêu lên bao nhiêu giữa hai giai đoạn?","Từ 0,2% lên 63%",[(166,["Structural transformation 0.2 63"],"Table 2.1 structural transformation row")]),
    ("N07","image_or_diagram","Hình 3.4 cho thấy nhà quản lý Việt Nam mạnh ở khía cạnh nào nhưng yếu ở những khía cạnh chính nào?","Mạnh về giám sát; yếu về mục tiêu dài hạn, công nghệ/thực hành mới và chính sách nhân sự",[(218,["strong on monitoring","weak on setting long-term targets"],"Figure 3.4 and interpretation")]),
    ("N08","image_or_diagram","Hình 2.23 minh họa đặc điểm gì của xuất khẩu điện tử Việt Nam?","Hàm lượng nhập khẩu cao, phụ thuộc nhiều vào linh kiện nhập khẩu",[(191,["High import content of electronics exports","imported components"],"Figure 2.23 and adjacent text")]),
    ("N09","image_or_diagram","Thông điệp chính của Hình 4.7 về năng suất trong các khu công nghiệp là gì?","Năng suất trong khu công nghiệp cao hơn các thành phố lân cận",[(250,["Productivity is higher in industrial zones than in neighboring cities"],"Figure 4.7 caption")]),
    ("N10","image_or_diagram","Hình 4.15 mô tả thay đổi nào sau khi Thái Nguyên đạt đô thị loại I năm 2009?","Thu ngân sách địa phương gần như tăng gấp đôi",[(262,["After receiving Class I status in 2009","local receipts nearly doubled"],"Figure 4.15 caption")]),
    ("N11","image_or_diagram","Hình 6.27 đặt thành tích học tập quốc tế của Việt Nam trong tương quan nào?","Việt Nam đạt điểm cao hơn nhiều nước giàu",[(350,["Vietnam excels in international tests","above many rich countries"],"Figure 6.27")]),
    ("N12","chart","Hình 2.14 cho thấy xu hướng tăng trưởng năng suất lao động từ cuối thập niên 1990 như thế nào?","Có xu hướng giảm",[(165,["Labor productivity growth has been on a declining trend since the late 1990s"],"Figure 2.14")]),
    ("N13","chart","Hình 5.9 cho thấy loại phương tiện nào dẫn dắt mức tăng sở hữu phương tiện đô thị giai đoạn 2000–11?","Xe máy",[(300,["Motorcycles have seen the fastest rise","FIGURE 5.9"],"Figure 5.9 and text")]),
    ("N14","chart","Hình 2.17 so sánh năng suất doanh nghiệp tư nhân trong nước quy mô lớn với doanh nghiệp nhỏ như thế nào?","Doanh nghiệp lớn trung bình kém năng suất hơn doanh nghiệp nhỏ",[(168,["FIGURE 2.17","Large domestic private","less productive than smaller private"],"Figure 2.17")]),
    ("N15","chart","Hình 6.38 dự báo chi tiêu lương hưu của Việt Nam thay đổi thế nào trong những năm tới?","Hiện thấp nhưng dự kiến tăng nhanh",[(365,["low pension spending","expected to rise quickly"],"Figure 6.38")]),
    ("N16","chart","Hình 3.4 ghi điểm giám sát của Việt Nam là bao nhiêu?","2,82",[(218,["Vietnam","2.82"],"Figure 3.4 Vietnam monitoring score")]),
    ("N17","text","VAMC được thành lập năm nào, với vốn ban đầu bao nhiêu và tăng lên bao nhiêu vào tháng 4/2015?","Năm 2013; 500 tỷ đồng; tăng lên 2 nghìn tỷ đồng",[(182,["established in 2013","500","2 trillion in April 2015"],"Box 2.8")]),
    ("N18","text","Luật Doanh nghiệp 2005 đã thống nhất điều gì và mở đường cho cột mốc quốc tế nào năm 2007?","Thống nhất khung pháp lý giữa các loại hình sở hữu và mở đường gia nhập WTO năm 2007",[(159,["regulatory framework","paved the way","WTO","2007"],"Enterprise Law paragraph")]),
    ("N19","text","Nghiên cứu được báo cáo dẫn lại cho thấy thêm một nhà khai thác di động ở châu Phi làm số thuê bao tăng bao nhiêu?","57%",[(175,["mobile phone opera","57 percent (Gebreab"],"Competition evidence paragraph")]),
    ("N20","text","Đến năm 2015, khu vực FDI đóng góp bao nhiêu vào sản lượng chế tạo và kim ngạch xuất khẩu?","Hơn một nửa sản lượng chế tạo và hơn 70% kim ngạch xuất khẩu",[(168,["over half of manufacturing output","over 70 percent of export turnover"],"FDI contribution paragraph")]),
    ("N21","multi_hop","Kết hợp năng lực đổi mới và vai trò FDI: chi R&D ước tính chiếm bao nhiêu GDP, còn FDI đóng góp thế nào cho chế tạo và xuất khẩu năm 2015?","Khoảng 0,3% GDP; FDI đóng góp hơn nửa sản lượng chế tạo và hơn 70% xuất khẩu",[(210,["0.3 percent of GDP"],"R&D estimate"),(168,["over half of manufacturing output","over 70 percent"],"FDI contribution")]),
    ("N22","multi_hop","Kết hợp Bảng 2.1 và Hình 2.14: tăng trưởng năng suất lao động giảm từ bao nhiêu xuống bao nhiêu giữa hai giai đoạn, và xu hướng dài hạn được mô tả thế nào?","Từ 5,2% xuống 3,8%; xu hướng giảm từ cuối thập niên 1990",[(166,["Labor productivity growth 5.2 3.8"],"Table 2.1"),(165,["declining trend since the late 1990s"],"Figure 2.14")]),
    ("N23","multi_hop","Kết hợp dữ liệu xã hội và giao thông: tử vong trẻ sơ sinh giảm từ bao nhiêu xuống bao nhiêu, còn giao thông công cộng chiếm bao nhiêu chuyến đi ở Hà Nội và TP.HCM?","33 xuống 19; khoảng 7% ở Hà Nội và 5% ở TP.HCM",[(323,["Infant mortality","33 19"],"Table 6.1"),(300,["Hanoi","7 percent","Ho Chi Minh City","5 percent"],"Transport paragraph")]),
    ("N24","multi_hop","Kết hợp giáo dục đại học và đổi mới: tổng số giảng viên năm 2012 là bao nhiêu, trong khi chi R&D ước tính chiếm bao nhiêu GDP?","87.317 giảng viên và khoảng 0,3% GDP",[(231,["Total 48,266 74,573 84,109 87,317"],"Table 3.7"),(210,["0.3 percent of GDP"],"R&D estimate")]),
]

NEGATIVES = [
    ("N25","Bảng 2.1 cho biết GDP của riêng tỉnh Quảng Ninh năm 2013 là bao nhiêu?","Bảng chỉ có số liệu tăng trưởng cấp quốc gia."),
    ("N26","Hình 5.9 dự báo chính xác số ô tô điện tại Hà Nội năm 2035 là bao nhiêu?","Hình không dự báo ô tô điện theo thành phố năm 2035."),
    ("N27","Báo cáo cho biết giá cổ phiếu VAMC ngày 31/12/2015 là bao nhiêu?","VAMC không được trình bày như cổ phiếu niêm yết và báo cáo không có giá này."),
    ("N28","Bảng 3.7 cho biết mức lương trung bình của từng giảng viên năm 2012 là bao nhiêu?","Bảng chỉ có số lượng theo trình độ."),
    ("N29","Hình 6.27 cho biết điểm PISA của riêng học sinh tỉnh Huế là bao nhiêu?","Hình so sánh cấp quốc gia, không có số liệu tỉnh Huế."),
    ("N30","Báo cáo dự báo tên doanh nghiệp xuất khẩu điện tử lớn nhất Việt Nam năm 2035 là gì?","Báo cáo không đưa dự báo doanh nghiệp cụ thể cho năm 2035."),
]


def main() -> None:
    chunks = json.loads((ROOT / "advanced/derived/chunks.json").read_text(encoding="utf-8"))
    questions = []
    for qid, group, question, expected, gold_specs in SPECS:
        gold = []
        for page, terms, region in gold_specs:
            matches = [row for row in chunks if row["page"] == page and all(term.casefold() in row["text"].casefold() for term in terms)]
            if len(matches) != 1:
                raise ValueError(f"{qid}: expected one evidence block for page {page}, got {len(matches)}")
            row = matches[0]
            gold.append({"source_id": row["source_id"], "physical_pdf_page": page, "region": region,
                         "evidence_excerpt": row["text"], "verification_terms": terms})
        questions.append({"id": qid, "split": "test", "answerable": True, "primary_group": group,
                          "question": question, "expected_answer": expected, "gold": gold,
                          "grading": "All stated values/conditions must be correct and supported by every required gold region."})
    for qid, question, reason in NEGATIVES:
        questions.append({"id": qid, "split": "test", "answerable": False, "primary_group": "unanswerable",
                          "question": question, "expected_behavior": "search_then_abstain_without_unsupported_claims",
                          "absence_reason": reason, "absence_check": {"scope": "all_409_physical_pages"}})
    counts = {group: sum(row["primary_group"] == group for row in questions) for group in
              ("table","image_or_diagram","chart","multi_hop","text","unanswerable")}
    assert counts == {"table":6,"image_or_diagram":5,"chart":5,"multi_hop":4,"text":4,"unanswerable":6}
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    payload = {"benchmark_id":"vietnam-2035-independent-v2","created_after_pipeline_freeze":True,
               "test_policy":"sealed_until_v2_pipeline_freeze","questions":questions}
    question_path = OUT_DIR / "questions.json"
    question_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    freeze = {"benchmark_id":payload["benchmark_id"], "question_count":30, "group_counts":counts,
              "questions_sha256":hashlib.sha256(question_path.read_bytes()).hexdigest(), "test_run_count":0}
    (OUT_DIR / "freeze.json").write_text(json.dumps(freeze, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"benchmark":"PASS","questions":30,"groups":counts}))


if __name__ == "__main__":
    main()
