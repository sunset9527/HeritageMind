# -*- coding: utf-8 -*-
"""HeritageMind 检索评测 v2：100 条 query（40 简单 + 60 难题），分类型统计 Hit@5"""
import sys, io, glob, os, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, r"E:/python/LLM/IntangibleCulturalHeritage_MultiAgent")
import numpy as np
from langchain_huggingface import HuggingFaceEmbeddings
from src.retrieval.bm25_retriever import BM25Retriever
from src.retrieval.fusion import reciprocal_rank_fusion

DATA_DIR = r"E:/python/LLM/IntangibleCulturalHeritage_MultiAgent/data/crafts"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
TOP_K = 5

def chunk_text(text, doc_id, size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    chunks = []
    start = 0
    idx = 0
    while start < len(text):
        seg = text[start:start+size]
        if not seg:
            break
        chunks.append({"id": f"{doc_id}_c{idx}", "content": seg, "metadata": {"craft_id": doc_id}})
        idx += 1
        if start + size >= len(text):
            break
        start += size - overlap
    return chunks

t0 = time.time()
documents = []
files = sorted(glob.glob(DATA_DIR + "/*.txt"))
for f in files:
    craft = os.path.basename(f)[:-4]
    with io.open(f, "r", encoding="utf-8") as fp:
        text = fp.read()
    documents.extend(chunk_text(text, craft))
print(f"[{time.time()-t0:.0f}s] 加载 {len(files)} 个文档，切分 {len(documents)} 个 chunk")

# ============ 100 条评测集 ============
# (query, expected, anchor, type)  type: simple=直问含技艺名 / hard=难题不含技艺名
Q = [
    # ---- 简单题 40 条（直问，含技艺名） ----
    ("东阳木雕有哪些主要雕刻技法？", "东阳木雕", "镂空雕", "simple"),
    ("东阳木雕的代表传承人是谁？", "东阳木雕", "陆光正", "simple"),
    ("东阳木雕常用于哪些建筑部位？", "东阳木雕", "牛腿", "simple"),
    ("东阳木雕的历史渊源是怎样的？", "东阳木雕", "唐代", "simple"),
    ("京剧的四大行当是什么？", "京剧", "行当", "simple"),
    ("京剧有哪些代表流派？", "京剧", "流派", "simple"),
    ("京剧形成于什么时期？", "京剧", "徽班", "simple"),
    ("京剧的艺术特征有哪些？", "京剧", "艺术特征", "simple"),
    ("剪纸有哪些地域流派？", "剪纸", "流派", "simple"),
    ("剪纸的代表作品和传承人有哪些？", "剪纸", "传承人", "simple"),
    ("剪纸有什么文化内涵？", "剪纸", "文化内涵", "simple"),
    ("南京云锦的核心品种有哪些？", "南京云锦", "品种", "simple"),
    ("南京云锦的制作工艺有什么特点？", "南京云锦", "工艺", "simple"),
    ("南京云锦的代表传承人是谁？", "南京云锦", "传承人", "simple"),
    ("唐三彩有哪些器物类型？", "唐三彩", "器物", "simple"),
    ("唐三彩的工艺技术是怎样的？", "唐三彩", "工艺", "simple"),
    ("壮锦有哪些代表图案？", "壮锦", "图案", "simple"),
    ("宜兴紫砂的主要材料是什么？", "宜兴紫砂", "材料", "simple"),
    ("景德镇瓷器有哪些主要品种？", "景德镇瓷器", "品种", "simple"),
    ("景德镇瓷器的制作工艺？", "景德镇瓷器", "工艺", "simple"),
    ("景泰蓝的制作工艺是怎样的？", "景泰蓝", "工艺", "simple"),
    ("景泰蓝的主要材料有哪些？", "景泰蓝", "材料", "simple"),
    ("木版年画的主要产地在哪？", "木版年画", "产地", "simple"),
    ("木版年画的经典题材有什么？", "木版年画", "题材", "simple"),
    ("汝瓷的釉色有什么特点？", "汝瓷", "釉色", "simple"),
    ("泥人张的艺术特色是什么？", "泥人张", "艺术特色", "simple"),
    ("泥人张的制作工艺是怎样的？", "泥人张", "工艺", "simple"),
    ("漆器有哪些主要流派？", "漆器", "流派", "simple"),
    ("玉雕的工艺技法有哪些？", "玉雕", "技法", "simple"),
    ("玉雕主要产地在哪？", "玉雕", "产地", "simple"),
    ("皮影戏有哪些主要流派？", "皮影戏", "流派", "simple"),
    ("皮影戏的表演形式有什么特点？", "皮影戏", "表演形式", "simple"),
    ("竹编有哪些代表作品？", "竹编", "作品", "simple"),
    ("缂丝的核心技艺是什么？", "缂丝", "缂丝", "simple"),
    ("芜湖铁画的主要材料是什么？", "芜湖铁画", "材料", "simple"),
    ("苏绣有哪些艺术特色？", "苏绣", "艺术特色", "simple"),
    ("苗族蜡染有哪些代表纹样？", "苗族蜡染", "纹样", "simple"),
    ("蜀锦的主要材料包括什么？", "蜀锦", "材料", "simple"),
    ("钧瓷的窑变工艺有什么特点？", "钧瓷", "窑变", "simple"),
    ("龙泉青瓷的釉色有什么特点？", "龙泉青瓷", "釉色", "simple"),
    # ---- 难题 60 条（不含技艺名） ----
    ("哪种木雕以平面浮雕见长？", "东阳木雕", "平面浮雕", "hard"),
    ("陆光正是哪个非遗项目的国家级传承人？", "东阳木雕", "陆光正", "hard"),
    ("浙江三雕指的是哪三种雕刻？", "东阳木雕", "浙江三雕", "hard"),
    ("哪种木雕艺人曾进京修缮皇宫？", "东阳木雕", "修缮皇宫", "hard"),
    ("四大行当是生旦净丑的戏曲剧种是哪个？", "京剧", "行当", "hard"),
    ("梅兰芳是哪个剧种的代表人物？", "京剧", "梅兰芳", "hard"),
    ("徽班进京孕育了什么剧种？", "京剧", "徽班", "hard"),
    ("哪个剧种被称为国粹？", "京剧", "国粹", "hard"),
    ("以窗花著称的民间剪纸艺术属于哪个流派？", "剪纸", "窗花", "hard"),
    ("蔚县剪纸属于哪种民间艺术？", "剪纸", "蔚县", "hard"),
    ("妆花是哪个织锦的核心品种？", "南京云锦", "妆花", "hard"),
    ("产自南京的传统织锦是什么？", "南京云锦", "南京", "hard"),
    ("以黄绿白三色釉著称的唐代陶器是什么？", "唐三彩", "釉", "hard"),
    ("唐三彩中常见的动物造型是什么？", "唐三彩", "骆驼", "hard"),
    ("广西壮族传统织锦是什么？", "壮锦", "壮族", "hard"),
    ("壮锦上常见的吉祥图案有什么？", "壮锦", "图案", "hard"),
    ("紫砂壶的主要产地是哪里？", "宜兴紫砂", "宜兴", "hard"),
    ("宜兴紫砂采用什么泥料制作？", "宜兴紫砂", "泥", "hard"),
    ("青花瓷的主要产地是哪里？", "景德镇瓷器", "景德镇", "hard"),
    ("四大名瓷中哪种以青花装饰著称？", "景德镇瓷器", "青花", "hard"),
    ("掐丝珐琅的另一个名称是什么？", "景泰蓝", "掐丝", "hard"),
    ("景泰蓝以什么为胎体？", "景泰蓝", "铜", "hard"),
    ("天津杨柳青以什么民间艺术闻名？", "木版年画", "杨柳青", "hard"),
    ("苏州桃花坞年画属于哪种艺术形式？", "木版年画", "桃花坞", "hard"),
    ("以天青釉闻名于世的宋代名瓷是哪种？", "汝瓷", "天青", "hard"),
    ("雨过天晴云破处描述的是哪种瓷器釉色？", "汝瓷", "天青", "hard"),
    ("天津泥人张以什么技艺闻名？", "泥人张", "泥人", "hard"),
    ("泥人张的创始人是谁？", "泥人张", "张明山", "hard"),
    ("福州脱胎漆器属于哪类非遗技艺？", "漆器", "脱胎", "hard"),
    ("扬州漆器以什么工艺著称？", "漆器", "扬州", "hard"),
    ("和田玉主要产自哪个地区？", "玉雕", "和田", "hard"),
    ("哪种玉石以青白色调闻名？", "玉雕", "玉雕", "hard"),
    ("唐山皮影是哪个省份的代表性影戏？", "皮影戏", "唐山", "hard"),
    ("以皮影演出传统故事的民间艺术是什么？", "皮影戏", "影", "hard"),
    ("四川青神以什么竹编工艺品闻名？", "竹编", "青神", "hard"),
    ("竹编工艺品的主要材料是什么？", "竹编", "竹", "hard"),
    ("通经断纬是哪种丝织技艺的核心？", "缂丝", "通经断纬", "hard"),
    ("苏州缂丝属于什么传统艺术？", "缂丝", "苏州", "hard"),
    ("以铁为墨、以砧为纸的艺术形式是什么？", "芜湖铁画", "砧", "hard"),
    ("芜湖铁画以什么材料制作？", "芜湖铁画", "铁", "hard"),
    ("双面绣是哪个绣种的代表技艺？", "苏绣", "双面绣", "hard"),
    ("四大名绣中产自江苏的是哪个？", "苏绣", "江苏", "hard"),
    ("苏绣以什么针法著称？", "苏绣", "针法", "hard"),
    ("蝴蝶妈妈是哪个民族的传统纹样？", "壮锦", "壮锦", "hard"),
    ("贵州苗族有什么传统印染技艺？", "苗族蜡染", "贵州", "hard"),
    ("蜡染以什么工具蘸蜡绘制纹样？", "苗族蜡染", "蜡刀", "hard"),
    ("产自成都的传统织锦是什么？", "蜀锦", "成都", "hard"),
    ("蜀锦采用什么纤维织造？", "蜀锦", "蚕丝", "hard"),
    ("窑变是哪种瓷器最独特的工艺现象？", "钧瓷", "窑变", "hard"),
    ("钧瓷产于今天的哪个城市？", "钧瓷", "禹州", "hard"),
    ("粉青和梅子青是什么瓷器的釉色？", "龙泉青瓷", "粉青", "hard"),
    ("龙泉青瓷产自哪个省份？", "龙泉青瓷", "浙江", "hard"),
    ("哪种瓷以厚釉著称？", "钧瓷", "钧瓷", "hard"),
    ("木版年画中常见的门神题材属于什么？", "木版年画", "门神", "hard"),
    ("京剧中的武生属于哪个行当？", "京剧", "武生", "hard"),
    ("哪种瓷器以开片纹为特色？", "汝瓷", "开片", "hard"),
    ("哪种丝织品被称为织中之圣？", "缂丝", "织中之圣", "hard"),
    ("金线织造的代表品种是什么？", "南京云锦", "金", "hard"),
    ("景泰蓝的釉料以什么色为主？", "景泰蓝", "蓝", "hard"),
    ("哪种木雕工艺品可多角度观赏？", "东阳木雕", "圆雕", "hard"),
]

# ---- 锚词验证 ----
valid = []
invalid = []
for q, exp, anchor, typ in Q:
    exp_path = os.path.join(DATA_DIR, exp + ".txt")
    with io.open(exp_path, "r", encoding="utf-8") as fp:
        txt = fp.read()
    if anchor in txt:
        valid.append((q, exp, anchor, typ))
    else:
        invalid.append((q, exp, anchor, typ))
print(f"有效 query: {len(valid)} / {len(Q)}")
if invalid:
    print("被剔除的 query:")
    for q, exp, anchor, typ in invalid:
        print(f"  [剔除] ({typ}) 期望={exp} 锚={anchor} | {q}")

queries = valid
simple = [x for x in queries if x[3] == "simple"]
hard = [x for x in queries if x[3] == "hard"]
print(f"简单题: {len(simple)} | 难题: {len(hard)}")

# ---- 检索 ----
bm25 = BM25Retriever()
bm25.build_index(documents)
emb = HuggingFaceEmbeddings(model_name=r"E:/huggingface/model", model_kwargs={"device": "cpu"},
                            encode_kwargs={"normalize_embeddings": True, "batch_size": 32})
docs_vectors = emb.embed_documents([d["content"] for d in documents])
doc_mat = np.array(docs_vectors)
print(f"[{time.time()-t0:.0f}s] 文档向量化完成: {doc_mat.shape}")

def vector_retrieve(query, top_k=TOP_K):
    qv = np.array(emb.embed_query(query))
    qn = np.linalg.norm(qv) + 1e-9
    sims = (doc_mat @ qv) / (np.linalg.norm(doc_mat, axis=1) * qn + 1e-9)
    idxs = np.argsort(-sims)[:top_k]
    return [{"doc_id": documents[i]["id"], "content": documents[i]["content"], "score": float(sims[i]), "metadata": documents[i]["metadata"]} for i in idxs]

def hit_at5(results, expected):
    return any(r["metadata"].get("craft_id") == expected for r in results[:5])

stats = {"BM25": [0, 0], "Vector": [0, 0], "Hybrid(RRF)": [0, 0]}  # [命中, 总数]
by_type = {"simple": {"BM25": 0, "Vector": 0, "Hybrid(RRF)": 0},
           "hard": {"BM25": 0, "Vector": 0, "Hybrid(RRF)": 0}}
detail = []
for q, exp, anchor, typ in queries:
    r_bm25 = bm25.retrieve(q, top_k=TOP_K)
    r_vec = vector_retrieve(q, TOP_K)
    r_fused = reciprocal_rank_fusion([r_bm25, r_vec])[:TOP_K]
    hb = hit_at5(r_bm25, exp); hv = hit_at5(r_vec, exp); hf = hit_at5(r_fused, exp)
    for k, h in (("BM25", hb), ("Vector", hv), ("Hybrid(RRF)", hf)):
        stats[k][0] += h
        stats[k][1] += 1
        by_type[typ][k] += h
    detail.append((typ, q, exp, hb, hv, hf,
                   [x["metadata"].get("craft_id") for x in r_bm25[:3]],
                   [x["metadata"].get("craft_id") for x in r_vec[:3]],
                   [x["metadata"].get("craft_id") for x in r_fused[:3]]))

print()
print("=" * 50)
print("总结果:")
print(f'{"方法":<14}{"Hit@5":>7}{"准确率":>10}')
for k, (hit, total) in stats.items():
    print(f"{k:<14}{hit}/{total}{hit/total*100:>9.1f}%")
print()
print("按题型:")
for typ in ("simple", "hard"):
    n = sum(1 for x in queries if x[3] == typ)
    print(f"  [{typ}] 共{n}条")
    for k in ("BM25", "Vector", "Hybrid(RRF)"):
        h = by_type[typ][k]
        print(f"    {k:<14}{h}/{n}{h/n*100:>8.1f}%")
print()
print("=" * 50)
print("逐条明细（类型 | 命中:BM25/Vector/RRF | 前三来源）:")
for typ, q, exp, hb, hv, hf, b3, v3, f3 in detail:
    print(f"[{typ}] {hb}/{hv}/{hf} 期望={exp:<6} Q: {q[:26]}")
    print(f"    BM25前三: {b3}")
    print(f"    Vec前三 : {v3}")
    print(f"    RRF前三 : {f3}")
print()
print(f"评测完成，总耗时 {time.time()-t0:.0f}s")
