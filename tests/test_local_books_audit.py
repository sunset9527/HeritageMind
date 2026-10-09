"""Regression checks for numbered project and inheritor book coverage."""

import json
from pathlib import Path


def _document(book, page, text):
    return {"id": f"book:{book}:p{page}:c1", "content": text,
            "metadata": {"book_title": book, "page_start": page}}


def test_audit_counts_only_main_catalogue_profile_numbers_and_dedicated_inheritors(tmp_path):
    from src.services.local_books_audit import audit_local_books

    root = tmp_path / "books"
    root.mkdir()
    documents = [
        _document("第二批国家级非物质文化遗产名录简介", 3, "目录\n519\nI-32\n错误目录名"),
        _document("第二批国家级非物质文化遗产名录简介", 51,
                  "519\nI-32\n八达岭长城传说\n申报地区或单位：北京市\n八达岭长城传说流传于北京。"),
        _document("第二批国家级非物质文化遗产名录简介", 52,
                  "521\nI-34\n杨家将传说\n（穆桂英传说、杨家将说唱）\n杨家将传说展现了英雄家族。\n杨家将传说·穆桂英传说\n申报地区或单位：北京市"),
        _document("第三批国家级非物质文化遗产名录图典 上", 26,
                  "1029\n天坛传说\n申报地区或单位：北京市\nI-85\n天坛传说流传于北京。"),
        _document("非遗通识读本", 15, "1 I-1\n张三传承布洛陀"),
        _document("国家级非物质文化遗产项目代表性传承人大典 第1卷", 15,
                  "1 I-1\n王安江\n男，苗族。第一批国家级非物质文化遗产项目苗族古歌代表性传承人。"),
    ]
    (root / "documents.jsonl").write_text(
        "".join(json.dumps(item, ensure_ascii=False) + "\n" for item in documents), encoding="utf-8"
    )

    report = audit_local_books(root)

    assert report["batches"]["second"]["found_count"] == 2
    assert report["batches"]["second"]["profiles"]["519"]["name"] == "八达岭长城传说"
    assert report["batches"]["second"]["profiles"]["521"]["name"] == "杨家将传说"
    assert report["batches"]["third"]["found_count"] == 1
    assert report["batches"]["third"]["profiles"]["1029"]["name"] == "天坛传说"
    assert report["inheritor_volume"]["found_count"] == 1
    assert report["inheritor_volume"]["profile_numbers"]["1"] == 15


def test_audit_keeps_unreadable_numbers_missing_instead_of_inventing_records(tmp_path):
    from src.services.local_books_audit import audit_local_books

    root = tmp_path / "books"
    root.mkdir()
    (root / "documents.jsonl").write_text(json.dumps(_document(
        "第二批国家级非物质文化遗产名录简介", 51,
        "519\nI-32\n八达岭长城传说\n申报地区或单位：北京市",
    ), ensure_ascii=False) + "\n", encoding="utf-8")

    report = audit_local_books(root)
    assert report["batches"]["second"]["expected_count"] == 510
    assert 520 in report["batches"]["second"]["missing_numbers"]
    assert 519 not in report["batches"]["second"]["missing_numbers"]


def test_audit_accepts_numbered_umbrella_entry_without_region_label(tmp_path):
    from src.services.local_books_audit import audit_local_books

    root = tmp_path / "books"
    root.mkdir()
    rows = [
        _document("第二批国家级非物质文化遗产名录简介", 114,
                  "上一项目正文。\n598\n3II-99\n码头号子\n（上海港码头号子）\n码头号子主要流传于码头。"),
        _document("第二批国家级非物质文化遗产名录简介", 115,
                  "正文里提到\n599\n森林号子\n但缺少项目编号，不能把它当成标题。"),
    ]
    (root / "documents.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8"
    )

    report = audit_local_books(root)["batches"]["second"]

    assert report["profiles"]["598"]["name"] == "码头号子"
    assert 599 in report["missing_numbers"]


def test_audit_accepts_sequence_and_code_when_ocr_merges_them(tmp_path):
    from src.services.local_books_audit import audit_local_books

    root = tmp_path / "books"
    root.mkdir()
    rows = [
        _document("第二批国家级非物质文化遗产名录简介", 117,
                  "600II-101\n搬运号子\n申报地区或单位：重庆市\n搬运号子是在劳动中形成的民歌。"),
        _document("第二批国家级非物质文化遗产名录简介", 390,
                  "8371\nVI-61\n葫芦雕刻\n申报地区或单位：山东省\n葫芦雕刻工艺流传于山东。"),
    ]
    (root / "documents.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8"
    )

    report = audit_local_books(root)["batches"]["second"]

    assert report["profiles"]["600"]["name"] == "搬运号子"
    assert report["profiles"]["837"]["name"] == "葫芦雕刻"


def test_official_comparison_flags_unreadable_pages_and_ocr_name_errors(tmp_path):
    from src.services.local_books_audit import audit_local_books, compare_official_catalogue

    root = tmp_path / "books"
    root.mkdir()
    (root / "documents.jsonl").write_text("".join(json.dumps(item, ensure_ascii=False) + "\n" for item in [
        _document("第二批国家级非物质文化遗产名录简介", 51,
                  "519\nI-32\n八达岭长城传说\n申报地区或单位：北京市"),
        _document("第二批国家级非物质文化遗产名录简介", 273,
                  "721\nIV-120\n枣郴\n申报地区或单位：山东省菏泽市"),
    ]), encoding="utf-8")
    official_path = tmp_path / "official.json"
    official_path.write_text(json.dumps({"batches": [{"batch": "second", "items": [
        {"sequence": 519, "name": "八达岭长城传说", "code": "Ⅰ—32"},
        {"sequence": 520, "name": "永定河传说", "code": "Ⅰ—33"},
        {"sequence": 721, "name": "枣梆", "code": "Ⅳ—120"},
    ]}]}, ensure_ascii=False), encoding="utf-8")

    comparison = compare_official_catalogue(audit_local_books(root), official_path)

    assert comparison["second"]["covered_count"] == 2
    assert comparison["second"]["missing_from_book"] == [520]
    assert comparison["second"]["name_disagreements"] == [
        {"sequence": 721, "official_name": "枣梆", "ocr_name": "枣郴", "page": 273}
    ]


def test_checked_official_catalogue_has_complete_main_batch_sequences():
    source = Path(__file__).resolve().parents[1] / "data" / "knowledge_sources" / "official_national_batches_2_3.json"
    batches = json.loads(source.read_text(encoding="utf-8"))["batches"]

    assert [len(batch["items"]) for batch in batches] == [510, 191]
    assert sorted(item["sequence"] for item in batches[0]["items"]) == list(range(519, 1029))
    assert sorted(item["sequence"] for item in batches[1]["items"]) == list(range(1029, 1220))
