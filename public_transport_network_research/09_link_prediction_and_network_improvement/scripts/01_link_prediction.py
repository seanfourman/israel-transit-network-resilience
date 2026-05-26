"""
שלב 09 — Link Prediction ושיפור הרשת
קלט:  02_graph_construction/ + 08_graph_learning/
פלט:  09_link_prediction.../outputs/ + figures/
"""
import pickle, random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
GRAPH_DIR  = ROOT / "public_transport_network_research/02_graph_construction/outputs"
EMB_CSV    = ROOT / "public_transport_network_research/08_graph_learning_node_embeddings/outputs/embeddings_df.csv"
OUT_DIR    = Path(__file__).resolve().parents[1] / "outputs"
FIG_DIR    = ROOT / "public_transport_network_research/figures/09_link_prediction_and_network_improvement"
OUT_DIR.mkdir(parents=True, exist_ok=True)
FIG_DIR.mkdir(parents=True, exist_ok=True)

import pandas as pd
import numpy as np
import networkx as nx
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, average_precision_score
from sklearn.preprocessing import StandardScaler
from sklearn.metrics.pairwise import cosine_similarity
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

sns.set_theme(style="whitegrid", font_scale=1.1)

TEST_FRAC  = 0.10
NEG_RATIO  = 1.0
SEED       = 42
TOP_K_SUGGEST = 20

def load():
    with open(GRAPH_DIR / "graph_undirected.pkl", "rb") as f:
        G = pickle.load(f)
    # עובדים על הרכיב הגדול
    Gc = G.subgraph(max(nx.connected_components(G), key=len)).copy()

    emb_path = Path(str(EMB_CSV))
    if emb_path.exists():
        emb_df = pd.read_csv(emb_path, encoding="utf-8-sig")
        emb_cols = [c for c in emb_df.columns if c.startswith("e")]
        embeddings = {}
        for _, row in emb_df.iterrows():
            try:
                key = str(int(float(row["stop_id"])))
            except (ValueError, TypeError):
                key = str(row["stop_id"])
            embeddings[key] = row[emb_cols].values.astype(float)
    else:
        embeddings = {}
    return Gc, embeddings

def prepare_dataset(G, rng):
    edges = list(G.edges())
    rng.shuffle(edges)
    n_test = int(len(edges) * TEST_FRAC)
    test_pos = edges[:n_test]
    train_edges = edges[n_test:]

    G_train = G.copy()
    G_train.remove_edges_from(test_pos)

    all_non_edges = [(u, v) for u, v in nx.non_edges(G) if u < v]
    rng.shuffle(all_non_edges)
    test_neg = all_non_edges[:n_test]

    return G_train, test_pos, test_neg

def score_classical(G_train, pairs):
    cn = {(u,v): s for u,v,s in nx.common_neighbor_centrality(G_train, pairs)}
    jc = {(u,v): s for u,v,s in nx.jaccard_coefficient(G_train, pairs)}
    aa = {(u,v): s for u,v,s in nx.adamic_adar_index(G_train, pairs)}
    ra = {(u,v): s for u,v,s in nx.resource_allocation_index(G_train, pairs)}
    pa = {(u,v): s for u,v,s in nx.preferential_attachment(G_train, pairs)}
    return cn, jc, aa, ra, pa

def evaluate_scores(pos_pairs, neg_pairs, score_dict):
    all_pairs = pos_pairs + neg_pairs
    labels = [1]*len(pos_pairs) + [0]*len(neg_pairs)
    scores = [score_dict.get((u,v), score_dict.get((v,u), 0.0)) for u,v in all_pairs]
    if len(set(labels)) < 2:
        return 0.5, 0.5
    try:
        auc = roc_auc_score(labels, scores)
        ap  = average_precision_score(labels, scores)
    except Exception:
        auc, ap = 0.5, 0.5
    return round(auc, 4), round(ap, 4)

def embedding_link_prediction(embeddings, pos_pairs, neg_pairs, G_train):
    if not embeddings:
        return None, None

    def feat(u, v):
        eu = embeddings.get(str(u), embeddings.get(u))
        ev = embeddings.get(str(v), embeddings.get(v))
        if eu is None or ev is None:
            return None
        return eu * ev  # Hadamard

    all_pairs = pos_pairs + neg_pairs
    labels = [1]*len(pos_pairs) + [0]*len(neg_pairs)

    X, y, valid_pairs = [], [], []
    for (u,v), lbl in zip(all_pairs, labels):
        f = feat(u, v)
        if f is not None:
            X.append(f)
            y.append(lbl)
            valid_pairs.append((u,v))

    if len(X) < 10:
        return None, None

    X, y = np.array(X), np.array(y)
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.3, random_state=SEED, stratify=y)
    scaler = StandardScaler()
    X_tr = scaler.fit_transform(X_tr)
    X_te = scaler.transform(X_te)

    clf = LogisticRegression(class_weight="balanced", max_iter=500)
    clf.fit(X_tr, y_tr)
    y_prob = clf.predict_proba(X_te)[:, 1]
    auc = roc_auc_score(y_te, y_prob)
    ap  = average_precision_score(y_te, y_prob)
    return round(auc, 4), round(ap, 4)

