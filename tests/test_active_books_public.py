import json


def _write_projection(tmp_path):
    root = tmp_path / "local_books_corpus"
    root.mkdir()
    (root / "catalog.json").write_text(json.dumps({
        "corpus_id": "books-v1", "status": "active", "source_count": 2, "document_count": 3,
    }, ensure_ascii=False), encoding="utf-8")
    (root / "documents.jsonl").write_text("\n".join(json.dumps(item, ensure_ascii=False) for item in [
        {"id": "book:a:p1:c1", "content": "甲", "char_count": 10, "metadata": {"book_title": "图书甲", "page_start": 1}},
        {"id": "book:a:p2:c1", "content": "乙", "char_count": 20, "metadata": {"book_title": "图书甲", "page_start": 2}},
        {"id": "book:b:p1:c1", "content": "丙", "char_count": 30, "metadata": {"book_title": "图书乙", "page_start": 1}},
    ]) + "\n", encoding="utf-8")
    (root / "craft_metadata.json").write_text(json.dumps({
        "corpus_id": "books-v1",
        "projects": [{
            "craft_id": "craft-jtl", "project_name": "景泰蓝制作技艺",
            "category": {"value": "传统技艺", "status": "verified", "evidence": []},
            "regions": [{"value": "北京市", "status": "verified", "evidence": []}],
            "inheritors": [{"name": "钟连盛", "recognition": "国家级代表性传承人", "status": "verified", "evidence": [{"book_title": "国家级非物质文化遗产项目代表性传承人大典 第1卷", "page": 2, "document_id": "book:a:p2:c1", "excerpt": "钟连盛1978年进入北京市珐琅厂学艺。"}]}],
            "description": {"text": "景泰蓝的书中介绍", "status": "mentioned", "evidence": []},
            "sources": [{"book_title": "图书甲", "chapter_title": "传统技艺", "page": 1, "document_id": "book:a:p1:c1", "excerpt": "景泰蓝资料"}],
            "status": "verified",
        }],
    }, ensure_ascii=False), encoding="utf-8")
    return root


def test_active_books_projection_drives_public_summary_encyclopedia_and_inheritors(tmp_path):
    from src.services.active_books_public import ActiveBooksProjection

    projection = ActiveBooksProjection.load(_write_projection(tmp_path))

    assert projection.dashboard_summary() == {
        "source_books": 2, "document_count": 3, "total_characters": 60,
        "project_count": 1, "inheritor_count": 1,
    }
    assert projection.encyclopedia_entries()[0]["slug"] == "craft-jtl"
    assert projection.encyclopedia_entry("craft-jtl")["content"] == "景泰蓝的书中介绍"
    inheritor = projection.inheritors()[0]
    assert inheritor["name"] == "钟连盛"
    assert inheritor["craft_name"] == "景泰蓝制作技艺"
    assert inheritor["sources"][0]["name"] == "国家级非物质文化遗产项目代表性传承人大典 第1卷 第2页"
    assert inheritor["biography"] == "钟连盛1978年进入北京市珐琅厂学艺。"


def test_active_books_projection_keeps_the_list_summary_shorter_than_detail_content(tmp_path):
    from src.services.active_books_public import ActiveBooksProjection

    root = _write_projection(tmp_path)
    metadata = json.loads((root / "craft_metadata.json").read_text(encoding="utf-8"))
    full_text = "景泰蓝制作技艺" + "的书中介绍。" * 80
    metadata["projects"][0]["description"]["text"] = full_text
    (root / "craft_metadata.json").write_text(json.dumps(metadata, ensure_ascii=False), encoding="utf-8")

    projection = ActiveBooksProjection.load(root)

    assert projection.encyclopedia_entry("craft-jtl")["content"] == full_text
    assert projection.encyclopedia_entries()[0]["summary"] != full_text
    assert len(projection.encyclopedia_entries()[0]["summary"]) <= 180


def test_active_books_projection_does_not_publish_old_cross_book_person_links(tmp_path):
    from src.services.active_books_public import ActiveBooksProjection

    root = _write_projection(tmp_path)
    metadata = json.loads((root / "craft_metadata.json").read_text(encoding="utf-8"))
    metadata["projects"][0]["inheritors"].append({
        "name": "任天元", "recognition": "传承人", "status": "verified",
        "evidence": [{"book_title": "第二批国家级非物质文化遗产名录简介", "page": 116,
                      "document_id": "book:b:p116:c1", "excerpt": "长白山森林号子传承人任天元"}],
    })
    (root / "craft_metadata.json").write_text(json.dumps(metadata, ensure_ascii=False), encoding="utf-8")

    projection = ActiveBooksProjection.load(root)
    assert projection.dashboard_summary()["inheritor_count"] == 1
    assert [item["name"] for item in projection.inheritors()] == ["钟连盛"]
    assert projection.build_graph().get_statistics()["node_types"]["inheritor"] == 1


