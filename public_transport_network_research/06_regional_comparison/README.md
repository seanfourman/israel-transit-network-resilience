# שלב 06 — השוואה אזורית

## מה המטרה של החלק הזה?

לחלק את תחנות הרשת לפי אזורים גיאוגרפיים ולבדוק האם הפגיעות לשיבושים שונה בין אזורים.

## למה אנחנו עושים את זה?

שאלת המחקר שואלת: "האם הפגיעה שונה בין אזורים שונים בארץ?"
ניתוח אזורי מוסיף ממד גיאוגרפי לניתוח הטופולוגי — לא רק "מי התחנה הכי חשובה" אלא "באיזה אזור יש יותר תחנות קריטיות?"

## קלט

- `02_graph_construction/outputs/nodes.csv` (כולל lat, lon)
- `04_centrality_analysis/outputs/stop_metrics.csv`
- `03_network_descriptive_analysis/outputs/articulation_points.csv`
- `03_network_descriptive_analysis/outputs/bridges.csv`
- `05_robustness_and_disruption_analysis/outputs/disruption_results.csv`

## פלט

| קובץ | תוכן |
|------|------|
| `outputs/regional_assignments.csv` | שיוך כל תחנה לאזור |
| `outputs/regional_summary.csv` | סיכום סטטיסטיקות לכל אזור |
| `outputs/critical_stations_by_region.csv` | מספר תחנות קריטיות לאזור |
| `figures/06_regional_comparison/` | גרפים |

## איך זה מקדם את שאלת המחקר?

שאלת המחקר שואלת על הבדלים בין אזורים. שלב זה עונה ישירות: "כן, אזור X פגיע יותר מאזור Y, ומסיבה Z."

## הגדרת אזורים

### אפשרות א — לפי גיאוגרפיה (קו רוחב)

| אזור | קו רוחב (lat) |
|------|---------------|
| צפון | > 32.7 |
| מרכז | 31.5 - 32.7 |
| ירושלים | 31.7 - 31.9 (טווח מיוחד) |
| דרום | < 31.5 |

### אפשרות ב — לפי מטרופולין (עיר קרובה)

- **מטרופולין תל אביב:** רדיוס 30 ק"מ ממרכז ת"א
- **מטרופולין חיפה:** רדיוס 25 ק"מ ממרכז חיפה
- **מטרופולין ירושלים:** רדיוס 20 ק"מ ממרכז ירושלים
- **מטרופולין באר שבע:** רדיוס 30 ק"מ ממרכז ב"ש
- **פריפריה:** כל השאר

**ההחלטה: נשתמש בשתי השיטות ונשווה.**

---

## שאלות להשוואה

1. **כמה תחנות קריטיות לפי Betweenness גבוה יש בכל אזור?**
2. **כמה Articulation Points יש בכל אזור?**
3. **כמה Bridges יש בכל אזור?**
4. **מה ה-Degree הממוצע בכל אזור?**
5. **מה הנזק מהסרת k תחנות קריטיות מכל אזור — ביחס לגודל האזור?**
6. **האם הסרת תחנה אחת בפריפריה גורמת לנזק יחסי גדול יותר?**

---

## קבצים/סקריפטים בחלק הזה

- `scripts/01_assign_regions.py` — שיוך תחנות לאזורים
- `scripts/02_regional_centrality_stats.py` — סטטיסטיקות centrality לכל אזור
- `scripts/03_regional_robustness.py` — סימולציה אזורית
- `scripts/04_plot_regional_comparison.py` — ויזואליזציות

## ויזואליזציות נדרשות

| גרף | תוכן | מתאים ל- |
|-----|-------|----------|
| `critical_stations_by_region.png` | Bar chart — מספר תחנות קריטיות לאזור | דוח + מצגת |
| `ap_by_region.png` | מספר Articulation Points לאזור | דוח |
| `bridges_by_region.png` | מספר Bridges לאזור | דוח |
| `avg_betweenness_by_region.png` | Betweenness ממוצע לאזור | דוח |
| `regional_vulnerability_comparison.png` | השוואה כוללת בין אזורים | מצגת |
| `stations_map_by_region.png` | מפה של ישראל עם תחנות לפי צבע אזור | מצגת |

## מה צריך להופיע בדוח הסופי?

- הגדרה ברורה של כל אזור (קואורדינטות / קריטריון)
- טבלת סיכום: מספר תחנות, מספר תחנות קריטיות, מספר AP, מספר Bridges — לכל אזור
- גרפים השוואתיים
- דיון: האם פריפריה (צפון, דרום) פגיעה יותר ממרכז?

## TODO

- [ ] לשייך כל תחנה לאזור על פי קואורדינטות
- [ ] לחשב סטטיסטיקות לכל אזור
- [ ] לבדוק מתאם בין "גודל אזור" ל"מספר תחנות קריטיות"
- [ ] לייצר כל הגרפים
- [ ] לכתוב region_definition.md ו-comparison_questions.md

## פלטים צפויים

```
outputs/
├── regional_assignments.csv    (stop_id, region, metro_area)
├── regional_summary.csv        (region, num_stops, num_critical, num_ap, ...)
└── critical_stations_by_region.csv

figures/06_regional_comparison/
├── critical_stations_by_region.png
├── ap_by_region.png
├── bridges_by_region.png
├── avg_betweenness_by_region.png
├── regional_vulnerability_comparison.png
└── stations_map_by_region.png
```

## תוספת 06B — ניתוח סוציו-אקונומי וזמינות תחבורה

נוסף סקריפט משלים:

- `scripts/02_socioeconomic_equity.py`

המטרה היא לבדוק האם יש קשר בין אשכול חברתי-כלכלי של הלמ"ס לבין זמינות תחבורה ציבורית, גם לפי אזורים סטטיסטיים וגם לפי קהילות Louvain. ההסבר המלא, כולל מקור הנתונים, שיטת השיוך, המדדים, הפלטים והמגבלות נמצא כאן:

- `socioeconomic_equity_analysis.md`

פלטים עיקריים:

- `outputs/stops_with_socioeconomic.csv`
- `outputs/socioeconomic_area_access.csv`
- `outputs/socioeconomic_cluster_summary.csv`
- `outputs/community_socioeconomic_summary.csv`
- `outputs/socioeconomic_correlation_summary.csv`
- `outputs/socioeconomic_join_quality.json`

ויזואליזציות:

- `figures/06_regional_comparison/socioeconomic_access_by_cluster.png`
- `figures/06_regional_comparison/socioeconomic_stop_use_boxplot.png`
- `figures/06_regional_comparison/community_socioeconomic_access.png`
