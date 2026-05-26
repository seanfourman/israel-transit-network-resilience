# מדדי הערכה לאחר שיבוש

## Largest Component Share (LCS)

### הגדרה
```
LCS(k) = |V_largest(k)| / |V_original|
```
כאשר `V_largest(k)` הוא גודל הרכיב הגדול ביותר לאחר הסרת k תחנות.

### פרשנות
- LCS = 1.0: הרשת עדיין מחוברת לחלוטין
- LCS = 0.5: רק 50% מהתחנות המקוריות עדיין מחוברות לרכיב הראשי
- **ציר X בגרף ה-Resilience Curve:** מספר התחנות שהוסרו
- **ציר Y:** ה-LCS

---

## Number of Connected Components

### הגדרה
מספר הרכיבים הקשורים בגרף לאחר ההסרה.

### פרשנות
- 1 רכיב = רשת מחוברת
- k רכיבים > 1 = k "אזורים מנותקים"
- עלייה מהירה = הרשת "מתפוררת" מהר

---

## Disconnected Stations Count

### הגדרה
```
disconnected(k) = |V_original| - |V_largest(k)|
```

### פרשנות
כמה תחנות איבדו קשר עם הרשת הראשית? זה המספר של "נוסעים שנתקעו".

---

## Average Shortest Path Length (ASPL)

### הגדרה
```
ASPL(k) = mean(d(u, v) for all reachable pairs u, v in largest component)
```

### פרשנות
- עולה → נוסעים צריכים לנסוע יותר זמן
- קפיצה חדה = "צוואר בקבוק" הוסר

### הערה טכנית
חישוב ASPL על גרף גדול הוא יקר. נחשב על דגימה של 200 זוגות.

---

## Accessibility Score

### הגדרה
```
accessibility(s, k) = מספר התחנות שניתן להגיע אליהן מתחנה s בתוך 30 דקות
accessibility_drop(s, k) = accessibility(s, 0) - accessibility(s, k)
```

### פרשנות
עבור תחנות "מוצא" נבחרות, כמה תחנות אחרות נגישות לאחר ההסרה?

---

## Area Under Resilience Curve (AUC)

### הגדרה
שטח תחת עקומת ה-LCS(k) כפונקציה של k.

```
AUC = Σ LCS(k) / max(k)
```

### פרשנות
- AUC גדול = הרשת עמידה יחסית
- AUC קטן = הרשת מתמוטטת מהר
- **ניתן להשוות AUC בין אסטרטגיות שונות בטבלה אחת**

---

## טבלת מדדים — השוואה בין אסטרטגיות (למלא)

| מדד / אסטרטגיה | Betweenness | Degree | PageRank | Articulation | Random |
|----------------|-------------|--------|----------|--------------|--------|
| LCS @ k=10 | | | | | |
| LCS @ k=50 | | | | | |
| # Components @ k=10 | | | | | |
| ASPL @ k=10 | | | | | |
| AUC (כל k) | | | | | |