def test_active_books_projection_builds_graph_from_the_same_project_records(tmp_path):
    from src.services.active_books_public import ActiveBooksProjection

    graph = ActiveBooksProjection.load(_write_projection(tmp_path)).build_graph()
    stats = graph.get_statistics()

    assert stats["node_types"] == {"craft": 1, "category": 1, "region": 1, "inheritor": 1, "source": 1}
    assert stats["edge_types"] == {"related_to": 1, "originates_from": 1, "mastered_by": 1, "has_source": 1}


def test_active_books_projection_exposes_only_a_source_backed_book_image(tmp_path):
    from src.services.active_books_public import ActiveBooksProjection

    root = _write_projection(tmp_path)
    (root / "book_images.json").write_text(json.dumps({
        "corpus_id": "books-v1",
        "selection_version": 3,
        "images": {
            "craft-jtl": {
                "status": "extracted",
                "selection_version": 3,
                "book_title": "图书甲",
                "page": 1,
                "file_path": "images/craft-jtl.png",
            },
        },
    }, ensure_ascii=False), encoding="utf-8")

    image = ActiveBooksProjection.load(root).encyclopedia_entries()[0]["image"]

    assert image == {"url": "/api/local-books/images/craft-jtl", "status": "extracted"}


def test_active_books_projection_resolves_only_the_manifested_image_file(tmp_path):
    from src.services.active_books_public import ActiveBooksProjection

    root = _write_projection(tmp_path)
    image_path = root / "images" / "craft-jtl.png"
    image_path.parent.mkdir()
    image_path.write_bytes(b"png-data")
    (root / "book_images.json").write_text(json.dumps({
        "corpus_id": "books-v1",
        "selection_version": 3,
        "images": {"craft-jtl": {"status": "extracted", "selection_version": 3, "file_path": "images/craft-jtl.png"}},
    }, ensure_ascii=False), encoding="utf-8")

    projection = ActiveBooksProjection.load(root)

    assert projection.image_file("craft-jtl") == image_path
    assert projection.image_file("../craft-jtl") is None


def test_active_books_projection_hides_images_built_by_an_unvalidated_selection_rule(tmp_path):
    from src.services.active_books_public import ActiveBooksProjection

    root = _write_projection(tmp_path)
    (root / "book_images.json").write_text(json.dumps({
        "corpus_id": "books-v1",
        "images": {"craft-jtl": {"status": "extracted", "file_path": "images/craft-jtl.png"}},
    }, ensure_ascii=False), encoding="utf-8")

    image = ActiveBooksProjection.load(root).encyclopedia_entries()[0]["image"]

    assert image == {"url": None, "status": "unavailable"}


def test_active_books_projection_hides_fake_project_and_contaminated_legacy_summary(tmp_path):
    from src.services.active_books_public import ActiveBooksProjection

    root = _write_projection(tmp_path)
    metadata = json.loads((root / "craft_metadata.json").read_text(encoding="utf-8"))
    metadata["projects"][0]["description"]["text"] = "目录：景泰蓝、枣梆、其他项目。"
    metadata["projects"].append({
        "craft_id": "fake", "project_name": "申报地区或单位", "category": {"value": None},
        "regions": [], "inheritors": [], "description": {"text": "附录里的杂乱内容"}, "sources": [],
    })
    (root / "craft_metadata.json").write_text(json.dumps(metadata, ensure_ascii=False), encoding="utf-8")

    projection = ActiveBooksProjection.load(root)

    assert projection.dashboard_summary()["project_count"] == 1
    assert projection.encyclopedia_entry("fake") is None
    assert projection.encyclopedia_entry("craft-jtl")["content"] == ""


def test_active_books_projection_hides_legacy_cross_book_joined_description(tmp_path):
    from src.services.active_books_public import ActiveBooksProjection

    root = _write_projection(tmp_path)
    metadata = json.loads((root / "craft_metadata.json").read_text(encoding="utf-8"))
    metadata["projects"][0]["description"] = {
        "text": "景泰蓝旧书中的介绍。其他书中偶然提及景泰蓝的段落。",
        "evidence": [
            {"book_title": "第一批国家级非物质文化遗产名录图典", "page": 10},
            {"book_title": "通识读本", "page": 22},
        ],
    }
    (root / "craft_metadata.json").write_text(json.dumps(metadata, ensure_ascii=False), encoding="utf-8")

    assert ActiveBooksProjection.load(root).encyclopedia_entry("craft-jtl")["content"] == ""


def test_crafts_endpoint_uses_the_active_books_projection(monkeypatch):
    import asyncio
    from types import SimpleNamespace
    import api

    monkeypatch.setattr(api, "active_books_projection", SimpleNamespace(
        encyclopedia_entries=lambda: [
            {"slug": "book-1", "name": "苗族古歌"},
            {"slug": "book-2", "name": "布洛陀"},
        ]
    ))

    assert asyncio.run(api.list_crafts()) == {
        "crafts": [{"id": "book-1", "name": "苗族古歌"}, {"id": "book-2", "name": "布洛陀"}]
    }
