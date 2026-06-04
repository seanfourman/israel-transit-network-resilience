# צינור הניתוח — Jupyter Notebooks

ניתוח עמידות רשת התחבורה הציבורית בישראל בכלים של תורת הגרפים, מאורגן כסדרת notebooks.
מריצים אותם לפי הסדר; כל notebook קורא את הפלטים של קודמיו (נשמרים תחת `outputs/`).

| Notebook | תוכן |
|---|---|
| `01_data_preparation` | טעינה וניקוי נתוני GTFS, שיוך אזור ומטרופולין |
| `02_graph_construction` | בניית גרף הנסיעות (צומת=תחנה, קשת=מקטע נסיעה) |
| `03_network_descriptive_analysis` | מבנה הרשת: רכיבים, דרגות, Articulation Points, Bridges |
| `04_centrality_analysis` | Degree, Betweenness, PageRank, Harmonic |
| `05_robustness_and_disruption_analysis` | סימולציית הסרת תחנות ועקומות עמידות |
| `06_regional_comparison` | השוואת פגיעוּת בין אזורי הארץ |
| `07_community_detection` | קהילות Louvain ו-Label Propagation |
| `08_graph_learning_node_embeddings` | Node2Vec, סיווג תחנות קריטיות |
| `09_link_prediction_and_network_improvement` | חיזוי קשתות והצעת חיבורים חדשים |
| `10_conclusions` | ריכוז הממצאים והמסקנות |

## הרצה

הנתונים נמצאים בתיקיית `israel-public-transportation/` שבשורש הפרויקט, וכל notebook מאתר אותם אוטומטית.
התקנות הנדרשות (`python-bidi`, `python-louvain`, `node2vec`) מופיעות בתא הראשון של ה-notebook שזקוק להן.

שלבים 02, 04, 05 ו-08 כוללים חישוב כבד ועשויים לקחת מספר דקות.
