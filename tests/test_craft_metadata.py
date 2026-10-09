import json
from pathlib import Path
import subprocess
import sys

import pytest


def _write_active_corpus(tmp_path, documents, *, status="active", corpus_id="books-v1"):
    corpus_path = tmp_path / "local_books_corpus"
    corpus_path.mkdir()
    (corpus_path / "catalog.json").write_text(
        json.dumps({"corpus_id": corpus_id, "status": status, "source_count": 1}, ensure_ascii=False),
        encoding="utf-8",
    )
    (corpus_path / "documents.jsonl").write_text(
        "".join(json.dumps(document, ensure_ascii=False) + "\n" for document in documents),
        encoding="utf-8",
    )
    return corpus_path


def _document(page, text, *, book_title="国家级非物质文化遗产名录图典"):
    return {
        "id": f"book:example:p{page}:c1",
        "content": text,
        "metadata": {
            "book_title": book_title,
            "chapter_title": "传统技艺",
            "page_start": page,
            "page_end": page,
        },
    }


def test_build_craft_metadata_groups_evidence_and_keeps_uncertain_fields_honest(tmp_path):
    from src.services.craft_metadata import build_craft_metadata

    corpus_path = _write_active_corpus(tmp_path, [
        _document(12, "传统技艺类：景泰蓝制作技艺。景泰蓝以铜胎、掐丝和点蓝工艺闻名。"),
        _document(13, "景泰蓝制作技艺国家级代表性传承人钟连盛，长期从事景泰蓝创作。", book_title="国家级非物质文化遗产项目代表性传承人大典 第1卷"),
        _document(14, "张三参观了景泰蓝制作技艺展览。"),
    ])

    result = build_craft_metadata(corpus_path)

    assert result["corpus_id"] == "books-v1"
    assert result["project_count"] == 1
    project = result["projects"][0]
    assert project["project_name"] == "景泰蓝制作技艺"
    assert project["category"]["value"] == "传统技艺"
    assert project["category"]["status"] == "verified"
    assert project["inheritors"] == [{
        "name": "钟连盛", "recognition": "国家级代表性传承人", "status": "verified",
        "evidence": project["inheritors"][0]["evidence"],
    }]
    assert project["inheritors"][0]["evidence"][0]["page"] == 13
    assert all(inheritor["name"] != "张三" for inheritor in project["inheritors"])
    assert project["regions"] == []
    assert project["sources"][0]["book_title"] == "国家级非物质文化遗产名录图典"
    assert (corpus_path / "craft_metadata.json").is_file()


def test_build_craft_metadata_rejects_non_active_corpus(tmp_path):
    from src.services.craft_metadata import CraftMetadataError, build_craft_metadata

    corpus_path = _write_active_corpus(tmp_path, [_document(1, "传统技艺类：景泰蓝制作技艺。")], status="staged")

    with pytest.raises(CraftMetadataError, match="active"):
        build_craft_metadata(corpus_path)


def test_build_craft_metadata_reads_catalogue_entries_with_category_and_region(tmp_path):
    from src.services.craft_metadata import build_craft_metadata

    corpus_path = _write_active_corpus(tmp_path, [
        _document(21, "传统手工技艺（共计46项）\nVIII-1\n景泰蓝制作技艺北京市\nVIII-2\n龙泉青瓷烧制技艺浙江省龙泉市"),
    ])

    result = build_craft_metadata(corpus_path)

    assert [item["project_name"] for item in result["projects"]] == ["景泰蓝制作技艺", "龙泉青瓷烧制技艺"]
    assert all(item["category"]["value"] == "传统技艺" for item in result["projects"])
    assert result["projects"][0]["regions"][0]["value"] == "北京市"
    assert result["projects"][1]["sources"][0]["page"] == 21


def test_build_craft_metadata_does_not_treat_a_prose_category_reference_as_a_project(tmp_path):
    from src.services.craft_metadata import build_craft_metadata

    corpus_path = _write_active_corpus(tmp_path, [
        _document(8, "研究者把这段材料归为民间文学：这是一个流传已久的传说。"),
    ])

    assert build_craft_metadata(corpus_path)["projects"] == []


def test_build_craft_metadata_uses_general_books_only_as_evidence_for_known_projects(tmp_path):
    from src.services.craft_metadata import build_craft_metadata

    corpus_path = _write_active_corpus(tmp_path, [
        _document(1, "传统技艺类：景泰蓝制作技艺。", book_title="第一批国家级非物质文化遗产名录图典"),
        _document(2, "传统技艺类：虚构制作技艺。", book_title="非遗通识读本"),
    ])

    result = build_craft_metadata(corpus_path)

    assert [item["project_name"] for item in result["projects"]] == ["景泰蓝制作技艺"]
    assert len(result["projects"][0]["sources"]) == 1


def test_build_craft_metadata_rejects_catalogue_rows_contaminated_by_serial_numbers(tmp_path):
    from src.services.craft_metadata import build_craft_metadata

    corpus_path = _write_active_corpus(tmp_path, [
        _document(3, "传统手工技艺（共计46项）\nVIII-1\n景泰蓝制作技艺123钟连盛北京市", book_title="国家级非物质文化遗产名录图典"),
    ])

    assert build_craft_metadata(corpus_path)["projects"] == []


