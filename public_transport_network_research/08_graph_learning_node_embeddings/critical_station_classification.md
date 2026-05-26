# משימה ב — Critical Station Classification (סיווג תחנות קריטיות)

## שאלת המחקר למשימה זו

> "האם ניתן לנבא האם תחנה קריטית על בסיס Node Embedding בלבד?"

---

## הגדרת Label

```python
def is_critical(stop_id, articulation_points, betweenness_series, threshold=0.9):
    """
    תחנה קריטית = AP או betweenness גבוה מ-90th percentile
    """
    is_ap = stop_id in articulation_points
    betw_threshold = betweenness_series.quantile(threshold)
    is_high_betweenness = betweenness_series[stop_id] >= betw_threshold
    return int(is_ap or is_high_betweenness)
```

**פרשנות:**
- `critical = 1` = תחנה קריטית
- `critical = 0` = תחנה רגילה

**הערה על חוסר איזון:** ייתכן שרק 10-15% מהתחנות יהיו "קריטיות". זה חוסר איזון (imbalance) שיש לטפל בו.

---

## טיפול ב-Class Imbalance

```python
# אפשרות א — class_weight
LogisticRegression(class_weight='balanced')

# אפשרות ב — oversampling
from imblearn.over_sampling import SMOTE
X_resampled, y_resampled = SMOTE(random_state=42).fit_resample(X_train, y_train)

# אפשרות ג — threshold tuning
# במקום threshold=0.5, לנסות 0.3 עבור precision/recall tradeoff
```

---

## מודלים

### מודל א — Logistic Regression
```python
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)
clf = LogisticRegression(class_weight='balanced', max_iter=500)
```

### מודל ב — Random Forest
```python
from sklearn.ensemble import RandomForestClassifier
clf = RandomForestClassifier(n_estimators=100, class_weight='balanced', random_state=42)
```

---

## הערכה

```python
from sklearn.metrics import classification_report, confusion_matrix

y_pred = clf.predict(X_test)
print(classification_report(y_test, y_pred, target_names=["רגילה", "קריטית"]))
```

**מדדי הערכה:**
- **Accuracy** — נמוך בגלל imbalance, פחות חשוב
- **Precision** — כמה מהתחנות שניבאנו כ"קריטיות" אכן קריטיות?
- **Recall** — כמה מהתחנות הקריטיות האמיתיות ניבאנו נכון?
- **F1-Score** — ממוצע הרמוני של Precision ו-Recall

---

## פרשנות תוצאות

**המטרה אינה לנצח את ה-SOTA — המטרה היא להראות שה-embeddings קולטים מידע מבני.**

- F1 > 0.6: embeddings לומדים מידע על קריטיות — תוצאה טובה
- F1 = 0.4-0.6: תוצאה סבירה — embeddings מכילים מידע חלקי
- F1 < 0.4: embeddings לא מספקים לסיווג זה — ייתכן שצריך פרמטרים שונים

**להשוות מול baseline:**
```python
# baseline — מנבא תמיד "לא קריטית"
baseline_f1 = f1_score(y_test, np.zeros(len(y_test)))
```

---

## פלטים

- `outputs/classification_results.json` — כל מדדי ההערכה
- `figures/08.../confusion_matrix.png` — Confusion Matrix
