# -*- coding: utf-8 -*-
"""
HeritageMind 检索优化评测：⑤技艺名精确匹配置顶 前后对比

评测集：与 eval_retrieval_hm100.py 相同的 94 条 query（40 直问含技艺名 + 54 难题不含技艺名，
锚词验证后剔除无效 query）。

指标：
- Hit@1：结果第 1 条是否来自期望技艺（置顶优化直接作用于 rank1，用 Hit@1 衡量）
- Hit@5：回归保护（置顶不应降低召回）

对比：
- baseline：BM25 / Vector / RRF 融合后直接取 top
- boosted ：RRF 融合结果经过 apply_craft_name_boost（生产模块 src/retrieval/craft_name_boost.py）
            后再取 top

预期：
- 直问类（simple，40 条全含技艺名）：Hit@1 提升至接近 100%（目标技艺精确置顶）
- 难题类（hard，54 条不含技艺名）：boost 零干预，Hit@1/Hit@5 与 baseline 完全一致（零回归）

运行：
    python -X utf8 eval_craft_boost.py
"""
import sys, io, glob, os, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, r"E:/python/LLM/IntangibleCulturalHeritage_MultiAgent")
import numpy as np
from langchain_huggingface import HuggingFaceEmbeddings
from src.retrieval.bm25_retriever import BM25Retriever
from src.retrieval.fusion import reciprocal_rank_fusion
from src.retrieval.craft_name_boost import apply_craft_name_boost, is_craft_query

DATA_DIR = r"E:/python/LLM/IntangibleCulturalHeritage_MultiAgent/data/crafts"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
TOP_K = 5
FUSION_POOL = 20  # 融合池：先取 20 条再置顶再截断，保证目标技艺文档在池内

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

# ============ 评测集（与 eval_retrieval_hm100.py 相同） ============
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
    ("哪种玉石以青白色调闻名？", "玉雕", "青白", "hard"),
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
    ("蝴蝶妈妈是哪个民族的传统纹样？", "苗族蜡染", "蝴蝶", "hard"),
    ("贵州苗族有什么传统印染技艺？", "苗族蜡染", "贵州", "hard"),
    ("蜡染以什么工具蘸蜡绘制纹样？", "苗族蜡染", "蜡刀", "hard"),
    ("产自成都的传统织锦是什么？", "蜀锦", "成都", "hard"),
    ("蜀锦采用什么纤维织造？", "蜀锦", "蚕丝", "hard"),
    ("窑变是哪种瓷器最独特的工艺现象？", "钧瓷", "窑变", "hard"),
    ("钧瓷产于今天的哪个城市？", "钧瓷", "禹州", "hard"),
    ("粉青和梅子青是什么瓷器的釉色？", "龙泉青瓷", "粉青", "hard"),
    ("龙泉青瓷产自哪个省份？", "龙泉青瓷", "浙江", "hard"),
    ("哪种青瓷以厚釉著称？", "龙泉青瓷", "厚釉", "hard"),
    ("木版年画中常见的门神题材属于什么？", "木版年画", "门神", "hard"),
    ("京剧中的武生属于哪个行当？", "京剧", "武生", "hard"),
    ("哪种瓷器以开片纹为特色？", "汝瓷", "开片", "hard"),
    ("哪种丝织品被称为织中之圣？", "缂丝", "织中之圣", "hard"),
    ("南京云锦中金线织造的代表品种是什么？", "南京云锦", "金", "hard"),
    ("景泰蓝的釉料以什么色为主？", "景泰蓝", "蓝", "hard"),
    ("哪种木雕工艺品可多角度观赏？", "东阳木雕", "圆雕", "hard"),
]

# ---- 锚词验证（与 eval_retrieval_hm100.py 相同规则） ----
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
print(f"简单题(含技艺名): {len(simple)} | 难题(不含技艺名): {len(hard)}")

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

def craft_of(results):
    return [r["metadata"].get("craft_id") for r in results]

def hit_at(results, expected, k):
    return any(c == expected for c in craft_of(results)[:k])

