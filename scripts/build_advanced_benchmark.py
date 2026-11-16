"""Build and freeze the Advanced benchmark before indexing or retrieval experiments.

The PDF is the source of truth.  Every positive locator is checked against its
physical PDF page, and every negative probe is checked against all extracted
text.  Test labels are only consumed by the offline evaluator, never by the
agent or query builder.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path

import pymupdf


ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / "advanced" / "source" / "vietnam-2035.pdf"
OUT = ROOT / "advanced" / "benchmark" / "questions.json"
FREEZE = ROOT / "advanced" / "benchmark" / "freeze.json"
SOURCE_ID = "vietnam-2035-world-bank-2016"


def e(page: int, region: str, terms: list[str]) -> dict:
    return {"page": page, "region": region, "terms": terms}


# Each answerable question belongs to one primary group only.  Dev deliberately
# covers all five groups; test uses the exact 6/5/5/4/4 minimum distribution.
ANSWERABLE = [
    # DEV: table 4, image 3, chart 3, multi-hop 3, text 4.
    ("A01", "dev", "table", "Theo Bảng O.1, Việt Nam xếp hạng LPI tổng thể và hạ tầng năm 2014 lần lượt là bao nhiêu?", "48 và 44.", [e(66, "Table O.1, Vietnam 2014 row", ["Vietnam, 2014", "48", "44"])]),
    ("A02", "dev", "table", "Theo Bảng 4.1, từ 1995 đến 2015 số đô thị tăng từ bao nhiêu lên bao nhiêu?", "Từ 420 lên 775 đô thị.", [e(248, "Table 4.1, 1995 and 2015 rows", ["1995", "420", "2015", "775"])]),
    ("A03", "dev", "table", "Bảng B5.3.1 ước tính tổng chi phí do tác động của vệ sinh kém là bao nhiêu?", "780 triệu USD.", [e(293, "Table B5.3.1, Impact of poor sanitation row", ["estimated cost of poor sanitation", "780"])]),
    ("A04", "dev", "table", "Theo Bảng 7.1, tỷ lệ công chức trên 50 tuổi thay đổi thế nào từ 2005 đến 2012?", "Tăng từ 10,6% lên 22,0%, tức tăng 11,4 điểm phần trăm.", [e(399, "Table 7.1, Older than 50 years row", ["Older than 50 years", "10.6", "22.0"])]),
    ("A05", "dev", "image_or_diagram", "Bản đồ 4.3 cho thấy giá trị sản lượng công nghiệp trên mỗi km² tập trung cao nhất ở hai đô thị nào?", "Hà Nội và Thành phố Hồ Chí Minh.", [e(254, "Map 4.3", ["highest in Hanoi and Ho Chi Minh City", "MAP 4.3"])]),
    ("A06", "dev", "image_or_diagram", "Bản đồ 4.4 kết luận không gian đường phố của thành phố nào không phù hợp với giao thông đô thị?", "Hà Nội.", [e(265, "Map 4.4", ["Hanoi’s street space", "urban transport"])]),
    ("A07", "dev", "image_or_diagram", "Trong sơ đồ Hình 7.12, ba chức năng đầu tiên của trung tâm chính phủ là gì?", "Quản lý chiến lược; điều phối chính sách; theo dõi và cải thiện hiệu quả.", [e(397, "Figure 7.12", ["Managing strategically", "Coordinating policy", "Monitoring and improving performance"])]),
    ("A08", "dev", "chart", "Hình 5.1 phân bổ mức sử dụng nước giữa nông nghiệp và công nghiệp lần lượt bao nhiêu phần trăm?", "Nông nghiệp 81%, công nghiệp 15%.", [e(288, "Figure 5.1 pie chart", ["Agriculture", "81%", "Industrial", "15%"])]),
    ("A09", "dev", "chart", "Theo Hình 4.11, nhóm thành phố trên 2 triệu dân tăng tỷ trọng dân số bao nhiêu điểm phần trăm giai đoạn 1989–2009?", "5,6 điểm phần trăm.", [e(254, "Figure 4.11, >2 million bar", [">2 million", "5.6", "1989–2009"])]),
    ("A10", "dev", "chart", "Hình 6.35 và phần diễn giải dự báo tỷ lệ phụ thuộc người cao tuổi tăng từ bao nhiêu lên bao nhiêu trong giai đoạn 2015–2035?", "Từ 9,6 lên 21,7.", [e(363, "Figure 6.35 and adjacent paragraph", ["9.6", "21.7", "2015 and 2035"])]),
    ("A11", "dev", "multi_hop", "Kết hợp dự báo dân số cao tuổi và tỷ lệ phụ thuộc: đến 2035 có bao nhiêu người trên 65 tuổi và tỷ lệ phụ thuộc người cao tuổi là bao nhiêu?", "15,5 triệu người trên 65 tuổi và tỷ lệ phụ thuộc 21,7.", [e(50, "demographic paragraph", ["15.5 million", "older than 65"]), e(363, "old-age dependency paragraph", ["21.7", "2035"])]),
    ("A12", "dev", "multi_hop", "Đối chiếu đô thị hóa và giao thông: dân số đô thị hiện tại được nêu là bao nhiêu và mất khoảng bao lâu để đi 40 km từ trung tâm TP.HCM đến Bình Dương?", "30 triệu dân đô thị và gần hai giờ cho quãng đường 40 km.", [e(72, "urban transformation paragraph", ["30 million", "urban"]), e(248, "peri-urban travel paragraph", ["nearly two hours", "40 kilometers"])]),
    ("A13", "dev", "multi_hop", "So sánh hai chỉ báo môi trường: nông nghiệp chiếm bao nhiêu phần trăm sử dụng nước và rừng nguyên sinh đã giảm bao nhiêu phần trăm trong 20 năm?", "Nông nghiệp chiếm 81% sử dụng nước; rừng nguyên sinh giảm 79%.", [e(288, "Figure 5.1", ["Agriculture", "81%"]), e(288, "forests paragraph", ["primary forests", "79 percent"])]),
    ("A14", "dev", "text", "Báo cáo nêu bốn hướng cải cách tức thời nào để phục hồi tăng trưởng năng suất?", "Tạo môi trường cho khu vực tư nhân trong nước; cải tổ DNNN; củng cố liên kết doanh nghiệp FDI–nội địa; nâng kỹ năng và năng lực đổi mới.", [e(148, "productivity reform discussion", ["four fronts", "private sector", "SOE"])]),
    ("A15", "dev", "text", "Bốn nền tảng của nền kinh tế dẫn dắt bởi đổi mới trong Hộp 3.1 tập trung vào những gì?", "Tăng cầu tri thức trong doanh nghiệp; tăng năng lực học công nghệ; tăng sản xuất tri thức, nhân lực trình độ cao và R&D; liên tục nâng chất lượng và mức phù hợp của kỹ năng lao động qua giáo dục đại học.", [e(208, "Box 3.1", ["Foundation I", "Foundation II", "Foundation III", "Foundation IV"])]),
    ("A16", "dev", "text", "Báo cáo định nghĩa hiệu quả của chính phủ là gì?", "Năng lực của nhà nước trong việc xây dựng và thực thi chính sách và pháp luật.", [e(380, "government effectiveness paragraph", ["capability of the state", "formulate and implement policy and law"])]),
    ("A17", "dev", "text", "Mục tiêu giảm phát thải khí nhà kính năm 2030 của Việt Nam là bao nhiêu nếu không và nếu có hỗ trợ quốc tế?", "Giảm 8% so với kịch bản thông thường bằng nguồn lực trong nước, và tới 25% khi có hỗ trợ quốc tế.", [e(285, "NDC paragraph", ["8 percent", "25 percent", "international support"])]),

    # TEST: exact required distribution, labels frozen before retrieval work.
    ("A21", "test", "table", "Theo Bảng O.1, hạng hải quan của Việt Nam thay đổi từ năm 2007 sang 2014 như thế nào?", "Từ hạng 37 xuống hạng 61, tức kém hơn 24 bậc.", [e(66, "Table O.1, Customs column", ["Vietnam, 2007", "37", "Vietnam, 2014", "61"])]),
    ("A22", "test", "table", "Theo Bảng 4.1, tỷ lệ đất đô thị và tỷ lệ dân số đô thị năm 2015 là bao nhiêu?", "Đất đô thị chiếm 4,96% tổng diện tích và dân số đô thị chiếm 34,3%.", [e(248, "Table 4.1, 2015 row", ["2015", "4.96", "34.3"])]),
    ("A23", "test", "table", "Trong Bảng B5.3.1, chi phí tác động lên nguồn nước và du lịch lần lượt là bao nhiêu?", "287 triệu USD và 69 triệu USD.", [e(293, "Table B5.3.1, water sources and tourism rows", ["water sources", "287", "Tourism", "69"])]),
    ("A24", "test", "table", "Theo Bảng 5.1, nước biển dâng gây ba hậu quả chính nào?", "Xâm nhập mặn, mất đất và tác động đến nông nghiệp, đồng thời làm trầm trọng thời tiết cực đoan như nước dâng do bão.", [e(296, "Table 5.1, sea-level rise row", ["Sea-level rise", "Salinization", "loss of land", "storm surges"])]),
    ("A25", "test", "table", "Bảng 6.4 nêu cơ chế tài chính nào cho lộ trình nhanh đạt bảo hiểm 100% và bất lợi chính là gì?", "Dùng nguồn thu thuế chung; bất lợi là gánh nặng tài khóa ngắn hạn lớn hơn và ít thời gian xử lý các điểm kém hiệu quả hiện có.", [e(360, "Table 6.4, Faster route row", ["Faster route", "General tax revenue", "Larger short-term"])]),
    ("A26", "test", "table", "Theo Bảng 7.1, nhóm công chức dưới 30 tuổi thay đổi ra sao từ 2005 đến 2012?", "Giảm từ 23,8% xuống 18,0%, tức giảm 5,8 điểm phần trăm.", [e(399, "Table 7.1, Younger than 30 years row", ["Younger than 30 years", "23.8", "18.0"])]),
    ("A27", "test", "image_or_diagram", "Bản đồ 4.1 minh họa sự mở rộng đô thị của vùng kết tụ nào trong giai đoạn khoảng 2000–2010?", "Vùng kết tụ Thành phố Hồ Chí Minh.", [e(249, "Map 4.1", ["Urban expansion in the Ho Chi Minh City agglomeration", "2000–2010"])]),
    ("A28", "test", "image_or_diagram", "Bản đồ 4.2 minh họa vấn đề gì ở vùng ven Thành phố Hồ Chí Minh?", "Nhiều khu công nghiệp ở vùng ven còn trống hoặc có tỷ lệ lấp đầy rất thấp.", [e(251, "Map 4.2", ["industrial zones are empty", "periphery of Ho Chi Minh City"])]),
    ("A29", "test", "image_or_diagram", "Trong Bản đồ 4.2, hai khu công nghiệp ví dụ có tỷ lệ lấp đầy lần lượt là bao nhiêu?", "Tân Phú Trung 0,0% và Dầu Giây 2,5%.", [e(251, "Map 4.2 callouts", ["Tan Phu Trung", "0.0%", "Dau Giay", "2.5%"])]),
    ("A30", "test", "image_or_diagram", "Sơ đồ Hình 7.12 đề xuất cấu trúc nào để tinh gọn nguồn lực và hoạt động?", "Một trung tâm chính phủ được tăng cường.", [e(397, "Figure 7.12", ["strengthened center", "streamlining resources and operations"])]),
    ("A31", "test", "image_or_diagram", "Bản đồ 4.4 so sánh mạng đường Hà Nội với ba thành phố nào?", "Bangkok, Seoul và New York.", [e(265, "Map 4.4 city panels", ["HANOI", "BANGKOK", "SEOUL", "NEW YORK"])]),
    ("A32", "test", "chart", "Theo Hình O.2, tỷ lệ dân số trên 65 tuổi tăng từ bao nhiêu năm 2015 lên bao nhiêu năm 2035?", "Từ 6,7% lên 14,4%.", [e(50, "Figure O.2 and adjacent paragraph", ["6.7 percent", "14.4 percent", "2035"])]),
    ("A33", "test", "chart", "Theo Hình O.4, ba kịch bản tăng GDP bình quân đầu người 5%, 6% và 7% đưa mức năm 2035 đến khoảng bao nhiêu?", "Lần lượt gần 15.000 USD, 18.000 USD và 22.200 USD (PPP 2011).", [e(53, "Figure O.4 and adjacent paragraph", ["5.0 percent", "$15,000", "6 percent", "$18,000", "aspirational growth target", "$22,200"])]),
    ("A34", "test", "chart", "Hình 4.10 cho biết năm 2009 nhóm thành phố trên 2 triệu dân chiếm bao nhiêu phần trăm dân số Việt Nam?", "10,0%.", [e(254, "Figure 4.10, >2 million bar", [">2 million", "10.0", "2009"])]),
    ("A35", "test", "chart", "Trong Hình 5.1, hộ gia đình và dịch vụ lần lượt chiếm bao nhiêu phần trăm sử dụng nước?", "Hộ gia đình 3% và dịch vụ 2%.", [e(288, "Figure 5.1 pie chart", ["Households", "3%", "Services", "2%"])]),
    ("A36", "test", "chart", "Theo Hình 6.35, xu hướng tỷ lệ người cao tuổi so với dân số trong độ tuổi lao động sau 2015 là gì?", "Tăng nhanh và tiếp tục tăng qua các thập kỷ sau 2035.", [e(363, "Figure 6.35", ["increase rapidly", "2015", "2035", "2055"])]),
    ("A37", "test", "multi_hop", "Kết hợp kịch bản tăng trưởng và đô thị hóa: mức tăng GDP bình quân đầu người tối thiểu nào giúp đạt 18.000 USD năm 2035, và đô thị hiện đóng góp bao nhiêu GDP quốc gia?", "Tối thiểu 6% mỗi năm; khu vực đô thị đóng góp hơn một nửa GDP quốc gia.", [e(53, "growth scenario paragraph", ["minimum of 6 percent", "$18,000"]), e(72, "urban transformation paragraph", ["over half of national GDP"])]),
    ("A38", "test", "multi_hop", "Đối chiếu hạ tầng logistics và khu công nghiệp: hạ tầng LPI của Việt Nam năm 2014 xếp hạng bao nhiêu, và tỷ lệ lấp đầy bình quân của 212 khu đang hoạt động là bao nhiêu?", "Hạ tầng LPI xếp hạng 44; tỷ lệ lấp đầy bình quân là 66%.", [e(66, "LPI infrastructure paragraph", ["infrastructure", "44"]), e(249, "industrial zones paragraph", ["212", "occupancy rate", "66 percent"])]),
    ("A39", "test", "multi_hop", "So sánh hai thay đổi nhân khẩu học đến 2035: tỷ lệ dân số trên 65 tuổi và tỷ lệ phụ thuộc người cao tuổi đạt bao nhiêu?", "Tỷ lệ dân số trên 65 tuổi đạt 14,4%; tỷ lệ phụ thuộc người cao tuổi đạt 21,7.", [e(50, "older population paragraph", ["14.4 percent", "2035"]), e(363, "old-age dependency paragraph", ["21.7", "2035"])]),
    ("A40", "test", "multi_hop", "Kết hợp dữ liệu đất đô thị và giao thông: năm 2015 đất đô thị chiếm bao nhiêu phần trăm diện tích, còn đường chính và phụ quanh trung tâm Hà Nội chiếm bao nhiêu phần trăm diện tích?", "Đất đô thị chiếm 4,96%; đường chính và phụ quanh trung tâm Hà Nội chiếm 9,03%.", [e(248, "Table 4.1, 2015 row", ["2015", "4.96"]), e(265, "Map 4.4 road-area comparison", ["Hanoi", "9.03%"])]),
    ("A41", "test", "text", "Bốn biểu hiện hiện đại hóa kinh tế được báo cáo liệt kê là gì?", "Chuyển dịch cơ cấu; hướng ngoại và tham gia chuỗi giá trị toàn cầu; chuyển sang hệ thống định hướng thị trường với vai trò tư nhân tăng; chuyển dịch không gian từ nông thôn sang đô thị.", [e(150, "four transformations list", ["Structural transformation", "Outward orientation", "private sector", "Spatial transformation"])]),
    ("A42", "test", "text", "Vì sao tăng trưởng khu vực tư nhân trong nước bị suy giảm năng suất theo báo cáo?", "Do doanh nghiệp chủ yếu rất nhỏ, thiếu lợi ích quy mô, chuyên môn hóa và đổi mới; thâm dụng vốn tăng mà không có lợi ích quy mô làm năng suất vốn giảm.", [e(148, "domestic private firms paragraph", ["capital-intensive", "scale economies", "capital productivity"])]),
    ("A43", "test", "text", "Ba thuộc tính kết nối được báo cáo nêu để tham gia chuỗi giá trị là gì?", "Kết nối thể chế, kết nối vật chất và kết nối giữa người với người.", [e(66, "institutional and physical connectivity discussion", ["Institutional connectivity", "Physical connectivity"]), e(67, "people-to-people connectivity discussion", ["People-to-people connectivity", "third attribute"])]),
    ("A44", "test", "text", "Một trung tâm chính phủ được tăng cường có ba chức năng chính nào theo phần diễn giải?", "Lập kế hoạch chiến lược; điều phối và theo dõi hiệu quả; bảo đảm trách nhiệm giải trình.", [e(397, "strengthened center paragraph", ["strategic planning", "coordinating and monitoring performance", "ensuring accountability"])]),
]


UNANSWERABLE = [
    ("A18", "dev", "Báo cáo công bố ngân sách chính xác của tuyến metro Hà Nội số 5 là bao nhiêu?", "Báo cáo thảo luận giao thông đô thị nhưng không công bố ngân sách tuyến metro Hà Nội số 5.", ["Hanoi metro line 5", "metro line 5"]),
    ("A19", "dev", "Báo cáo nêu giá đóng cửa VN-Index ngày 31/12/2015 là bao nhiêu?", "Không có chuỗi giá chứng khoán hằng ngày hoặc giá đóng cửa VN-Index được yêu cầu.", ["VN-Index", "closing price"]),
    ("A20", "dev", "Báo cáo cho biết tên người đoạt Nobel Kinh tế năm 2035 là ai?", "Đây là thông tin tương lai, không tồn tại trong báo cáo xuất bản năm 2016.", ["Nobel Prize in Economics 2035", "Nobel economics 2035"]),
    ("A45", "test", "Bảng 4.1 cho biết diện tích đất đô thị riêng của Đà Nẵng năm 2015 là bao nhiêu?", "Bảng chỉ đưa tổng số toàn quốc, không tách riêng Đà Nẵng.", ["Da Nang urban land 2015", "Danang urban land 2015"]),
    ("A46", "test", "Báo cáo dự báo tỷ giá USD/VND chính xác vào ngày 1/1/2035 là bao nhiêu?", "Báo cáo không dự báo tỷ giá theo một ngày cụ thể trong năm 2035.", ["USD/VND on January 1 2035", "exchange rate on 1 January 2035"]),
    ("A47", "test", "Hình O.2 cho biết dân số trên 65 tuổi của riêng tỉnh Lào Cai năm 2035 là bao nhiêu?", "Hình O.2 là dữ liệu cấp quốc gia, không có dự báo riêng cho Lào Cai.", ["Lao Cai population over 65", "Lào Cai population over 65"]),
    ("A48", "test", "Bản đồ 4.2 cho biết giá thuê đất mỗi mét vuông của KCN Dầu Giây là bao nhiêu?", "Bản đồ nêu vị trí, năm thành lập, khoảng cách và tỷ lệ lấp đầy, không nêu giá thuê đất.", ["Dau Giay land rent", "Dau Giay rental price"]),
    ("A49", "test", "Báo cáo nêu lượng điện tiêu thụ của từng trung tâm dữ liệu AI tại Việt Nam năm 2035 là bao nhiêu?", "Báo cáo không có dữ liệu theo từng trung tâm dữ liệu AI cho năm 2035.", ["AI data center electricity", "AI datacenter electricity"]),
    ("A50", "test", "Bảng 7.1 cho biết mức lương trung vị của công chức trên 50 tuổi năm 2012 là bao nhiêu?", "Bảng 7.1 chỉ nêu cơ cấu tuổi theo phần trăm, không có mức lương.", ["median salary of civil servants", "median civil service salary"]),
]


def norm(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).casefold()
    return re.sub(r"\s+", " ", value).strip()


def locate(page: pymupdf.Page, item: dict) -> dict:
    blocks = [b for b in page.get_text("blocks") if b[4].strip()]
    page_text = page.get_text()
    normalized = norm(page_text)
    missing = [term for term in item["terms"] if norm(term) not in normalized]
    if missing:
        raise ValueError(f"PDF page {item['page']} missing terms {missing}")

    matched = [b for b in blocks if any(norm(t) in norm(b[4]) for t in item["terms"])]
    if not matched:
        matched = blocks
    x0 = min(b[0] for b in matched)
    y0 = min(b[1] for b in matched)
    x1 = max(b[2] for b in matched)
    y1 = max(b[3] for b in matched)
    excerpt = " ".join(b[4].strip().replace("\n", " ") for b in matched)
    return {
        "source_id": SOURCE_ID,
        "physical_pdf_page": item["page"],
        "printed_page": page_text.splitlines()[0].strip() or None,
        "region": item["region"],
        "bbox_points": [round(v, 2) for v in (x0, y0, x1, y1)],
        "evidence_excerpt": excerpt[:1800],
        "verification_terms": item["terms"],
    }


def canonical(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode()


def main() -> None:
    if not PDF.exists():
        raise SystemExit("Run scripts/download_advanced_source.py first")
    doc = pymupdf.open(PDF)
    questions = []
    for qid, split, group, question, answer, evidence in ANSWERABLE:
        gold = [locate(doc[item["page"] - 1], item) for item in evidence]
        questions.append({
            "id": qid,
            "split": split,
            "answerable": True,
            "primary_group": group,
            "question": question,
            "expected_answer": answer,
            "gold": gold,
            "grading": "All stated values/conditions must be correct and supported by every required gold region.",
        })

    all_text = norm("\n".join(page.get_text() for page in doc))
    for qid, split, question, reason, terms in UNANSWERABLE:
        found = [term for term in terms if norm(term) in all_text]
        if found:
            raise ValueError(f"{qid}: absence probe unexpectedly found: {found}")
        questions.append({
            "id": qid,
            "split": split,
            "answerable": False,
            "primary_group": "unanswerable",
            "question": question,
            "expected_behavior": "search_then_abstain_without_unsupported_claims",
            "absence_reason": reason,
            "absence_check": {"scope": "all_409_physical_pages", "searched_phrases": terms},
        })

    questions.sort(key=lambda row: int(row["id"][1:]))
    counts = Counter((q["split"], q["primary_group"]) for q in questions)
    expected = {
        ("dev", "table"): 4, ("dev", "image_or_diagram"): 3,
        ("dev", "chart"): 3, ("dev", "multi_hop"): 3,
        ("dev", "text"): 4, ("dev", "unanswerable"): 3,
        ("test", "table"): 6, ("test", "image_or_diagram"): 5,
        ("test", "chart"): 5, ("test", "multi_hop"): 4,
        ("test", "text"): 4, ("test", "unanswerable"): 6,
    }
    if counts != Counter(expected):
        raise ValueError(f"Unexpected benchmark distribution: {counts}")
    if any(q["primary_group"] == "multi_hop" and len(q["gold"]) < 2 for q in questions if q["answerable"]):
        raise ValueError("Every multi-hop question requires at least two evidence regions")

    payload = {
        "benchmark_id": "vietnam-2035-multimodal-v1",
        "source_id": SOURCE_ID,
        "created_before_retrieval_experiments": True,
        "test_policy": "sealed_until_pipeline_freeze",
        "questions": questions,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_bytes(canonical(payload))
    digest = hashlib.sha256(OUT.read_bytes()).hexdigest()
    freeze = {
        "benchmark_file": str(OUT.relative_to(ROOT)).replace("\\", "/"),
        "sha256": digest,
        "question_count": len(questions),
        "distribution": {f"{split}.{group}": count for (split, group), count in sorted(counts.items())},
        "sealed_test": True,
        "selection_split": "dev",
    }
    FREEZE.write_bytes(canonical(freeze))
    print(json.dumps(freeze, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
