"""
שלב 08 — Node2Vec: Graph Learning & Node Embeddings
קלט:  02_graph_construction/ + 04_centrality/ + 03_descriptive/
פלט:  08_graph_learning.../outputs/ + figures/
"""
import pickle
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
GRAPH_DIR   = ROOT / "public_transport_network_research/02_graph_construction/outputs"
METRICS_CSV = ROOT / "public_transport_network_research/04_centrality_analysis/outputs/stop_metrics.csv"
AP_CSV      = ROOT / "public_transport_network_research/03_network_descriptive_analysis/outputs/articulation_points.csv"
COMM_CSV    = ROOT / "public_transport_network_research/07_community_detection/outputs/community_assignments.csv"
OUT_DIR     = Path(__file__).resolve().parents[1] / "outputs"
FIG_DIR     = ROOT / "public_transport_network_research/figures/08_graph_learning_node_embeddings"
OUT_DIR.mkdir(parents=True, exist_ok=True)
FIG_DIR.mkdir(parents=True, exist_ok=True)

import pandas as pd
import numpy as np
import networkx as nx
from node2vec import Node2Vec
from sklearn.manifold import TSNE
from sklearn.decomposition import PCA
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix, f1_score
from sklearn.preprocessing import StandardScaler
from sklearn.metrics.pairwise import cosine_similarity
import matplotlib
matplotlib.use("Agg")
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))
from _hebrew_bidi import install_hebrew
install_hebrew()
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import seaborn as sns

sns.set_theme(style="whitegrid", font_scale=1.1)

EMBEDDING_DIM = 64
WALK_LENGTH   = 20
NUM_WALKS     = 5

def load():
    with open(GRAPH_DIR / "graph_undirected.pkl", "rb") as f:
        G = pickle.load(f)
    metrics = pd.read_csv(METRICS_CSV, encoding="utf-8-sig")
    metrics["betweenness"] = pd.to_numeric(metrics["betweenness"], errors="coerce").fillna(0)
    ap_df = pd.read_csv(AP_CSV, encoding="utf-8-sig")

    comm_path = Path(str(COMM_CSV))
    comm_df = pd.read_csv(comm_path, encoding="utf-8-sig") if comm_path.exists() else pd.DataFrame()
    return G, metrics, ap_df, comm_df

def train_node2vec(G):
    # עובדים על הרכיב הגדול כדי לחסוך זמן
    Gc = G.subgraph(max(nx.connected_components(G), key=len)).copy()
    print(f"  Node2Vec על הרכיב הגדול: {Gc.number_of_nodes():,} צמתים")

    n2v = Node2Vec(
        Gc,
        dimensions=EMBEDDING_DIM,
        walk_length=WALK_LENGTH,
        num_walks=NUM_WALKS,
        p=1, q=1,
        workers=1,
        seed=42,
        quiet=True,
    )
    model = n2v.fit(window=5, min_count=1, batch_words=4, epochs=3)
    embeddings = {node: model.wv[str(node)] for node in Gc.nodes()}
    return embeddings, Gc

def plot_tsne(embeddings, nodes_meta, col, title, fname, fig_dir):
    ids = list(embeddings.keys())
    matrix = np.array([embeddings[n] for n in ids])

    meta = nodes_meta.set_index("stop_id") if "stop_id" in nodes_meta.columns else nodes_meta
    labels = [meta.loc[n, col] if n in meta.index and col in meta.columns else "?" for n in ids]

    unique = sorted(set(str(l) for l in labels))
    cmap = matplotlib.colormaps.get_cmap("tab20").resampled(len(unique))
    color_map = {l: cmap(i) for i, l in enumerate(unique)}

    print(f"  t-SNE ({title}) ...")
    tsne = TSNE(n_components=2, random_state=42, perplexity=min(30, len(ids)-1), max_iter=300)
    emb_2d = tsne.fit_transform(matrix)

    fig, ax = plt.subplots(figsize=(10, 8))
    for label in unique[:15]:  # מגבילים ל-15 קטגוריות
        idx = [i for i, l in enumerate(labels) if str(l) == label]
        ax.scatter(emb_2d[idx, 0], emb_2d[idx, 1], s=5, alpha=0.5,
                   color=color_map[label], label=str(label))
    ax.legend(markerscale=3, fontsize=8, loc="best")
    ax.set_title(title)
    ax.set_xlabel("t-SNE dim 1"); ax.set_ylabel("t-SNE dim 2")
    plt.tight_layout()
    plt.savefig(fig_dir / fname, dpi=150)
    plt.close()
    print(f"  ✓ {fname}")

