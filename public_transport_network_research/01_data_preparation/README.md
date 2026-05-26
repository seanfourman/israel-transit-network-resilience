# שלב 01 — הכנת הדאטה

## מה המטרה של החלק הזה?

לטעון, לנקות, ולאחד את קבצי GTFS של תחבורה ציבורית ישראלית,
כך שהנתונים יהיו מוכנים לבניית גרף נכון ואמין בשלב הבא.

## למה אנחנו עושים את זה?

גרף שנבנה על נתונים לא נקיים יניב תוצאות מוטות ושגויות:
- תחנות כפולות יקבלו centrality מנופחת
- trips שגויים ייצרו קשתות לא אמיתיות
- תחנות לא פעילות "ידללו" את הרשת מבחינת קישוריות

ניקוי נתונים הוא לא רק שלב טכני — הוא שלב מחקרי קריטי.

## קלט

קבצי GTFS מהתיקייה `israel-public-transportation/`:

| קובץ | תוכן |
|------|------|
| `stops.txt` | כל תחנות הרשת (stop_id, stop_name, lat, lon) |
| `routes.txt` | כל קווי התחבורה (route_id, route_type, agency_id) |
| `trips.txt` | כל הנסיעות (trip_id, route_id, service_id) |
| `stop_times.txt` | זמני עצירה בכל תחנה בכל נסיעה |
| `calendar.txt` | ימי פעילות לכל service_id |
| `agency.txt` | מפעילי התחבורה |

## פלט

| קובץ | תוכן |
|------|------|
| `outputs/stops_clean.csv` | תחנות מנוקות עם קואורדינטות |
| `outputs/routes_clean.csv` | קווים מנוקים |
| `outputs/trips_clean.csv` | נסיעות תקינות |
| `outputs/agencies_clean.csv` | מפעילי תחבורה |
| `outputs/data_cleaning_report.json` | כמה שורות הוסרו ולמה |

The current staged script does not export `stop_times_clean.csv`; the large
`stop_times.txt` file is streamed directly by the primary pipeline in `src/`.

## איך זה מקדם את שאלת המחקר?

שאלת המחקר עוסקת בעמידות הרשת — אבל אפשר לענות עליה רק אם הרשת שנבנית
משקפת את המציאות. ניקוי הדאטה מבטיח שהרשת שנבנה היא הרשת האמיתית.

## קבצים/סקריפטים בחלק הזה

- `scripts/01_load_and_clean.py` — loads stops, routes, trips, and agencies;
  cleans stop coordinates; and assigns geographic region/metro labels.

## מה צריך להופיע בדוח הסופי?

- תיאור הדאטה (כמה תחנות, כמה קווים, כמה נסיעות לפני ניקוי)
- החלטות הניקוי שנעשו ולמה
- כמה שורות הוסרו בכל שלב
- validation שהדאטה המנוקה עדיין מייצגת את הרשת הכוללת

## TODO / Historical Plan

- [x] לטעון את קבצי GTFS העיקריים ולהדפיס גדלים
- [x] לנקות תחנות ללא קואורדינטות תקינות
- [x] להוסיף שיוך אזורי ומטרופוליני
- [x] לייצר data_cleaning_report.json
- [ ] לתעד את כל החלטות הניקוי בcleaning_decisions.md

## פלטים צפויים

```
outputs/
├── agencies_clean.csv
├── routes_clean.csv
├── stops_clean.csv
├── trips_clean.csv
└── data_cleaning_report.json
```
