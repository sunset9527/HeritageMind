import json


def _save_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


def test_review_candidate_merges_identical_official_names_and_uses_only_own_book_page(tmp_path):
    from src.services.reviewed_books_projection import build_review_candidate

    root = tmp_path / "corpus"
    root.mkdir()
    _save_json(root / "catalog.json", {"corpus_id": "books-test", "status": "active", "source_count": 3})
    documents = [
        {"id": "first:p40:c1", "content": "湘剧\n申报地区或单位：湖南省\n湘剧流传于湖南。",
         "metadata": {"book_title": "第一批国家级非物质文化遗产名录图典 上", "page_start": 40}},
        {"id": "second:p51:c1", "content": "519\nI-32\n八达岭长城传说\n申报地区或单位：北京市\n八达岭长城传说流传于北京。",
         "metadata": {"book_title": "第二批国家级非物质文化遗产名录简介", "page_start": 51}},
        {"id": "other:p2:c1", "content": "目录：湘剧、八达岭长城传说和其他故事。",
         "metadata": {"book_title": "非遗通识读本", "page_start": 2}},
    ]
    (root / "documents.jsonl").write_text(
        "".join(json.dumps(item, ensure_ascii=False) + "\n" for item in documents), encoding="utf-8"
    )
    first_path = tmp_path / "first.json"
    _save_json(first_path, {"batch": "first", "source_url": "https://example.org/first", "items": [
        {"sequence": 1, "code": "Ⅳ—1", "name": "湘剧"}
    ]})
    later_path = tmp_path / "later.json"
    _save_json(later_path, {"batches": [
        {"batch": "second", "source_url": "https://example.org/second", "items": [
            {"sequence": 519, "code": "Ⅰ—32", "name": "八达岭长城传说"},
            {"sequence": 728, "code": "Ⅳ—127", "name": "湘剧"},
        ]},
    ]})

    candidate = build_review_candidate(root, first_path=first_path, later_path=later_path)

    assert len(candidate["projects"]) == 2
    xiangju = next(item for item in candidate["projects"] if item["project_name"] == "湘剧")
    assert [item["sequence"] for item in xiangju["catalogue_entries"]] == [1, 728]
    assert xiangju["description"]["text"] == "湘剧流传于湖南。"
    badaling = next(item for item in candidate["projects"] if item["project_name"] == "八达岭长城传说")
    assert badaling["description"]["text"] == "八达岭长城传说流传于北京。"
    assert all("目录" not in item["description"]["text"] for item in candidate["projects"])


def test_review_candidate_marks_missing_book_profile_instead_of_fabricating_description(tmp_path):
    from src.services.reviewed_books_projection import build_review_candidate

    root = tmp_path / "corpus"
    root.mkdir()
    _save_json(root / "catalog.json", {"corpus_id": "books-test", "status": "active"})
    (root / "documents.jsonl").write_text("", encoding="utf-8")
    first_path = tmp_path / "first.json"
    _save_json(first_path, {"batch": "first", "source_url": "https://example.org/first", "items": []})
    later_path = tmp_path / "later.json"
    _save_json(later_path, {"batches": [{"batch": "second", "source_url": "https://example.org/second", "items": [
        {"sequence": 600, "code": "Ⅱ—101", "name": "搬运号子"}
    ]}]})

    candidate = build_review_candidate(root, first_path=first_path, later_path=later_path)

    assert candidate["projects"][0]["project_name"] == "搬运号子"
    assert candidate["projects"][0]["description"]["text"] == ""
    assert candidate["projects"][0]["status"] == "pending_review"