def plot_pca(embeddings, critical_labels, fig_dir):
    ids = list(embeddings.keys())
    matrix = np.array([embeddings[n] for n in ids])
    labels = [critical_labels.get(n, 0) for n in ids]

    pca = PCA(n_components=2, random_state=42)
    emb_2d = pca.fit_transform(matrix)

    fig, ax = plt.subplots(figsize=(9, 7))
    colors = ["#94a3b8" if l == 0 else "#dc2626" for l in labels]
    ax.scatter(emb_2d[:, 0], emb_2d[:, 1], s=4, alpha=0.4, c=colors)
    from matplotlib.patches import Patch
    legend = [Patch(color="#94a3b8", label="רגילה"), Patch(color="#dc2626", label="קריטית")]
    ax.legend(handles=legend)
    ax.set_title(f"PCA של Node Embeddings\n(אחוז שונות: {sum(pca.explained_variance_ratio_)*100:.1f}%)")
    ax.set_xlabel(f"PC1 ({pca.explained_variance_ratio_[0]*100:.1f}%)")
    ax.set_ylabel(f"PC2 ({pca.explained_variance_ratio_[1]*100:.1f}%)")
    plt.tight_layout()
    plt.savefig(fig_dir / "pca_embeddings.png", dpi=150)
    plt.close()
    print("  ✓ pca_embeddings.png")

def classify_critical(embeddings, metrics, ap_df):
    print("  סיווג תחנות קריטיות ...")
    ap_set = set(ap_df["stop_id"].astype(str))
    btw_p90 = metrics["betweenness"].quantile(0.90)
    metrics_idx = metrics.set_index("stop_id") if "stop_id" in metrics.columns else metrics

    ids = list(embeddings.keys())
    X, y = [], []
    for n in ids:
        X.append(embeddings[n])
        is_ap  = str(n) in ap_set
        is_btw = metrics_idx.loc[n, "betweenness"] >= btw_p90 if n in metrics_idx.index else False
        y.append(1 if (is_ap or is_btw) else 0)

    X, y = np.array(X), np.array(y)
    print(f"  קריטיות: {sum(y)} / {len(y)} ({sum(y)/len(y)*100:.1f}%)")

    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    scaler = StandardScaler()
    X_tr = scaler.fit_transform(X_tr)
    X_te = scaler.transform(X_te)

    results = {}
    for name, clf in [("LogisticRegression", LogisticRegression(class_weight="balanced", max_iter=500)),
                       ("RandomForest", RandomForestClassifier(n_estimators=100, class_weight="balanced", random_state=42))]:
        clf.fit(X_tr, y_tr)
        y_pred = clf.predict(X_te)
        f1 = f1_score(y_te, y_pred, average="binary")
        results[name] = {
            "f1": round(f1, 4),
            "report": classification_report(y_te, y_pred, target_names=["רגילה","קריטית"]),
            "confusion": confusion_matrix(y_te, y_pred).tolist(),
        }
        print(f"\n  {name} — F1={f1:.4f}")
        print(results[name]["report"])

    return results, dict(zip(ids, y.tolist()))

def plot_confusion_matrix(cm_data, title, fname, fig_dir):
    fig, ax = plt.subplots(figsize=(6, 5))
    sns.heatmap(np.array(cm_data), annot=True, fmt="d", cmap="Blues",
                xticklabels=["רגילה","קריטית"], yticklabels=["רגילה","קריטית"], ax=ax)
    ax.set_xlabel("ניבוי"); ax.set_ylabel("אמת")
    ax.set_title(title)
    plt.tight_layout()
    plt.savefig(fig_dir / fname, dpi=150)
    plt.close()
    print(f"  ✓ {fname}")

