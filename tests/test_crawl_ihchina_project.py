"""Offline orchestration tests for the single-project IHChina crawler."""

from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def test_cli_help_runs_when_invoked_as_documented_script():
    result = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "crawl_ihchina_project.py"), "--help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    assert result.returncode == 0
    assert "--acknowledge-ihchina-terms" in result.stdout


def test_collect_project_candidate_does_not_fetch_detail_without_unique_exact_search_match():
    from tools.crawl_ihchina_project import collect_project_candidate

    fetched_urls: list[str] = []

    def fetch_html(url: str) -> str:
        fetched_urls.append(url)
        return '<a href="/project_details/1.html">宜兴紫砂</a>'

    record = collect_project_candidate(
        "宜兴紫砂陶制作技艺",
        fetch_html,
        max_candidates=3,
        pause=lambda _: None,
    )

    assert record["status"] == "ambiguous"
    assert record["project_detail_candidates"] == [
        {"url": "https://www.ihchina.cn/project_details/1.html", "title": "宜兴紫砂"},
    ]
    assert len(fetched_urls) == 1
    assert "/search_result/keyword/" in fetched_urls[0]


def test_collect_project_candidate_emits_review_only_record_for_unique_exact_match():
    from tools.crawl_ihchina_project import collect_project_candidate

    def fetch_html(url: str) -> str:
        if "/search_result/keyword/" in url:
            return '<a href="/project_details/1.html">宜兴紫砂陶制作技艺</a>'
        return """
        <h1>宜兴紫砂陶制作技艺 - 中国非物质文化遗产网·中国非物质文化遗产数字博物馆</h1>
        <p>项目编号：Ⅷ-114</p>
        <p>类别：传统技艺</p>
        <section class="introduction">以紫砂泥为原料的传统手工技艺。</section>
        <img src="/Uploads/Picture/2018/11/01/yixing.jpg" alt="紫砂壶" />
        """

    record = collect_project_candidate(
        "宜兴紫砂陶制作技艺",
        fetch_html,
        max_candidates=3,
        pause=lambda _: None,
    )

    assert record["status"] == "needs_review"
    assert record["publication_status"] == "candidate"
    assert record["matched_craft_name"] == "宜兴紫砂陶制作技艺"
    assert record["detail_title_matches_query"] is True
    assert record["project_code"] == "Ⅷ-114"
    assert record["introduction_excerpt"] == "以紫砂泥为原料的传统手工技艺。"
    assert record["image_candidates"] == [
        {
            "image_url": "https://www.ihchina.cn/Uploads/Picture/2018/11/01/yixing.jpg",
            "alt": "紫砂壶",
            "context": "详情页图片候选",
            "source_page_url": "https://www.ihchina.cn/project_details/1.html",
            "status": "pending_review",
        },
    ]


def test_collect_project_candidate_keeps_detail_when_page_title_is_not_parseable():
    from tools.crawl_ihchina_project import collect_project_candidate

    def fetch_html(url: str) -> str:
        if "/search_result/keyword/" in url:
            return '<a href="/project_details/14265.html">傣族慢轮制陶技艺</a>'
        return """
        <nav>首页 国家级代表性项目名录</nav>
        <h2>傣族慢轮制陶技艺</h2>
        <p>项目编号：Ⅷ-82</p>
        <p>类别：传统技艺</p>
        <section class="introduction">傣族慢轮制陶技艺流传于云南省。</section>
        <img src="/Uploads/Picture/2018/11/01/dai.jpg" alt="制陶场景" />
        """

    record = collect_project_candidate(
        "傣族慢轮制陶技艺",
        fetch_html,
        max_candidates=3,
        pause=lambda _: None,
    )

    assert record["status"] == "needs_review"
    assert record["matched_craft_name"] == "傣族慢轮制陶技艺"
    assert record["detail_page_title"] == "首页 国家级代表性项目名录"
    assert record["detail_title_matches_query"] is False
    assert record["project_code"] == "Ⅷ-82"
    assert record["image_candidates"][0]["image_url"] == "https://www.ihchina.cn/Uploads/Picture/2018/11/01/dai.jpg"
