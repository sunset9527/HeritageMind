"""Official-detail candidates are discovered offline from saved search HTML."""


def test_extract_ihchina_project_candidates_deduplicates_and_keeps_project_pages_only():
    from src.services.official_source_discovery import extract_ihchina_project_candidates

    html = """
    <a href="/project_details/19981.html">蚕丝织造技艺（杭州织锦技艺）</a>
    <a href="/project_details/19981.html">查看更多</a>
    <a href="/news/123.html">无关新闻</a>
    <a href="/project_details/14471.html"><span>蚕丝织造技艺（杭州织锦技艺）</span></a>
    """

    candidates = extract_ihchina_project_candidates(html)

    assert [(candidate.url, candidate.title) for candidate in candidates] == [
        ("https://www.ihchina.cn/project_details/19981.html", "蚕丝织造技艺（杭州织锦技艺）"),
        ("https://www.ihchina.cn/project_details/14471.html", "蚕丝织造技艺（杭州织锦技艺）"),
    ]
