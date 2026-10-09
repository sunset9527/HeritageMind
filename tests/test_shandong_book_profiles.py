import json


def test_extracts_only_shandong_project_pages_and_keeps_evidence(tmp_path):
    from src.services.shandong_book_profiles import extract_shandong_profiles

    title = "山东省省级非物质文化遗产名录图典 第1卷"
    rows = [
        {"id": "toc:10", "content": "目录\n梁祝传说\n济宁市\n[2]", "metadata": {"book_title": title, "page_start": 10}},
        {"id": "page:22", "content": "梁祝传说\n(济宁市)\n梁祝传说在济宁民间长期流传。", "metadata": {"book_title": title, "page_start": 22}},
        {"id": "page:519", "content": "山东省第一批省级非物质文化遗产名录\n(共157项)\n目录", "metadata": {"book_title": title, "page_start": 519}},
        {"id": "other:p5", "content": "任天元\n(山东省)\n故事", "metadata": {"book_title": "中国的非物质文化遗产", "page_start": 5}},
    ]
    (tmp_path / "documents.jsonl").write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")

    profiles = extract_shandong_profiles(tmp_path)

    assert len(profiles) == 1
    assert profiles[0]["project_name"] == "梁祝传说"
    assert profiles[0]["region"] == "济宁市"
    assert profiles[0]["evidence"]["page"] == 22
    assert profiles[0]["status"] == "toc_confirmed"


def test_known_ocr_heading_is_corrected_from_book_contents(tmp_path):
    from src.services.shandong_book_profiles import extract_shandong_profiles

    title = "山东省省级非物质文化遗产名录图典 第1卷"
    rows = [
        {"id": "toc", "content": "目录\n闵子骞传说\n[29]", "metadata": {"book_title": title, "page_start": 10}},
        {"id": "page", "content": "闵子寒传说\n(济宁市)\n正文。", "metadata": {"book_title": title, "page_start": 49}},
    ]
    (tmp_path / "documents.jsonl").write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")

    profiles = extract_shandong_profiles(tmp_path)

    assert profiles[0]["project_name"] == "闵子骞传说"
    assert profiles[0]["ocr_name"] == "闵子寒传说"
    assert profiles[0]["status"] == "book_title_corrected"