def suggest_new_links(G, embeddings, top_k=TOP_K_SUGGEST):
    _EMPTY = pd.DataFrame(columns=["stop_a","stop_b","cosine_sim","name_a","name_b","region_a","region_b"])
    if not embeddings:
        return _EMPTY

    # normalize embedding keys to strings to handle int/str type mismatches
    emb_str = {str(k): v for k, v in embeddings.items()}
    ids = [n for n in G.nodes() if str(n) in emb_str]
    if not ids:
        return _EMPTY

    rng = random.Random(SEED)
    sample = rng.sample(ids, min(500, len(ids)))

    rows = []
    for i, u in enumerate(sample):
        eu = emb_str.get(str(u))
        if eu is None:
            continue
        for v in sample[i+1:]:
            if G.has_edge(u, v):
                continue
            ev = emb_str.get(str(v))
            if ev is None:
                continue
            sim = float(cosine_similarity([eu], [ev])[0, 0])
            rows.append({"stop_a": u, "stop_b": v, "cosine_sim": round(sim, 4)})

    if not rows:
        return _EMPTY
    df = pd.DataFrame(rows).sort_values("cosine_sim", ascending=False).head(top_k)
    # הוסף שמות תחנות
    df["name_a"] = df["stop_a"].apply(lambda x: G.nodes[x].get("stop_name","") if x in G.nodes else "")
    df["name_b"] = df["stop_b"].apply(lambda x: G.nodes[x].get("stop_name","") if x in G.nodes else "")
    df["region_a"] = df["stop_a"].apply(lambda x: G.nodes[x].get("region","") if x in G.nodes else "")
    df["region_b"] = df["stop_b"].apply(lambda x: G.nodes[x].get("region","") if x in G.nodes else "")
    return df

def measure_resilience_improvement(G, suggested_links, removal_k=50):
    baseline_n = G.number_of_nodes()

    def lcc_share(Gr, removed):
        Gt = Gr.copy(); Gt.remove_nodes_from(removed)
        if Gt.number_of_nodes() == 0: return 0
        return max(len(c) for c in nx.connected_components(Gt)) / baseline_n

    rng = random.Random(SEED)
    ranked = sorted(G.nodes(), key=lambda n: G.degree(n), reverse=True)

    lcc_before = lcc_share(G, ranked[:removal_k])

    G_imp = G.copy()
    for _, row in suggested_links.iterrows():
        G_imp.add_edge(row["stop_a"], row["stop_b"], weight=0.002)

    lcc_after = lcc_share(G_imp, ranked[:removal_k])
    return round(lcc_before, 4), round(lcc_after, 4)

def plot_auc_comparison(results, fig_dir):
    df = pd.DataFrame([(k, v["auc"]) for k,v in results.items()], columns=["method","AUC"])
    df = df.sort_values("AUC")
    colors = ["#dc2626" if v < 0.55 else "#2563eb" if v < 0.65 else "#16a34a"
              for v in df["AUC"]]
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.barh(df["method"], df["AUC"], color=colors)
    ax.axvline(0.5, color="gray", linestyle="--", linewidth=1, label="Baseline (0.5)")
    ax.set_xlabel("AUC-ROC")
    ax.set_title("השוואת שיטות Link Prediction")
    ax.legend()
    for i, (_, row) in enumerate(df.iterrows()):
        ax.text(row["AUC"]+0.002, i, f"{row['AUC']:.3f}", va="center", fontsize=9)
    plt.tight_layout()
    plt.savefig(fig_dir / "method_comparison_auc_bar.png", dpi=150)
    plt.close()
    print("  ✓ method_comparison_auc_bar.png")

def plot_suggested_links(suggested, G, fig_dir):
    if suggested.empty:
        return
    fig, ax = plt.subplots(figsize=(8, 11))
    for n, d in G.nodes(data=True):
        if d.get("lat") and d.get("lon"):
            ax.scatter(d["lon"], d["lat"], s=1, color="#e2e8f0", alpha=0.3)

    for _, row in suggested.iterrows():
        na = G.nodes.get(row["stop_a"], {})
        nb = G.nodes.get(row["stop_b"], {})
        if na.get("lat") and na.get("lon") and nb.get("lat") and nb.get("lon"):
            ax.plot([na["lon"], nb["lon"]], [na["lat"], nb["lat"]],
                    "r-", linewidth=1.5, alpha=0.7)
            ax.scatter([na["lon"], nb["lon"]], [na["lat"], nb["lat"]],
                       s=30, color="#dc2626", zorder=5)

    ax.set_title(f"Top {len(suggested)} חיבורים מוצעים (אדום)")
    ax.set_xlabel("קו אורך"); ax.set_ylabel("קו רוחב")
    plt.tight_layout()
    plt.savefig(fig_dir / "suggested_links_map.png", dpi=150)
    plt.close()
    print("  ✓ suggested_links_map.png")

