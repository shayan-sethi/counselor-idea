# AI Model Training & Evaluation Report

This report summarizes the performance of the three predictive AI models trained on the cleaned Discover Uni (KIS) higher education dataset.

## Model: Graduate Median Salary (£) (Salary)
Predicting median salary 3 years post-graduation.

### Performance Metrics
- **Samples Used**: 23,374
- **R² Score**: 0.6411
- **Mean Absolute Error (MAE)**: 1427.24
- **Root Mean Squared Error (RMSE)**: 2603.60

### Top 10 Feature Importances
| Feature | Importance |
| --- | --- |
| `nss_average_satisfaction` | 0.2562 |
| `sbj_group_CAH10` | 0.0907 |
| `TARAGG` | 0.0591 |
| `sbj_group_CAH25` | 0.0535 |
| `tef_outcomes` | 0.0515 |
| `tef_experience` | 0.0451 |
| `KISAIMLABEL_BA` | 0.0379 |
| `tef_overall` | 0.0360 |
| `YEARABROAD` | 0.0336 |
| `SANDWICH` | 0.0306 |

---

## Model: Student Continuation Rate (%) (Continuation)
Predicting percentage of students continuing after year 1.

### Performance Metrics
- **Samples Used**: 28,252
- **R² Score**: 0.4796
- **Mean Absolute Error (MAE)**: 7.30
- **Root Mean Squared Error (RMSE)**: 11.42

### Top 10 Feature Importances
| Feature | Importance |
| --- | --- |
| `nss_average_satisfaction` | 0.3242 |
| `TARAGG` | 0.0743 |
| `tef_outcomes` | 0.0629 |
| `KISLEVEL` | 0.0594 |
| `tef_experience` | 0.0450 |
| `sbj_group_CAH17` | 0.0397 |
| `COUNTRY_XF` | 0.0365 |
| `YEARABROAD` | 0.0352 |
| `SANDWICH` | 0.0304 |
| `FOUNDATION` | 0.0294 |

---

## Model: Professional Employment/Study Rate (%) (Employment)
Predicting percentage of graduates entering professional work/study.

### Performance Metrics
- **Samples Used**: 25,491
- **R² Score**: 0.4061
- **Mean Absolute Error (MAE)**: 4.00
- **Root Mean Squared Error (RMSE)**: 5.99

### Top 10 Feature Importances
| Feature | Importance |
| --- | --- |
| `nss_average_satisfaction` | 0.4230 |
| `TARAGG` | 0.0809 |
| `tef_experience` | 0.0376 |
| `tef_outcomes` | 0.0359 |
| `SANDWICH` | 0.0357 |
| `YEARABROAD` | 0.0356 |
| `FOUNDATION` | 0.0299 |
| `tef_overall` | 0.0295 |
| `KISAIMLABEL_BA` | 0.0159 |
| `KISAIMLABEL_BSc` | 0.0159 |

---