def test_review_candidate_links_people_only_when_dedicated_volume_names_the_project(tmp_path):
    from src.services.reviewed_books_projection import build_review_candidate

    root = tmp_path / "corpus"
    root.mkdir()
    _save_json(root / "catalog.json", {"corpus_id": "books-test", "status": "active"})
    rows = [
        {"id": "person:p15", "content": "男，苗族，1935年生。第一批国家级非物质文化遗产项目苗族古歌代表性传承人。\n1 I-1\n王安江\n王安江长期演唱苗族古歌。", "metadata": {"book_title": "国家级非物质文化遗产项目代表性传承人大典 第1卷", "page_start": 15}},
        {"id": "other:p12", "content": "任天元是长白山森林号子代表性传承人。", "metadata": {"book_title": "第二批国家级非物质文化遗产名录简介", "page_start": 12}},
    ]
    (root / "documents.jsonl").write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
    first_path = tmp_path / "first.json"
    _save_json(first_path, {"batch": "first", "source_url": "https://example.org/first", "items": [
        {"sequence": 1, "code": "Ⅰ—1", "name": "苗族古歌"}
    ]})
    later_path = tmp_path / "later.json"
    _save_json(later_path, {"batches": []})

    candidate = build_review_candidate(root, first_path=first_path, later_path=later_path)

    assert [person["name"] for person in candidate["people"]] == ["王安江"]
    assert [person["name"] for person in candidate["projects"][0]["inheritors"]] == ["王安江"]
    public_person = candidate["projects"][0]["inheritors"][0]
    assert "王安江长期演唱" in public_person["evidence"][0]["excerpt"]
    assert "任天元" not in json.dumps(candidate, ensure_ascii=False)


def test_review_candidate_links_unique_project_variant_to_base_name(tmp_path):
    from src.services.reviewed_books_projection import _match_project

    projects = {"剪纸": {"project_name": "剪纸"}, "风筝制作技艺": {"project_name": "风筝制作技艺"}}

    assert _match_project(projects, "剪纸（蔚县剪纸）")["project_name"] == "剪纸"
    assert _match_project(projects, "风筝制作技艺（南通板鹞风筝）")["project_name"] == "风筝制作技艺"
    assert _match_project(projects, "剪纸安塞剪纸")["project_name"] == "剪纸"
    assert _match_project(projects, "不在名录里的项目") is None


def test_review_candidate_adds_shandong_profile_and_merges_identical_name(tmp_path):
    from src.services.reviewed_books_projection import build_review_candidate

    root = tmp_path / "corpus"
    root.mkdir()
    _save_json(root / "catalog.json", {"corpus_id": "books-test", "status": "active"})
    title = "山东省省级非物质文化遗产名录图典 第1卷"
    rows = [
        {"id": "sd:toc", "content": "目录\n梁祝传说\n孟姜女传说", "metadata": {"book_title": title, "page_start": 10}},
        {"id": "sd:22", "content": "梁祝传说\n(济宁市)\n梁祝传说在当地流传。", "metadata": {"book_title": title, "page_start": 22}},
        {"id": "sd:25", "content": "孟姜女传说\n(淄博市)\n孟姜女传说在当地流传。", "metadata": {"book_title": title, "page_start": 25}},
    ]
    (root / "documents.jsonl").write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
    first_path = tmp_path / "first.json"
    _save_json(first_path, {"batch": "first", "source_url": "https://example.org/first", "items": [
        {"sequence": 1, "code": "Ⅰ—1", "name": "梁祝传说"}
    ]})
    later_path = tmp_path / "later.json"
    _save_json(later_path, {"batches": []})

    candidate = build_review_candidate(root, first_path=first_path, later_path=later_path)

    assert candidate["project_count"] == 2
    assert candidate["provincial_profile_count"] == 2
    liangzhu = next(project for project in candidate["projects"] if project["project_name"] == "梁祝传说")
    assert len(liangzhu["sources"]) == 1
    assert next(project for project in candidate["projects"] if project["project_name"] == "孟姜女传说")["catalogue_entries"] == []


def test_description_source_rejects_a_different_project_on_the_same_page():
    from src.services.reviewed_books_projection import _description_source

    pages = {("第三批国家级非物质文化遗产名录图典 上", 80): [{
        "id": "wrong", "content": "维吾尔族刺绣\n申报地区或单位：新疆\n维吾尔族刺绣是当地的传统技艺。",
        "metadata": {"book_title": "第三批国家级非物质文化遗产名录图典 上", "page_start": 80},
    }]}

    description, evidence = _description_source(
        pages, batch="third", project_name="满族刺绣（岫岩满族民间刺绣）", page_hint=80,
        ocr_name="维吾尔族刺绣",
    )

    assert (description, evidence) == ("", None)


