import json


def test_inheritors_come_only_from_dedicated_volume_and_keep_page_evidence(tmp_path):
    from src.services.inheritor_volume import extract_inheritor_candidates

    rows = [
        {"id": "book:p15", "content": "民间文学\n男，苗族，1935年生。第一批国家级非物质文化遗产项目苗族古歌代表性传承人。\n1 I-1\n王安江\n王安江从小学习苗族古歌，并长期传授。\n王安江（左三）教孩子唱歌（摄影）", "metadata": {"book_title": "国家级非物质文化遗产项目代表性传承人大典 第1卷", "page_start": 15}},
        {"id": "other:p1", "content": "任天元是长白山森林号子传承人。", "metadata": {"book_title": "第二批国家级非物质文化遗产名录简介", "page_start": 1}},
    ]
    (tmp_path / "documents.jsonl").write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in rows), encoding="utf-8")

    result = extract_inheritor_candidates(tmp_path)

    assert len(result["people"]) == 1
    person = result["people"][0]
    assert (person["sequence"], person["name"], person["project_name"]) == (1, "王安江", "苗族古歌")
    assert person["book_project_code"] == "Ⅰ—1"
    assert "王安江从小学习苗族古歌" in person["biography"]["text"]
    assert "摄影" not in person["biography"]["text"]
    assert person["evidence"]["book_title"].startswith("国家级非物质文化遗产项目代表性传承人大典")
    assert person["evidence"]["page"] == 15
    assert result["missing_numbers"] == list(range(2, 227))


def test_dotted_heading_is_a_person_profile(tmp_path):
    from src.services.inheritor_volume import extract_inheritor_candidates

    row = {"id": "book:p77", "content": "65\n传统美术\n58.VII-9\n冯炳棠\n男，汉族，1936年生。第一批国家级非物质文化遗产项目佛山木版年画代表性传承人。冯炳棠长期制作木版年画。", "metadata": {"book_title": "国家级非物质文化遗产项目代表性传承人大典 第1卷", "page_start": 77}}
    (tmp_path / "documents.jsonl").write_text(json.dumps(row, ensure_ascii=False) + "\n", encoding="utf-8")

    result = extract_inheritor_candidates(tmp_path)

    assert result["people"][0]["sequence"] == 58
    assert result["people"][0]["name"] == "冯炳棠"
