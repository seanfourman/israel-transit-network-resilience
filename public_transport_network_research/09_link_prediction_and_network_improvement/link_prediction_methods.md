# שיטות Link Prediction — פירוט

## מה שאנחנו חוזים?

**Input:** זוג תחנות (u, v) שאינן מחוברות ישירות
**Output:** ציון/הסתברות שקשת u-v אמורה להתקיים

---

## שיטה א — Common Neighbors

```
score(u, v) = |{w : w ∈ N(u) ∩ N(v)}|
```

**פרשנות תחבורתית:** שתי תחנות שיש להן הרבה שכנים משותפים — ייתכן שכדאי לחברן ישירות, במקום לעבור דרך שכנים.

**מגבלה:** מעדיף תחנות Hub (שיש להן הרבה שכנים בכלל).

---

## שיטה ב — Jaccard Coefficient

```
score(u, v) = |N(u) ∩ N(v)| / |N(u) ∪ N(v)|
```

**פרשנות:** מנרמל את CN ביחס לכלל השכנים. תחנות עם מעט שכנים שחולקים הרבה — ניקוד גבוה.

---

## שיטה ג — Adamic-Adar

```
score(u, v) = Σ_{w ∈ N(u)∩N(v)} 1/log(degree(w))
```

**פרשנות:** שכן משותף עם מעט חיבורים "ייחודי" יותר ולכן תורם יותר לניקוד.
**דוגמה:** שתי תחנות שמחוברות לתחנה פריפריאלית קטנה — תרומה גדולה יותר מאשר שתי תחנות שמחוברות לתחנה מרכזית גדולה.

---

## שיטה ד — Resource Allocation

```
score(u, v) = Σ_{w ∈ N(u)∩N(v)} 1/degree(w)
```

דומה ל-Adamic-Adar אבל ללא לוגריתם — יותר אגרסיבי לגבי hubs.

---

## שיטה ה — Preferential Attachment

```
score(u, v) = degree(u) × degree(v)
```

**פרשנות:** "עשיר מתעשר" — תחנות עם הרבה חיבורים נוטות לרכוש עוד חיבורים.
**מגבלה:** לא מתחשב בשכנים משותפים בכלל.

---

## שיטה ו — Node2Vec Embeddings (ML)

```python
# Feature Engineering לכל זוג (u, v):
hadamard  = embeddings[u] * embeddings[v]           # element-wise multiply
l2        = (embeddings[u] - embeddings[v]) ** 2    # squared difference
avg       = (embeddings[u] + embeddings[v]) / 2     # average
cosine    = cosine_similarity([embeddings[u]], [embeddings[v]])[0][0]  # scalar
```

**מודל:** Logistic Regression על features אלו

```python
X = [hadamard(u, v) for u, v in pairs]
y = [1 if edge else 0 for edge in pairs]
clf = LogisticRegression(max_iter=500)
```

---

## השוואת שיטות — טבלה (למלא לאחר הרצה)

| שיטה | AUC | Precision@10 | Recall@10 | זמן חישוב |
|------|-----|-------------|----------|-----------|
| Common Neighbors | | | | |
| Jaccard | | | | |
| Adamic-Adar | | | | |
| Resource Allocation | | | | |
| Preferential Attachment | | | | |
| Node2Vec + LR | | | | |
| Baseline (random) | ~0.5 | | | |