def station_similarity(embeddings, G, top_k=10):
    ids = list(embeddings.keys())
    matrix = np.array([embeddings[n] for n in ids])
    sims = cosine_similarity(matrix)

    # בחר 5 תחנות לדוגמה
    sample_indices = [0, len(ids)//5, len(ids)//3, len(ids)//2, len(ids)*3//4]
    rows = []
    for idx in sample_indices:
        target = ids[idx]
        target_name = G.nodes[target].get("stop_name", target) if target in G.nodes else target
        top_idx = np.argsort(sims[idx])[::-1][1:top_k+1]
        for rank, j in enumerate(top_idx, 1):
            sim_id = ids[j]
            sim_name = G.nodes[sim_id].get("stop_name", sim_id) if sim_id in G.nodes else sim_id
            rows.append({
                "target_stop": target,
                "target_name": target_name,
                "rank": rank,
                "similar_stop": sim_id,
                "similar_name": sim_name,
                "cosine_similarity": round(float(sims[idx][j]), 4),
            })
    return pd.DataFrame(rows)

def main():
    print("=== שלב 08: Node2Vec + Classification ===")
    G, metrics, ap_df, comm_df = load()

    print("\n  מאמן Node2Vec ...")
    embeddings, Gc = train_node2vec(G)
    print(f"  Embeddings: {len(embeddings)} צמתים × {EMBEDDING_DIM} ממדים")

    # שמירת embeddings
    emb_df = pd.DataFrame([{"stop_id": k, **{f"e{i}": v for i, v in enumerate(vec)}}
                            for k, vec in embeddings.items()])
    emb_df.to_csv(OUT_DIR / "embeddings_df.csv", index=False, encoding="utf-8-sig")
    print("  ✓ embeddings_df.csv")

    # meta לכל node
    nodes_meta_rows = [{"stop_id": n,
                         "region": G.nodes[n].get("region","?"),
                         "metro":  G.nodes[n].get("metro","?")}
                        for n in embeddings.keys()]
    nodes_meta = pd.DataFrame(nodes_meta_rows)

    if not comm_df.empty:
        comm_idx = comm_df.set_index("stop_id")
        nodes_meta["community"] = nodes_meta["stop_id"].map(
            lambda x: str(comm_idx.loc[x, "community_louvain"]) if x in comm_idx.index else "?")
    else:
        nodes_meta["community"] = "?"

    print("\n  יוצר גרפי Embeddings ...")
    plot_tsne(embeddings, nodes_meta, "region", "t-SNE — צבע לפי אזור גיאוגרפי",
              "tsne_by_region.png", FIG_DIR)
    if not comm_df.empty:
        plot_tsne(embeddings, nodes_meta, "community", "t-SNE — צבע לפי קהילה",
                  "tsne_by_community.png", FIG_DIR)

    print("\n  סיווג תחנות קריטיות ...")
    clf_results, critical_labels = classify_critical(embeddings, metrics, ap_df)

    for name, res in clf_results.items():
        plot_confusion_matrix(res["confusion"],
                              f"Confusion Matrix — {name} (F1={res['f1']:.3f})",
                              f"confusion_matrix_{name.lower()[:2]}.png", FIG_DIR)

    # t-SNE צבוע לפי קריטיות
    ids = list(embeddings.keys())
    nodes_meta["is_critical"] = nodes_meta["stop_id"].map(
        lambda x: "קריטית" if critical_labels.get(x, 0) == 1 else "רגילה")
    plot_tsne(embeddings, nodes_meta, "is_critical",
              "t-SNE — קריטיות (אדום = קריטית)",
              "tsne_by_critical.png", FIG_DIR)
    plot_pca(embeddings, critical_labels, FIG_DIR)

    print("\n  Station Similarity ...")
    sim_df = station_similarity(embeddings, G)
    sim_df.to_csv(OUT_DIR / "station_similarity.csv", index=False, encoding="utf-8-sig")
    print("  ✓ station_similarity.csv")
    print(sim_df[sim_df["rank"] == 1][["target_name","similar_name","cosine_similarity"]].to_string(index=False))

    import json
    with open(OUT_DIR / "classification_results.json", "w", encoding="utf-8") as f:
        json.dump({k: {kk: vv for kk, vv in v.items() if kk != "report"}
                   for k, v in clf_results.items()}, f, ensure_ascii=False, indent=2)

    print(f"\nפלטים נשמרו ב:\n  {OUT_DIR}\n  {FIG_DIR}")

if __name__ == "__main__":
    main()