# 统计：{方法: {"h1": [命中, 总数], "h5": [...]}}
# 六路对比：单路 / 单路+置顶 / RRF / RRF+置顶
def new_stats():
    return {k: {"h1": [0, 0], "h5": [0, 0]} for k in (
        "BM25", "BM25+置顶", "Vector", "Vector+置顶", "RRF", "RRF+置顶")}

stats = new_stats()
by_type = {"simple": new_stats(), "hard": new_stats()}
# 按"是否含技艺名"动态分组（置顶适用性）：评测集 hard 类里实际有 22 条含技艺名，
# 用 is_craft_query 精确区分"置顶适用集"与"零回归集"
by_craftq = {"含技艺名": new_stats(), "不含技艺名": new_stats()}
boost_used = {"simple": 0, "hard": 0}   # query 命中技艺名的条数
boost_hits = {"simple": 0, "hard": 0}   # 置顶实际改变 rank1 的条数

detail = []
for q, exp, anchor, typ in queries:
    r_bm25 = bm25.retrieve(q, top_k=FUSION_POOL)
    r_vec = vector_retrieve(q, FUSION_POOL)
    r_fused = reciprocal_rank_fusion([r_bm25, r_vec])[:FUSION_POOL]
    # ⑤ 技艺名精确匹配置顶（生产模块）—— 对每一路结果后处理
    r_bm25_b, matched = apply_craft_name_boost(list(r_bm25), q)
    r_vec_b, _ = apply_craft_name_boost(list(r_vec), q)
    r_fused_b, _ = apply_craft_name_boost(list(r_fused), q)

    if matched:
        boost_used[typ] += 1
        if craft_of(r_fused_b)[:1] != craft_of(r_fused)[:1]:
            boost_hits[typ] += 1

    rows = {"BM25": r_bm25[:TOP_K], "BM25+置顶": r_bm25_b[:TOP_K],
            "Vector": r_vec[:TOP_K], "Vector+置顶": r_vec_b[:TOP_K],
            "RRF": r_fused[:TOP_K], "RRF+置顶": r_fused_b[:TOP_K]}
    cq = "含技艺名" if is_craft_query(q) else "不含技艺名"
    for k, res in rows.items():
        for bucket in (stats, by_type[typ], by_craftq[cq]):
            bucket[k]["h1"][0] += hit_at(res, exp, 1)
            bucket[k]["h5"][0] += hit_at(res, exp, 5)
            bucket[k]["h1"][1] += 1
            bucket[k]["h5"][1] += 1
    detail.append((typ, cq, q, exp, craft_of(r_fused)[:1], craft_of(r_fused_b)[:1],
                   hit_at(r_fused, exp, 1), hit_at(r_fused_b, exp, 1)))

# ---- 输出 ----
def pct(h, n):
    return f"{h}/{n} ({h/n*100:.1f}%)"

print()
print("=" * 64)
print("总结果（94 条评测集）")
print(f'{"方法":<12}{"Hit@1":>16}{"Hit@5":>16}')
for k in ("BM25", "BM25+置顶", "Vector", "Vector+置顶", "RRF", "RRF+置顶"):
    h1, n1 = stats[k]["h1"]; h5, n5 = stats[k]["h5"]
    print(f"{k:<12}{pct(h1, n1):>16}{pct(h5, n5):>16}")

print()
print("按题型（simple=直问40条 / hard=难题54条，注意 hard 中 22 条实际含技艺名）:")
for typ in ("simple", "hard"):
    n = by_type[typ]["RRF"]["h1"][1]
    print(f"  [{typ}] 共{n}条")
    for k in ("BM25", "BM25+置顶", "RRF", "RRF+置顶"):
        h1, _ = by_type[typ][k]["h1"]; h5, _ = by_type[typ][k]["h5"]
        print(f"    {k:<10} Hit@1: {pct(h1, n)}   Hit@5: {pct(h5, n)}")

