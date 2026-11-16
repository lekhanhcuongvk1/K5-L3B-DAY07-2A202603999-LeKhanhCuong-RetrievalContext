"""Build and freeze the new Day 7 benchmark before any retrieval experiment."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHUNKS = ROOT / "data" / "day6" / "chunks.json"
OUTPUT = ROOT / "benchmark" / "base_questions.json"
FREEZE = ROOT / "benchmark" / "base_freeze.json"


ANSWERABLE = [
    ("B01", "dev", "Tên đầy đủ tạo nên chữ viết tắt BASIC là gì?", "Beginner's All-purpose Symbolic Instruction Code.", "BASIC là viết tắt của B eginner's A ll-purpose S ymbolic I nstruction C ode trong tiếng Anh .", None),
    ("B02", "dev", "Ngôn ngữ Ada được đặt tên theo ai?", "Ada Augusta, nữ bá tước xứ Lovelace.", "Ngôn ngữ này được đặt tên theo Ada Augusta nữ bá tước xứ Lovelace (1815 – 1852)", None),
    ("B03", "dev", "Ai tạo ra ngôn ngữ D và ngôn ngữ này được phát hành năm nào?", "Walter Bright của Digital Mars tạo ra D và phát hành năm 2001.", "D là một ngôn ngữ lập trình hệ thống hướng đối tượng , dùng câu lệnh , đa mẫu hình do Walter Bright của Digital Mars tạo ra và phát hành năm 2001.", None),
    ("B04", "dev", "Ngoài ảnh hưởng tới các ngôn ngữ khác, APL đã ảnh hưởng lớn đến bốn lĩnh vực nào?", "Mô hình hóa khái niệm, bảng tính, lập trình hàm và gói tính toán máy tính.", "Nó đã có ảnh hưởng lớn đến sự phát triển của mô hình hóa khái niệm, bảng tính , lập trình hàm , và gói tính toán máy tính.", {"collection": "ngon_ngu_lap_trinh"}),
    ("B05", "dev", "Ai là người thiết kế chủ yếu C# và phiên bản 9.0 được phát hành cùng sản phẩm nào?", "Anders Hejlsberg; C# 9.0 được phát hành cùng Visual Studio 2019 phiên bản 16.8.", "C# được thiết kế chủ yếu bởi Anders Hejlsberg kiến trúc sư phần mềm nổi tiếng với các sản phẩm Turbo Pascal , Delphi , J++, WFC. Phiên bản gần đây nhất là 9.0, được phát hành vào năm 2020 cùng với Visual Studio 2019 phiên bản 16.8.", None),
    ("B06", "dev", "Nhận định ALGOL 68 không có triển khai và người dùng chỉ đúng một phần vì ngôn ngữ này từng được dùng ở đâu?", "Nó được dùng trong các thị trường thích hợp, đặc biệt tại Vương quốc Anh trên máy ICL và trong giảng dạy.", "ALGOL 68 đã được sử dụng trong một số thị trường thích hợp, đặc biệt là ở Vương quốc Anh nơi nó phổ biến trên các máy ICL và trong vai trò giảng dạy.", None),
    ("B07", "dev", "Bộ tự mã hóa được nêu là ứng dụng trong bốn bài toán nào?", "Nhận dạng khuôn mặt, phát hiện đặc trưng, phát hiện bất thường và học nghĩa của từ.", "Bộ tự mã hóa được ứng dụng trong nhiều bài toán, bao gồm nhận dạng khuôn mặt , phát hiện đặc trưng , phát hiện bất thường , và học nghĩa của từ .", {"collection": "khoa_hoc_may_tinh"}),
    ("B08", "dev", "MNIST chứa loại dữ liệu nào, các chữ số trong phạm vi nào và do những ai tạo ra?", "Các chữ số viết tay từ 0 đến 9; Yann LeCun, Corinna Cortes và Christopher J.C. Burges.", "là một cơ sở dữ liệu lớn gồm các chữ số viết tay từ 0 đến 9, được tạo ra bởi Yann LeCun , Corinna Cortes và Christopher J.C. Burges .", None),
    ("B09", "dev", "ImageNet được xây dựng từ năm nào, bởi ai, và cuối cùng có quy mô khoảng bao nhiêu?", "Fei-Fei Li và cộng sự xây dựng từ năm 2007; hơn 14 triệu ảnh có nhãn thuộc 22.000 danh mục.", "Tập dữ liệu ImageNet , yếu tố trung tâm cho thành công của AlexNet, được Fei-Fei Li và các cộng sự xây dựng từ năm 2007. Với mục tiêu thúc đẩy nhận dạng hình ảnh qua dữ liệu quy mô lớn, Li đã tạo ra một tập dữ liệu lớn hơn nhiều so với các nỗ lực trước đó, cuối cùng chứa hơn 14 triệu ảnh có nhãn thuộc 22.000 danh mục.", None),
    ("B10", "dev", "Hai nguyên nhân chính nào làm dấy lên lo ngại về bong bóng AI?", "Vòng đầu tư tuần hoàn giữa các công ty AI làm tăng giá trị cổ phiếu nhưng chưa thu hồi vốn, cùng sự tương đồng với bong bóng dot-com.", "Lo ngại về bong bóng phần lớn xuất phát từ việc các công ty công nghệ AI hàng đầu tham gia vào một vòng đầu tư tuần hoàn nhằm thổi phồng giá trị cổ phiếu của nhau, trong khi không thu lại được số tiền vốn bỏ ra. Bên cạnh đó, nhiều người cũng đưa ra sự so sánh giữa môi trường tài chính công nghệ hiện tại với bong bóng dot-com vào cuối thập niên 1990 và đầu thập niên 2000.", None),
    ("B11", "dev", "ChatGPT ra mắt khi nào và mất bao lâu để đạt 100 triệu người dùng?", "Ra mắt cuối năm 2022 và đạt 100 triệu người dùng trong hai tháng.", "ChatGPT – một chatbot do OpenAI phát triển, ra mắt vào cuối năm 2022 và đạt 100 triệu người dùng chỉ trong vòng hai tháng", None),
    ("B12", "dev", "Ai giới thiệu VAE vào năm 2013 và VAE có khả năng chính nào của mô hình tạo sinh?", "Diederik P. Kingma và Max Welling; VAE có thể tạo dữ liệu mới.", "Bộ mã hóa tự động biến phân , hay bộ tự mã hóa biến phân ( tiếng Anh : Variational Autoencoder , viết tắt VAE ) là một kiến trúc mạng neuron nhân tạo do Diederik P. Kingma và Max Welling giới thiệu năm 2013. VAE là một mô hình xác suất đồ thị và phương pháp Bayes biến phân , đồng thời là một dạng mô hình tạo sinh có khả năng tạo ra dữ liệu mới.", None),
    ("B13", "dev", "Transformer năm 2017 thay thế xử lý tuần tự của RNN bằng cơ chế nào và đem lại lợi ích gì?", "Transformer chỉ dùng tự chú ý và cho phép xử lý song song toàn bộ chuỗi.", "Năm 2017, Vaswani và cộng sự công bố kiến trúc Transformer trong bài báo \" Attention is all you need \" nổi tiếng, loại bỏ hoàn toàn thành phần hồi quy và chỉ dùng tự chú ý làm cơ chế tính toán chính, cho phép xử lý song song toàn bộ chuỗi thay vì tuần tự từng ký tự như RNN.", {"collection": "khoa_hoc_may_tinh"}),
    ("B14", "dev", "Trong Nobel Hóa học 2024 liên quan đến protein, Demis Hassabis và John Jumper được trao giải cho công trình gì, còn David Baker cho công trình gì?", "Hassabis và Jumper cho dự đoán cấu trúc protein; Baker cho thiết kế protein bằng tính toán.", "Năm 2024, hai lãnh đạo nhóm nghiên cứu của Google DeepMind trong dự án Alphafold Demis Hassabis và John Jumper được trao một nửa giải Nobel Hóa học \"cho công trình dự đoán cấu trúc protein\", nửa giải còn lại thuộc về David Baker \"cho công trình thiết kế protein bằng tính toán\".", None),
    ("B15", "dev", "Theo mô tả của Liskov và Zilles năm 1974, điều kiện nào làm một ngôn ngữ được gọi là kiểu mạnh?", "Khi một đối tượng truyền giữa hàm gọi và hàm được gọi, kiểu của nó phải tương thích với kiểu khai báo trong nguyên mẫu hàm được gọi.", "Vào năm 1974, Liskov và Zilles mô tả một ngôn ngữ lập trình \"kiểu mạnh\" là ở ngôn ngữ đó \"mỗi khi một đối tượng được truyền từ hàm đang gọi sang hàm được gọi, kiểu của nó phải tương thích với kiểu khai báo trong nguyên mẫu của hàm được gọi.\"", None),
    ("B16", "dev", "GCC là trình dịch tiêu chuẩn trên những hệ điều hành giống Unix nào được nêu, và còn có thể biên dịch cho hai nền tảng di động nào?", "Linux và Mac OS X; Android và iOS.", "GCC là một thành phần quan trọng của GNU toolchain , và được hầu hết các hệ điều hành giống Unix , như Linux và Mac OS X chọn làm trình dịch tiêu chuẩn. Các dòng hệ điều hành BSD đa phần đều sử dụng GCC, dù một số dòng như FreeBSD và OpenBSD lại sử dụng Clang làm trình biên dịch chuẩn. Các phiên bản sau đó của GCC cũng hỗ trợ trên cả Microsoft Windows và một số hệ điều hành khác. GCC cũng có thể biên dịch chương trình cho cả Android và iOS .", None),
    ("B17", "dev", "Trong AWK, các cột của tệp được gọi là gì và ba cột đầu được đặt tên ra sao?", "Các cột được xem là các trường, đặt tên $1, $2 và $3.", "Với một file như vậy các cột được Awk xem như các trường và được đặt tên $1 cho cột thứ nhất, $2 cho cột thứ hai, $3 cho cột thứ ba,...", None),
    ("B18", "dev", "Batch chạy dựa trên các phần mở rộng tệp nào và được thực thi trong môi trường gì?", "Các tệp .bat và .cmd, thực thi trong cửa sổ Command Prompt.", "Batch là một ngôn ngữ lập trình được dựa trên các tập tin thực thi batch (*.bat, *.cmd,...) để chạy. Chúng sẽ được thực thi dưới dạng một cửa sổ Command Prompt để chạy những dòng lệnh.", {"collection": "ngon_ngu_lap_trinh"}),
    ("B22", "test", "Mục đích ban đầu của AutoIt là gì?", "Tạo các tập lệnh tự động hóa cho chương trình Microsoft Windows.", "Trong bản phát hành đầu tiên, nó chủ yếu nhằm tạo ra các tập lệnh tự động hóa (đôi khi còn được gọi là macros ) cho các chương trình Microsoft Windows", None),
    ("B23", "test", "Ngành tương tác người–máy tập trung giải quyết thách thức gì?", "Làm cho máy tính và công việc tính toán hữu ích, dễ sử dụng với mọi người dùng.", "ngành tương tác người-máy tập trung vào những thách thức trong việc làm cho máy tính và công việc tính toán hữu ích, và dễ sử dụng đối với mọi người dùng.", {"collection": "khoa_hoc_may_tinh"}),
    ("B24", "test", "C++11 được ISO chấp nhận vào ngày nào và thay thế tiêu chuẩn nào?", "Ngày 12 tháng 4 năm 2011, thay thế C++03.", "Tiêu chuẩn này được chấp nhận bởi tổ chức ISO vào ngày 12 tháng 4 năm 2011 nhằm thay thế cho tiêu chuẩn C++03.", None),
    ("B25", "test", "Cấu trúc dữ liệu B-tree đặc biệt phù hợp với loại ứng dụng nào?", "Thiết kế cơ sở dữ liệu.", "Ví dụ, các B-tree đặc biệt phù hợp trong việc thiết kế cơ sở dữ liệu.", None),
    ("B26", "test", "Trong cây biểu diễn tập hợp rời nhau, phần tử đại diện đóng vai trò gì và các phần tử còn lại là gì?", "Phần tử đại diện là gốc cây; các phần tử còn lại là các nút của cây.", "Để dùng cây biểu diễn tập, ta chọn một phần tử trong tập hợp làm đại diện cho tập. Phần tử này sẽ làm gốc của cây. Các phần tử khác trong tập là các nút của cây.", None),
    ("B27", "test", "Thiết bị không hiển thị thông điệp có thể thay dòng chữ Hello World bằng tín hiệu nào?", "Bật sáng đèn LED.", "Trong các thiết bị không hiển thị thông điệp, một chương trình đơn giản là phát sinh tín hiệu, như bật đèn LED sáng để thay thế cho dòng chữ \"Hello world\" như là một chương trình chỉ dẫn.", {"collection": "ngon_ngu_lap_trinh"}),
]


UNANSWERABLE = [
    ("B19", "dev", "Rust sử dụng bộ kiểm tra mượn như thế nào để bảo đảm an toàn bộ nhớ?", "Corpus có nhắc nhiều ngôn ngữ nhưng không có tài liệu về Rust hoặc borrow checker.", ["borrow checker", "kiểm tra mượn"]),
    ("B20", "dev", "GPT-4o hỗ trợ tối đa bao nhiêu phút âm thanh trong một request API?", "Corpus không có tài liệu về giới hạn âm thanh hoặc API của GPT-4o.", ["gpt-4o", "GPT-4o"]),
    ("B21", "dev", "Python 3.13 thay đổi cơ chế Global Interpreter Lock ra sao?", "Corpus chỉ nhắc Python như nguồn cảm hứng hoặc ví dụ, không mô tả Python 3.13 hay thay đổi GIL.", ["Python 3.13", "Global Interpreter Lock"]),
    ("B28", "test", "AlphaFold 3 sử dụng learning rate chính xác bao nhiêu trong lần huấn luyện cuối?", "Tài liệu AlphaFold không cung cấp learning rate huấn luyện AlphaFold 3.", ["learning rate", "tốc độ học"]),
    ("B29", "test", "CIFAR-10 được thu thập bằng loại máy ảnh nào và khẩu độ ống kính bao nhiêu?", "Tài liệu CIFAR mô tả dữ liệu, kích thước và nhãn nhưng không nêu thiết bị hay khẩu độ chụp.", ["khẩu độ", "máy ảnh"]),
    ("B30", "test", "Phiên bản AutoIt tiếp theo dự kiến phát hành vào ngày cụ thể nào?", "Tài liệu không có lịch phát hành tương lai của AutoIt.", ["dự kiến phát hành", "lịch phát hành"]),
]


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def main() -> None:
    chunks = json.loads(CHUNKS.read_text(encoding="utf-8"))
    questions = []
    for qid, split, question, answer, evidence, filters in ANSWERABLE:
        matches = [row for row in chunks if evidence in row["text"]]
        if not matches:
            raise SystemExit(f"{qid}: evidence is not contained in any chunk")
        sources = {(row["source_id"], row["page"]) for row in matches}
        if len(sources) != 1:
            raise SystemExit(f"{qid}: evidence resolves ambiguously: {sources}")
        source_id, page = next(iter(sources))
        row = {
            "id": qid,
            "split": split,
            "answerable": True,
            "question": question,
            "expected_answer": answer,
            "gold": [{"source_id": source_id, "page": page, "evidence": evidence}],
        }
        if filters:
            if filters["collection"] != matches[0]["metadata"]["collection"]:
                raise SystemExit(f"{qid}: filter does not match source metadata")
            row["filter"] = filters
        questions.append(row)

    corpus_text = "\n".join(row["text"] for row in chunks).casefold()
    for qid, split, question, reason, absence_terms in UNANSWERABLE:
        found = [term for term in absence_terms if term.casefold() in corpus_text]
        if found:
            raise SystemExit(f"{qid}: declared absence term exists in corpus: {found}")
        questions.append({
            "id": qid,
            "split": split,
            "answerable": False,
            "question": question,
            "expected_behavior": "search_and_abstain",
            "absence_reason": reason,
            "absence_check": {"scope": "all_418_chunks", "searched_terms": absence_terms},
        })

    questions.sort(key=lambda row: int(row["id"][1:]))
    payload = {"benchmark_id": "day07-vi-computing-agent-v1", "questions": questions}
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    data = canonical_bytes(payload)
    OUTPUT.write_bytes(data)
    summary = {
        "benchmark_id": payload["benchmark_id"],
        "questions_sha256": hashlib.sha256(data).hexdigest(),
        "counts": {
            split: {
                "answerable": sum(q["split"] == split and q["answerable"] for q in questions),
                "unanswerable": sum(q["split"] == split and not q["answerable"] for q in questions),
                "total": sum(q["split"] == split for q in questions),
            }
            for split in ("dev", "test")
        },
        "filter_questions": [q["id"] for q in questions if q.get("filter")],
        "policy": "Select and tune on Dev only; freeze before the first Test run.",
    }
    FREEZE.write_bytes(canonical_bytes(summary))
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