def test_build_craft_metadata_only_reads_multi_item_catalogue_pages(tmp_path):
    from src.services.craft_metadata import build_craft_metadata

    corpus_path = _write_active_corpus(tmp_path, [
        _document(4, "传统手工技艺（共计46项）\nVIII-1\n景泰蓝制作技艺北京市", book_title="国家级非物质文化遗产名录图典"),
    ])

    assert build_craft_metadata(corpus_path)["projects"] == []


def test_build_craft_metadata_does_not_apply_national_catalogue_parser_to_provincial_books(tmp_path):
    from src.services.craft_metadata import build_craft_metadata

    corpus_path = _write_active_corpus(tmp_path, [
        _document(4, "传统手工技艺（共计46项）\nVIII-1\n虚构制作技艺北京市\nVIII-2\n虚构烧制技艺天津市", book_title="山东省省级非物质文化遗产名录图典"),
    ])

    assert build_craft_metadata(corpus_path)["projects"] == []


def test_craft_metadata_command_writes_projection_for_active_corpus(tmp_path):
    from tools.build_craft_metadata import main

    corpus_path = _write_active_corpus(tmp_path, [
        _document(1, "传统技艺类：景泰蓝制作技艺。"),
    ])

    assert main([str(corpus_path)]) == 0
    assert (corpus_path / "craft_metadata.json").is_file()