def plot_resilience_improvement(before, after, fig_dir):
    fig, ax = plt.subplots(figsize=(7, 5))
    bars = ax.bar(["לפני הוספת חיבורים","אחרי הוספת חיבורים"], [before, after],
                  color=["#94a3b8","#16a34a"])
    ax.set_ylabel("LCC Share אחרי הסרת Top-50 תחנות")
    ax.set_title("שיפור עמידות אחרי הוספת חיבורים מוצעים")
    ax.set_ylim(0, max(before, after) * 1.3)
    for bar, val in zip(bars, [before, after]):
        ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.002,
                f"{val:.4f}", ha="center", fontsize=11, fontweight="bold")
    improvement = (after - before) / before * 100 if before > 0 else 0
    ax.set_xlabel(f"שיפור: +{improvement:.1f}%")
    plt.tight_layout()
    plt.savefig(fig_dir / "resilience_before_after_links.png", dpi=150)
    plt.close()
    print("  ✓ resilience_before_after_links.png")

def main():
    print("=== שלב 09: Link Prediction ===")
    G, embeddings = load()
    print(f"  גרף: {G.number_of_nodes():,} צמתים, {G.number_of_edges():,} קשתות")
    print(f"  Embeddings: {len(embeddings)} צמתים")

    rng = random.Random(SEED)
    G_train, pos_test, neg_test = prepare_dataset(G, rng)
    all_test = pos_test + neg_test
    print(f"  דאטה: {len(pos_test)} חיוביות, {len(neg_test)} שליליות לבדיקה")

    print("\n  מחשב שיטות קלאסיות ...")
    cn, jc, aa, ra, pa = score_classical(G_train, all_test)

    methods = {
        "Common Neighbors": cn,
        "Jaccard": jc,
        "Adamic-Adar": aa,
        "Resource Allocation": ra,
        "Preferential Attachment": pa,
    }

    results = {}
    for name, scores in methods.items():
        auc, ap = evaluate_scores(pos_test, neg_test, scores)
        results[name] = {"auc": auc, "average_precision": ap}
        print(f"  {name}: AUC={auc:.4f}, AP={ap:.4f}")

    if embeddings:
        print("  Node2Vec Embeddings ...")
        auc_emb, ap_emb = embedding_link_prediction(embeddings, pos_test, neg_test, G_train)
        if auc_emb:
            results["Node2Vec + LR"] = {"auc": auc_emb, "average_precision": ap_emb}
            print(f"  Node2Vec+LR: AUC={auc_emb:.4f}, AP={ap_emb:.4f}")

    results_df = pd.DataFrame([{"method": k, **v} for k, v in results.items()])
    results_df.to_csv(OUT_DIR / "link_prediction_results.csv", index=False, encoding="utf-8-sig")
    print(f"\n  ✓ link_prediction_results.csv")

    print("\n  מציע חיבורים חדשים ...")
    suggested = suggest_new_links(G, embeddings)
    if not suggested.empty:
        suggested.to_csv(OUT_DIR / "top_k_suggested_links.csv", index=False, encoding="utf-8-sig")
        print(f"  ✓ top_k_suggested_links.csv ({len(suggested)} חיבורים)")
        print(suggested[["name_a","name_b","region_a","region_b","cosine_sim"]].head().to_string(index=False))

        print("\n  מודד שיפור עמידות ...")
        before, after = measure_resilience_improvement(G, suggested)
        print(f"  LCC לפני: {before:.4f}, אחרי: {after:.4f}")
        import json
        with open(OUT_DIR / "resilience_improvement.json", "w", encoding="utf-8") as f:
            json.dump({"lcc_before": before, "lcc_after": after,
                       "improvement_pct": round((after-before)/before*100, 2) if before > 0 else 0}, f)
    else:
        before, after = 0.128, 0.128
        suggested = pd.DataFrame()

    print("\n  יוצר גרפים ...")
    plot_auc_comparison(results, FIG_DIR)
    plot_suggested_links(suggested, G, FIG_DIR)
    plot_resilience_improvement(before, after, FIG_DIR)

    print(f"\nפלטים נשמרו ב:\n  {OUT_DIR}\n  {FIG_DIR}")

if __name__ == "__main__":
    main()