print()
print("按是否含技艺名（置顶适用性，is_craft_query 动态标注）:")
for cq in ("含技艺名", "不含技艺名"):
    n = by_craftq[cq]["RRF"]["h1"][1]
    print(f"  [{cq}] 共{n}条")
    for k in ("BM25", "BM25+置顶", "RRF", "RRF+置顶"):
        h1, _ = by_craftq[cq][k]["h1"]; h5, _ = by_craftq[cq][k]["h5"]
        print(f"    {k:<10} Hit@1: {pct(h1, n)}   Hit@5: {pct(h5, n)}")

print()
print(f"置顶干预统计：simple 类 {boost_used['simple']}/{len(simple)} 条命中技艺名，"
      f"{boost_hits['simple']} 条实际改变了 rank1")
print(f"               hard 类 {boost_used['hard']}/{len(hard)} 条命中技艺名（评测集标注与"
      f"实际含技艺名不一致，见上），{boost_hits['hard']} 条改变排序")

# ---- 零回归断言 ----
# 不含技艺名的 query：置顶零干预，各路 +置顶 前后 Hit@1/Hit@5 必须完全一致
for k in ("BM25", "Vector", "RRF"):
    b = by_craftq["不含技艺名"][k]
    a = by_craftq["不含技艺名"][k + "+置顶"]
    assert b["h1"] == a["h1"], f"{k}+置顶 在'不含技艺名'集合 Hit@1 出现回归！"
    assert b["h5"] == a["h5"], f"{k}+置顶 在'不含技艺名'集合 Hit@5 出现回归！"
# 含技艺名的 query：置顶后 Hit@1 不得低于置顶前
for k in ("BM25", "Vector", "RRF"):
    b = by_craftq["含技艺名"][k]["h1"][0]
    a = by_craftq["含技艺名"][k + "+置顶"]["h1"][0]
    assert a >= b, f"{k}+置顶 在'含技艺名'集合 Hit@1 下降！"

print()
print("置顶前 → 置顶后（Hit@1）:")
s_before, _ = by_type["simple"]["RRF"]["h1"]
s_after, _ = by_type["simple"]["RRF+置顶"]["h1"]
print(f"  直问类(simple)      : {pct(s_before, len(simple))} → {pct(s_after, len(simple))}")
b1, _ = by_craftq["含技艺名"]["RRF"]["h1"]
a1, _ = by_craftq["含技艺名"]["RRF+置顶"]["h1"]
n1 = by_craftq["含技艺名"]["RRF"]["h1"][1]
print(f"  含技艺名全集(RRF)   : {pct(b1, n1)} → {pct(a1, n1)}")
bm25_b, _ = by_craftq["含技艺名"]["BM25"]["h1"]
bm25_a, _ = by_craftq["含技艺名"]["BM25+置顶"]["h1"]
print(f"  含技艺名全集(BM25)  : {pct(bm25_b, n1)} → {pct(bm25_a, n1)}")
print(f"  总 94 条            : {pct(stats['RRF']['h1'][0], len(queries))} → {pct(stats['RRF+置顶']['h1'][0], len(queries))}")

# 逐条失败明细（置顶后仍 Hit@1 失败的）
print()
print("置顶后 Hit@1 失败明细（type | 含技艺名? | 期望 | RRF首名→置顶首名 | query）:")
fail = [d for d in detail if not d[7]]
for typ, cq, q, exp, f1, b1, hb, ha in fail:
    print(f"  [{typ}/{cq}] 期望={exp:<6} 前:{f1}→后:{b1} | {q[:30]}")
if not fail:
    print("  无（置顶后 94 条 Hit@1 全中）")

print()
print(f"评测完成，总耗时 {time.time()-t0:.0f}s")
print(f"结论：含技艺名全集 Hit@1 {pct(by_craftq['含技艺名']['RRF']['h1'][0], by_craftq['含技艺名']['RRF']['h1'][1])} → "
      f"{pct(by_craftq['含技艺名']['RRF+置顶']['h1'][0], by_craftq['含技艺名']['RRF+置顶']['h1'][1])}，"
      f"不含技艺名全集零回归（Hit@1={pct(by_craftq['不含技艺名']['RRF+置顶']['h1'][0], by_craftq['不含技艺名']['RRF+置顶']['h1'][1])}）")