def test_craft_metadata_command_runs_as_a_file_from_any_working_directory(tmp_path):
    corpus_path = _write_active_corpus(tmp_path, [
        _document(1, "传统技艺类：景泰蓝制作技艺。"),
    ])
    script = Path(__file__).resolve().parents[1] / "tools" / "build_craft_metadata.py"

    completed = subprocess.run(
        [sys.executable, str(script), str(corpus_path)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert (corpus_path / "craft_metadata.json").is_file()


def test_build_craft_metadata_attaches_general_book_evidence_to_a_known_project(tmp_path):
    from src.services.craft_metadata import build_craft_metadata

    corpus_path = _write_active_corpus(tmp_path, [
        _document(1, "民间文学（共计2项）\nI-1\n布洛陀广西壮族自治区\nI-2\n白蛇传传说浙江省", book_title="第一批国家级非物质文化遗产名录图典"),
        _document(2, "布洛陀在壮族民间文化中具有重要意义。", book_title="非遗通识读本"),
    ])

    result = build_craft_metadata(corpus_path)
    buluotuo = next(item for item in result["projects"] if item["project_name"] == "布洛陀")

    assert {source["book_title"] for source in buluotuo["sources"]} == {
        "第一批国家级非物质文化遗产名录图典", "非遗通识读本",
    }


def test_build_craft_metadata_attaches_explicit_inheritor_from_a_general_book_to_one_known_project(tmp_path):
    from src.services.craft_metadata import build_craft_metadata

    corpus_path = _write_active_corpus(tmp_path, [
        _document(1, "民间文学（共计2项）\nI-1\n布洛陀广西壮族自治区\nI-2\n白蛇传传说浙江省", book_title="第一批国家级非物质文化遗产名录图典"),
        _document(2, "布洛陀国家级代表性传承人张三，长期从事相关传承工作。", book_title="国家级非物质文化遗产项目代表性传承人大典 第1卷"),
    ])

    result = build_craft_metadata(corpus_path)
    buluotuo = next(item for item in result["projects"] if item["project_name"] == "布洛陀")

    assert buluotuo["inheritors"][0]["name"] == "张三"
    assert buluotuo["inheritors"][0]["evidence"][0]["book_title"] == "国家级非物质文化遗产项目代表性传承人大典 第1卷"


def test_build_craft_metadata_ignores_person_mentions_outside_the_inheritor_volume(tmp_path):
    from src.services.craft_metadata import build_craft_metadata

    corpus_path = _write_active_corpus(tmp_path, [
        _document(1, "民间文学（共计2项）\nI-1\n布洛陀广西壮族自治区\nI-2\n白蛇传传说浙江省"),
        _document(2, "布洛陀国家级代表性传承人张三，长期从事相关传承工作。", book_title="非遗通识读本"),
        _document(3, "布洛陀国家级代表性传承人李四，长期从事相关传承工作。", book_title="国家级非物质文化遗产项目代表性传承人大典 第1卷"),
    ])

    result = build_craft_metadata(corpus_path)
    buluotuo = next(item for item in result["projects"] if item["project_name"] == "布洛陀")
    assert [person["name"] for person in buluotuo["inheritors"]] == ["李四"]


def test_build_craft_metadata_never_creates_column_header_as_a_project(tmp_path):
    from src.services.craft_metadata import build_craft_metadata

    corpus_path = _write_active_corpus(tmp_path, [
        _document(1, "民俗（共计2项）\nX-1\n申报地区或单位：山东省菏泽市\nX-2\n枣梆山东省菏泽市", book_title="第二批国家级非物质文化遗产名录简介"),
    ])

    result = build_craft_metadata(corpus_path)
    assert "申报地区或单位" not in [item["project_name"] for item in result["projects"]]


def test_build_craft_metadata_does_not_use_the_catalogue_as_the_encyclopedia_description(tmp_path):
    from src.services.craft_metadata import build_craft_metadata

    corpus_path = _write_active_corpus(tmp_path, [
        _document(1, "民间文学（共计2项）\nI-1\n布洛陀广西壮族自治区\nI-2\n白蛇传传说浙江省"),
        _document(2, "布洛陀\n申报地区或单位：广西壮族自治区田阳县\n布洛陀是壮族的长篇诗体创世神话。", book_title="第一批国家级非物质文化遗产名录图典"),
    ])

    result = build_craft_metadata(corpus_path)
    buluotuo = next(item for item in result["projects"] if item["project_name"] == "布洛陀")
    assert buluotuo["description"]["text"] == "布洛陀是壮族的长篇诗体创世神话。"


def test_build_craft_metadata_does_not_treat_inheritor_status_text_as_a_person_name(tmp_path):
    from src.services.craft_metadata import build_craft_metadata

    corpus_path = _write_active_corpus(tmp_path, [
        _document(1, "民间文学（共计2项）\nI-1\n布洛陀广西壮族自治区\nI-2\n白蛇传传说浙江省", book_title="第一批国家级非物质文化遗产名录图典"),
        _document(2, "布洛陀的国家级代表性传承人日益减少。", book_title="传承人大典"),
    ])

    result = build_craft_metadata(corpus_path)
    buluotuo = next(item for item in result["projects"] if item["project_name"] == "布洛陀")

    assert buluotuo["inheritors"] == []


def test_build_craft_metadata_rejects_surname_shaped_status_or_work_descriptions(tmp_path):
    from src.services.craft_metadata import build_craft_metadata

    corpus_path = _write_active_corpus(tmp_path, [
        _document(1, "民间文学（共计2项）\nI-1\n布洛陀广西壮族自治区\nI-2\n白蛇传传说浙江省", book_title="第一批国家级非物质文化遗产名录图典"),
        _document(2, "布洛陀国家级代表性传承人严重萎缩，相关传承人杨氏画作颇多。", book_title="传承人大典"),
    ])

    result = build_craft_metadata(corpus_path)
    buluotuo = next(item for item in result["projects"] if item["project_name"] == "布洛陀")

    assert buluotuo["inheritors"] == []


def test_build_craft_metadata_rejects_truncated_or_category_only_catalogue_names(tmp_path):
    from src.services.craft_metadata import build_craft_metadata

    corpus_path = _write_active_corpus(tmp_path, [
        _document(1, "传统音乐（共计2项）\nII-1\n族民歌云南省\nII-2\n传统技艺浙江省", book_title="第一批国家级非物质文化遗产名录图典"),
    ])

    assert build_craft_metadata(corpus_path)["projects"] == []


def test_build_craft_metadata_rejects_a_category_name_captured_as_an_explicit_project(tmp_path):
    from src.services.craft_metadata import build_craft_metadata

    corpus_path = _write_active_corpus(tmp_path, [
        _document(1, "传统美术：传统技艺。", book_title="第二批国家级非物质文化遗产名录简介"),
    ])

    assert build_craft_metadata(corpus_path)["projects"] == []


def test_profile_description_skips_ocr_caption_before_substantive_sentence():
    from src.services.craft_metadata import _profile_description

    text = (
        "布洛陀\n申报地区或单位：\n布洛陀经博环社\n市海陀散北山\n"
        "广西壮族自治区田阳县\n2布洛陀\n"
        "布洛陀是壮族先民口碑文学中的创世神话人物，在当地长期口头传承。"
    )

    assert _profile_description(text, "布洛陀", "第一批国家级非物质文化遗产名录图典") == (
        "布洛陀是壮族先民口碑文学中的创世神话人物，在当地长期口头传承。"
    )


def test_profile_description_skips_form_fields_and_keeps_clean_sentence():
    from src.services.craft_metadata import _profile_description

    text = "皮影戏\n申报地区或单位：陕西省\n皮影戏·华县皮影戏申报地区或单位：陕西省项目保护单位：某机构皮影戏形成于清代。"

    assert _profile_description(text, "皮影戏", "第三批国家级非物质文化遗产名录图典 上") == "皮影戏形成于清代。"


def test_profile_description_keeps_two_book_sentences_for_context():
    from src.services.craft_metadata import _profile_description

    text = (
        "湘剧\n申报地区或单位：湖南省\n"
        "湘剧是湖南省的地方戏曲，流传于湘南。"
        "它融合了昆腔和高腔，形成鲜明的地方声腔。"
    )

    assert _profile_description(text, "湘剧", "第一批国家级非物质文化遗产名录图典") == (
        "湘剧是湖南省的地方戏曲，流传于湘南。它融合了昆腔和高腔，形成鲜明的地方声腔。"
    )
