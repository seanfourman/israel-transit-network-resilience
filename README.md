# עמידות רשת התחבורה הציבורית בישראל

כותרת העבודה:

**מעבר ממרכזיות לנגישות: עמידות רשת התחבורה הציבורית בישראל תחת שיבושי תחנות ומקטעי נסיעה מרכזיים**

הפרויקט מנתח את קובצי ה-GTFS של התחבורה הציבורית בישראל כרשת של תחנות. המטרה אינה רק לדרג תחנות לפי מדדי מרכזיות, אלא לבדוק כיצד שיבושים משפיעים על נגישות, ואילו קישורי גיבוי קטנים יכולים לשפר את עמידות הרשת.

הערת מושג: **מקטע נסיעה** הוא מעבר ישיר בין שתי תחנות עוקבות באותה נסיעה. למשל, אם קו אוטובוס נוסע מתחנה א' לתחנה ב', המעבר הזה הוא מקטע. **תחנה מאוחדת** היא כמה תחנות או רציפים סמוכים שמייצגים בפועל אותו מקום תחבורתי, ולכן בניתוח נתייחס אליהם כתחנה אחת.

## שאלת המחקר

אילו תחנות או מקטעי נסיעה הם באמת קריטיים לנגישות התחבורה הציבורית בישראל בזמן שיבושים, ואיזה סט קטן של קישורי גיבוי או שיפורי מעבר יכול להפוך את הרשת לעמידה יותר?

## למה זה יותר ממדדי מרכזיות

מדדים כמו מספר חיבורים, עומס שירות, PageRank והופעה על מסלולים קצרים משמשים כקו בסיס בלבד. הניסוי המרכזי מודד מה קורה אחרי הסרת תחנות:

- עד כמה הרכיב הקשיר הגדול מתכווץ.
- כמה תחנות נשארות נגישות בתוך סף זמן נתון.
- האם הסרה ממוקדת מזיקה יותר מהסרה אקראית.
- האם קישורי גיבוי גיאוגרפיים יכולים לשחזר קישוריות.

## נתונים

תיקיית הנתונים:

```text
israel-public-transportation/
```

הקבצים הקיימים כרגע בעץ העבודה:

- `agency.txt`
- `calendar.txt`
- `fare_attributes.txt`
- `fare_rules.txt`
- `routes.txt`
- `stops.txt`
- `translations.txt`
- `trips.txt`

הניתוח המלא דורש גם:

- `stop_times.txt`
- אופציונלית: `shapes.txt`

אלו קבצים גדולים שמופיעים בהיסטוריית Git LFS של המאגר. אם הם חסרים, צריך לשחזר אותם לפני הרצת הניתוח:

```bash
git checkout 733a885 -- israel-public-transportation/stop_times.txt
git lfs pull --include="israel-public-transportation/stop_times.txt"
```

להרחבות מבוססות צורת מסלול:

```bash
git checkout 733a885 -- israel-public-transportation/shapes.txt
git lfs pull --include="israel-public-transportation/shapes.txt"
```

## התקנה

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## הרצה

הרצה מלאה / ברירת מחדל:

```bash
python src/transit_resilience_analysis.py \
  --data-dir israel-public-transportation \
  --output-dir outputs
```

יצירת גרפים מסבירים מתוך ההרצה הסופית:

```bash
python src/make_explanatory_figures.py
```

הרצה מהירה לחקירה ראשונית:

```bash
python src/transit_resilience_analysis.py \
  --data-dir israel-public-transportation \
  --output-dir outputs \
  --betweenness-samples 16 \
  --accessibility-sample 24 \
  --resilience-removals 100 \
  --resilience-steps 6 \
  --random-trials 1 \
  --single-disruption-candidates 25 \
  --backup-links 5
```

## תוצרים מרכזיים

טבלאות:

- `outputs/tables/graph_build_summary.csv`
- `outputs/tables/network_summary.csv`
- `outputs/tables/baseline_accessibility.csv`
- `outputs/tables/unified_stations.csv`
- `outputs/tables/station_metrics.csv`
- `outputs/tables/resilience_curve.csv`
- `outputs/tables/segment_resilience_curve.csv`
- `outputs/tables/single_station_disruption_impact.csv`
- `outputs/tables/single_segment_disruption_impact.csv`
- `outputs/tables/recommended_backup_links.csv`
- `outputs/tables/mitigation_summary.csv`

תרשימים:

- `outputs/figures/unified_station_map.png`
- `outputs/figures/resilience_curve.png`
- `outputs/figures/segment_resilience_curve.png`
- `outputs/figures/single_station_impact.png`
- `outputs/figures/single_segment_impact.png`
- `outputs/figures/backup_links_map.png`

גרפים מסבירים להרצה הסופית:

- `outputs/final/explanatory_figures/01_research_flow.png`
- `outputs/final/explanatory_figures/02_radius_choice.png`
- `outputs/final/explanatory_figures/03_station_removal_strategies.png`
- `outputs/final/explanatory_figures/04_stations_vs_segments.png`
- `outputs/final/explanatory_figures/05_busy_vs_critical.png`
- `outputs/final/explanatory_figures/06_critical_station_map.png`
- `outputs/final/explanatory_figures/07_critical_station_zooms.png`
- `outputs/final/explanatory_figures/08_segment_story.png`
- `outputs/final/explanatory_figures/09_backup_links_before_after.png`
- `outputs/final/explanatory_figures/top_critical_stations.csv`

## קבצי הפרויקט

- [reports/proposal.md](reports/proposal.md): הצעת הפרויקט והיקף העבודה.
- [reports/visual_explanation.md](reports/visual_explanation.md): הסבר פשוט לקריאת הגרפים החדשים.
- [reports/final_findings.md](reports/final_findings.md): סיכום הממצאים המרכזיים.
- [src/transit_resilience_analysis.py](src/transit_resilience_analysis.py): פייפליין ניתוח ו-CLI.
- [src/run_sensitivity_experiments.py](src/run_sensitivity_experiments.py): ניסויי רגישות לרדיוס איחוד תחנות ולספי זמן נגישות.
- [src/make_explanatory_figures.py](src/make_explanatory_figures.py): יצירת גרפים אינטואיטיביים להצגה ולדוח.
- [notebooks/accessibility_resilience_analysis.ipynb](notebooks/accessibility_resilience_analysis.ipynb): מחברת להרצה והגשה בקורס.
- `docs/Graph_Algo_project_guidelines_2026.pdf`: הנחיות הקורס.

## הערות מימוש

- תחנות GTFS מתאחדות לתחנות מאוחדות לפי `parent_station` ולפי רדיוס גיאוגרפי.
- שתי תחנות עוקבות ב-`stop_times.txt` יוצרות קשת מכוונת.
- משקל הקשת הוא מספר מקטעי הנסיעה המתוזמנים.
- זמן הקשת מחושב מתוך זמני ההגעה והיציאה ב-GTFS כאשר הנתון זמין.
- נגישות נמדדת מתחנות מוצא מדגמיות באמצעות מסלולים קצרים בתוך סף זמן.
- קישורי גיבוי הם מועמדים להליכה/שאטל בין תחנות מאוחדות סמוכות שהתנתקו אחרי שיבוש.

## מגבלות ידועות

- המודל משתמש בלוחות זמנים ולא בנתוני ביקוש נוסעים.
- רדיוס איחוד התחנות יכול לאחד יותר מדי או פחות מדי תחנות.
- מדד ההופעה על מסלולים קצרים מחושב בקירוב בגלל גודל הרשת.
- קישורי הגיבוי הם מועמדים אלגוריתמיים ודורשים בדיקת היתכנות מציאותית.
