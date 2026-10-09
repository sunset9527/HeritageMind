"""Offline behavior tests for IHChina project-detail candidate parsing."""


def test_parse_project_detail_extracts_fields_and_only_same_host_image_candidates():
    from src.services.ihchina_project_parser import parse_ihchina_project_detail

    html = """
    <main class="project-detail">
      <h1>宜兴紫砂陶制作技艺</h1>
      <p>项目编号：Ⅷ-114</p>
      <p>类别：传统技艺</p>
      <p>申报地区或单位：江苏省宜兴市</p>
      <p>保护单位：宜兴市非物质文化遗产保护中心</p>
      <section class="introduction">宜兴紫砂陶制作技艺以紫砂泥为原料，经制坯、装饰、烧成等工序完成。</section>
      <img src="/Uploads/Picture/2018/11/01/yixing.jpg" alt="紫砂壶成品" />
      <img src="/Public/static/themes/image/gaj.png" alt="页脚图标" />
      <img src="https://cdn.example.com/unrelated.jpg" alt="第三方图片" />
    </main>
    """

    detail = parse_ihchina_project_detail(
        html,
        "https://www.ihchina.cn/project_details/14261.html",
    )

    assert detail.craft_name == "宜兴紫砂陶制作技艺"
    assert detail.project_code == "Ⅷ-114"
    assert detail.category == "传统技艺"
    assert detail.declaring_region_or_unit == "江苏省宜兴市"
    assert detail.protection_unit == "宜兴市非物质文化遗产保护中心"
    assert detail.introduction_excerpt == "宜兴紫砂陶制作技艺以紫砂泥为原料，经制坯、装饰、烧成等工序完成。"
    assert [(image.image_url, image.alt, image.status) for image in detail.image_candidates] == [
        ("https://www.ihchina.cn/Uploads/Picture/2018/11/01/yixing.jpg", "紫砂壶成品", "pending_review"),
    ]


def test_parse_project_detail_limits_introduction_and_keeps_absent_fields_empty():
    from src.services.ihchina_project_parser import parse_ihchina_project_detail

    detail = parse_ihchina_project_detail(
        "<h1>剪纸</h1><div class='introduction'>" + "甲" * 530 + "</div>",
        "https://www.ihchina.cn/project_details/1.html",
    )

    assert detail.craft_name == "剪纸"
    assert detail.project_code is None
    assert detail.category is None
    assert len(detail.introduction_excerpt) == 500
    assert detail.image_candidates == ()


def test_parse_project_detail_uses_h1_instead_of_navigation_text_as_project_name():
    from src.services.ihchina_project_parser import parse_ihchina_project_detail

    detail = parse_ihchina_project_detail(
        "<nav>首页  国家级代表性项目名录</nav><h1>剪纸</h1><p>类别：传统美术</p>",
        "https://www.ihchina.cn/project_details/1.html",
    )

    assert detail.craft_name == "剪纸"


def test_parse_project_detail_separates_project_sequence_extracts_body_introduction_and_filters_static_images():
    from src.services.ihchina_project_parser import parse_ihchina_project_detail

    detail = parse_ihchina_project_detail(
        """
        <h1>傣族慢轮制陶技艺</h1>
        <p>项目序号：355 | 项目编号：Ⅷ-5</p>
        <p>类别：传统技艺</p>
        <p>申报地区或单位：云南省西双版纳傣族自治州 | 保护单位：西双版纳傣族自治州文化馆</p>
        <p>傣族制陶历史悠久，多个村寨保留了传统制陶技艺。</p>
        <p>慢轮手工制作是这项技艺的突出特色。</p>
        <img src="/Uploads/Picture/2018/11/01/project.jpg" alt="制陶技艺" />
        <img src="/Public/static/themes/image/temp/w.gif" alt="占位图" />
        <img src="/Uploads/Picture/2019/09/22/season.png" alt="秋分" />
        <h2>相关传承人</h2>
        <p>玉勐</p>
        """,
        "https://www.ihchina.cn/project_details/14265.html",
    )

    assert detail.project_sequence == "355"
    assert detail.project_code == "Ⅷ-5"
    assert detail.protection_unit == "西双版纳傣族自治州文化馆"
    assert detail.introduction_excerpt == "傣族制陶历史悠久，多个村寨保留了传统制陶技艺。慢轮手工制作是这项技艺的突出特色。"
    assert [(image.image_url, image.alt) for image in detail.image_candidates] == [
        ("https://www.ihchina.cn/Uploads/Picture/2018/11/01/project.jpg", "制陶技艺"),
    ]
