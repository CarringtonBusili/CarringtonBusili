"""
Dynamic Micro-Clustering and Assortment — Blueprint section 5.3
(expansion phase).

D365's JAM extension ranges stores using static rules. This engine
supplies the dynamic, data-driven branch economic-profile signal JAM's
clustering is blind to: each store's real till currency-mix, its
realised category sales mix, and its sensitivity to liquidity pressure,
clustered independently of the store's assumed profile label. Where the
data-driven cluster disagrees with the static label, that store's
JAM ranging is running on a stale assumption.
"""
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

N_CLUSTERS = 5


def build_store_features(data: dict) -> pd.DataFrame:
    panel = data["panel"]
    till_mix = data["till_mix"].merge(data["stores"][["store_id", "profile"]], on="store_id")

    till_stats = (
        till_mix.groupby("store_id")["usd_till_share"]
        .agg(["mean", "std"])
        .rename(columns={"mean": "avg_usd_share", "std": "till_volatility"})
    )

    revenue_mix = (
        panel.groupby(["store_id", "category"], observed=True)["revenue_usd"].sum().unstack(fill_value=0)
    )
    revenue_share = revenue_mix.div(revenue_mix.sum(axis=1).replace(0, np.nan), axis=0).fillna(0)
    revenue_share.columns = [f"mix_{c.replace(' ', '_').replace('&', 'and')}" for c in revenue_share.columns]

    stores = data["stores"].set_index("store_id")[["profile", "price_sensitivity", "volatility"]]

    features = stores.join(till_stats).join(revenue_share).reset_index()
    return features


def run_clustering(features: pd.DataFrame, n_clusters: int = N_CLUSTERS):
    feature_cols = [c for c in features.columns if c.startswith("mix_")] + [
        "avg_usd_share", "till_volatility", "price_sensitivity", "volatility"
    ]
    X = features[feature_cols].fillna(0)
    X_scaled = StandardScaler().fit_transform(X)

    kmeans = KMeans(n_clusters=n_clusters, n_init=10, random_state=42)
    labels = kmeans.fit_predict(X_scaled)

    coords = PCA(n_components=2, random_state=42).fit_transform(X_scaled)

    out = features.copy()
    out["dynamic_cluster"] = labels
    out["pca_x"] = coords[:, 0]
    out["pca_y"] = coords[:, 1]
    return out, feature_cols


def profile_vs_cluster_crosstab(clustered: pd.DataFrame) -> pd.DataFrame:
    return pd.crosstab(clustered["profile"], clustered["dynamic_cluster"])


def drift_candidates(clustered: pd.DataFrame) -> pd.DataFrame:
    """Stores whose dynamic cluster is the minority outcome for their
    static profile label — the branches JAM's static rules are most
    likely mis-ranging today."""
    majority_cluster = (
        clustered.groupby("profile")["dynamic_cluster"]
        .agg(lambda s: s.value_counts().idxmax())
        .rename("profile_majority_cluster")
    )
    merged = clustered.merge(majority_cluster, on="profile", how="left")
    drift = merged[merged["dynamic_cluster"] != merged["profile_majority_cluster"]]
    cols = ["store_id", "profile", "dynamic_cluster", "profile_majority_cluster",
            "avg_usd_share", "till_volatility"]
    return drift[cols].reset_index(drop=True)


def build_assortment_report(data: dict) -> dict:
    features = build_store_features(data)
    clustered, feature_cols = run_clustering(features)
    crosstab = profile_vs_cluster_crosstab(clustered)
    drift = drift_candidates(clustered)
    return {
        "clustered": clustered,
        "feature_cols": feature_cols,
        "crosstab": crosstab,
        "drift_candidates": drift,
    }
