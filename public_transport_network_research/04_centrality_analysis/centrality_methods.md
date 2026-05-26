# שיטות Centrality — פירוט טכני

## Degree Centrality

### הגדרה
```python
import networkx as nx

# גרף לא מכוון
degree_centrality = nx.degree_centrality(G_undirected)

# גרף מכוון - in/out
in_degree_centrality = nx.in_degree_centrality(G_directed)
out_degree_centrality = nx.out_degree_centrality(G_directed)
```

### פרשנות לתחבורה
- **in-degree גבוה:** הרבה קווים מגיעים לתחנה — תחנה "מקלטת" רבים
- **out-degree גבוה:** הרבה קווים יוצאים מהתחנה — תחנה "מפזרת" לרבים
- **degree (לא מכוון) גבוה:** תחנה עם הרבה חיבורים — לרוב תחנה מרכזית עירונית

### מגבלות
אינו מבחין בין תחנה עם 10 שכנים חשובים לבין תחנה עם 10 שכנים שוליים.

---

## Betweenness Centrality

### הגדרה
```python
# חישוב מלא (איטי)
betweenness = nx.betweenness_centrality(G, weight='weight_time', normalized=True)

# approximation לרשתות גדולות
betweenness_approx = nx.betweenness_centrality(G, k=500, weight='weight_time', normalized=True)
```

### פרשנות לתחבורה
- **betweenness גבוה:** המסלול הקצר בין תחנות רבות עובר דרך תחנה זו
- תחנות כאלו הן "צוואר בקבוק" — הסרתן תגרום לעקיפות ארוכות
- **קשר לסימולציה:** תחנות עם betweenness גבוה הן מועמדות ראשיות לבדיקת השפעת הסרה

### מגבלות
- חישוב מלא: O(|V| × |E|) — איטי לרשתות גדולות
- תלוי בהגדרת המשקל (זמן/תדירות)

---

## Closeness / Harmonic Centrality

### Closeness (לרשת מחוברת)
```python
closeness = nx.closeness_centrality(G_undirected, distance='weight_time')
```

### Harmonic (לרשת לא מחוברת — מומלץ)
```python
harmonic = nx.harmonic_centrality(G_undirected, distance='weight_time')
```

### פרשנות לתחבורה
- **closeness/harmonic גבוה:** ניתן להגיע מתחנה זו לכל תחנה אחרת בזמן קצר
- תחנה מרכזית גיאוגרפית (כמו "תחנה מרכזית") אמורה להיות בעלת closeness גבוה

### הבדל בין closeness ל-harmonic
closeness לא מוגדר לרשתות לא מחוברות. harmonic מטפל בזה על ידי חיבור הסכום ל- 1/d.

---

## PageRank

### הגדרה
```python
pagerank = nx.pagerank(G_directed, alpha=0.85, weight='weight_freq')
```

### הסבר אלגוריתם
דמיינו "גולש אקראי" שנוסע ברשת: בכל צומת הוא בוחר קשת אקראית ועובר לתחנה הבאה.
עם הסתברות `1-alpha` הוא "קופץ" לתחנה אקראית. PageRank מודד כמה פעמים הגולש יבקר בכל תחנה.

### פרשנות לתחבורה
- **pagerank גבוה:** תחנה שמחוברת לתחנות חשובות אחרות
- שונה מ-Degree כי לא רק כמות החיבורים חשובה, אלא "איכותם"
- מתאים לגרף **מכוון** — כי הכיוון (מי "מצביע" על מי) חשוב

---

## השוואת מדדים

| מדד | שאלה שעונה | גרף | מהיר? |
|-----|-----------|-----|-------|
| Degree | מי מחובר להכי הרבה? | שניהם | כן |
| Betweenness | מי עם הכי הרבה תנועה עוברת? | שניהם | לא |
| Closeness/Harmonic | מי הכי "קרוב" לכולם? | לא מכוון | בינוני |
| PageRank | מי מחובר להכי הרבה חשובים? | מכוון | כן |

---

## קורלציות צפויות

- **Degree ↔ PageRank:** קורלציה גבוהה — תחנות עם הרבה שכנים לרוב גם "חשובות" לפי PageRank
- **Degree ↔ Betweenness:** קורלציה בינונית — לא תמיד תחנה עם הרבה שכנים היא "צוואר בקבוק"
- **Betweenness ↔ Closeness:** קורלציה בינונית — מדדים שונים, תוצאות שונות

הקורלציות הן נושא מחקרי בפני עצמו!
