"""The interactive graph must match the application's dark visual theme."""

from src.graph.heritage_graph import HeritageKnowledgeGraph
from src.graph import visualizer as visualizer_module


class FakeNetwork:
    instances = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.templateEnv = type("TemplateEnv", (), {"filters": {}})()
        self.nodes = []
        self.edges = []
        self.options = None
        self.__class__.instances.append(self)

    def barnes_hut(self, **_kwargs):
        pass

    def add_node(self, **node):
        self.nodes.append(node)

    def add_edge(self, **edge):
        self.edges.append(edge)

    def set_options(self, options):
        self.options = options

    def generate_html(self):
        return "<html><body><div id=\"graph\"></div></body></html>"


def test_interactive_graph_uses_dark_canvas_and_legend(monkeypatch):
    monkeypatch.setattr(visualizer_module, "Network", FakeNetwork)
    FakeNetwork.instances.clear()
    graph = HeritageKnowledgeGraph()
    graph.add_node("craft", "craft", name="景泰蓝")

    html = visualizer_module.HeritageGraphVisualizer(graph).render_interactive()

    assert FakeNetwork.instances[0].kwargs["bgcolor"] == "#1C2016"
    assert FakeNetwork.instances[0].kwargs["font_color"] == "#F4F0E7"
    assert "background:#293025" in html
    assert "color:#F4F0E7" in html
    assert FakeNetwork.instances[0].nodes[0]["color"]["background"] == "#D4B77E"
    assert FakeNetwork.instances[0].nodes[0]["color"]["border"] == "#F4F0E7"