def test_profile_page_evidence_keeps_a_traceable_source_when_ocr_body_is_empty():
    from src.services.reviewed_books_projection import _source_page_evidence

    title = "第二批国家级非物质文化遗产名录简介"
    pages = {(title, 51): [{
        "id": "b2:p51", "content": "519\nI-32\n八达岭长城传说\n申报地区或单位：北京市",
        "metadata": {"book_title": title, "page_start": 51},
    }]}

    evidence = _source_page_evidence(pages, batch="second", page_hint=51)

    assert evidence == {
        "book_title": title,
        "chapter_title": "",
        "page": 51,
        "document_id": "b2:p51",
        "document_ids": ["b2:p51"],
        "pages": [51],
        "excerpt": "519 I-32 八达岭长城传说 申报地区或单位：北京市",
        "extraction": "official_sequence_page",
    }


def test_description_source_uses_sequence_verified_page_when_ocr_loses_the_title():
    from src.services.reviewed_books_projection import _description_source

    title = "\u7b2c\u4e09\u6279\u56fd\u5bb6\u7ea7\u975e\u7269\u8d28\u6587\u5316\u9057\u4ea7\u540d\u5f55\u56fe\u5178 \u4e0a"
    project = "\u85cf\u65cf\u77ff\u690d\u7269\u989c\u6599\u5236\u4f5c\u6280\u827a"
    prose = "\u5728\u897f\u85cf\uff0c\u5236\u4f5c\u548c\u5e94\u7528\u77ff\u690d\u7269\u7ed8\u753b\u989c\u6599\u5df2\u6709\u4e24\u5343\u591a\u5e74\u7684\u60a0\u4e45\u5386\u53f2\u3002"
    pages = {(title, 358): [{
        "id": "b3:p358", "content": (
            "337\n" + project + "\n1179\n\u7533\u62a5\u5730\u533a\u6216\u5355\u4f4d\uff1a\u897f\u85cf\u81ea\u6cbb\u533a\u62c9\u8428\u5e02\n"
            "VII-199\n" + prose + "\u81ea\u53e4\u4ee5\u6765\uff0c\u85cf\u65cf\u7ed8\u753b\u6240\u7528\u989c\u6599\u90fd\u662f\u4ece\u96ea\u57df\u9ad8\u539f\u672c\u5730\u7684\u77ff\u690d\u7269\u4e2d\u63d0\u53d6\u3002"
        ),
        "metadata": {"book_title": title, "page_start": 358},
    }]}

    description, evidence = _description_source(
        pages, batch="third", project_name=project, page_hint=358,
        ocr_name=prose,
        sequence=1179,
    )

    assert description.startswith(prose)
    assert evidence["extraction"] == "sequence_verified_page_fallback"


def test_description_source_keeps_the_full_book_body_and_its_continuation_page():
    from src.services.reviewed_books_projection import _description_source

    title = "第一批国家级非物质文化遗产名录图典 上"
    pages = {
        (title, 40): [{
            "id": "b1:p40", "content": (
                "苗族古歌\n申报地区或单位：贵州省\n第一批国家级非物质文化遗产名录图典\n民间文\n"
                "苗族古歌流传于苗族聚居区。它记录了民族的历史与生活，具"
            ),
            "metadata": {"book_title": title, "page_start": 40},
        }],
        (title, 41): [{
            "id": "b1:p41", "content": (
                "有史学与民族学价值。\n布洛陀\n申报地区或单位：广西壮族自治区\n"
                "布洛陀是壮族创世神话。"
            ),
            "metadata": {"book_title": title, "page_start": 41},
        }],
    }

    description, evidence = _description_source(
        pages, batch="first", project_name="苗族古歌", page_hint=40, ocr_name="苗族古歌", sequence=1,
    )

    assert description == "苗族古歌流传于苗族聚居区。它记录了民族的历史与生活，具有史学与民族学价值。"
    assert evidence["pages"] == [40, 41]
    assert "布洛陀" not in description


def test_unique_first_batch_code_resolves_small_ocr_name_error():
    from src.services.reviewed_books_projection import _first_batch_project_by_code

    projects = {"岫岩玉雕": {"project_name": "岫岩玉雕", "catalogue_entries": [
        {"batch": "first", "code": "Ⅶ—29"}
    ]}}

    assert _first_batch_project_by_code(projects, "Ⅶ—29", "岩玉雕")["project_name"] == "岫岩玉雕"
    assert _first_batch_project_by_code(projects, "Ⅶ—29", "完全不相关") is None
