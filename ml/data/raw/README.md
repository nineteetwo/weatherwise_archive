# WeatherWise — Synthetic Dataset
## Anadolu Hackathon 2026 | Case 3

### Overview
This dataset provides rich meteorological data with pre-computed actionable labels
(clothing recommendations, umbrella flag, activity suitability, human-readable tips).
The goal is to train a service that converts raw weather numbers into short, clear,
human-friendly advice — "Rain after 4 PM — take an umbrella!" rather than "precipitation: 4 mm."

Inspired by the Yandex Shifts Weather Prediction dataset structure (tabular, multi-station,
with distributional shift across seasons and climate zones).

- **Stations**: 10 (Sivas ×3, + Kangal, Zara, Suşehri, Ankara, Kayseri, Erzincan, Malatya)
- **Time period**: January 1 – June 30, 2025 (181 days)
- **Granularity**: Hourly + daily aggregates
- **Total hourly records**: 43,440

---

### Files

#### 1. `hourly_observations.csv` — Core weather table (43,440 rows)
One row per station per hour. Contains both raw meteorological values and
pre-computed action labels (the "ground truth" for recommendation models).

| Column | Description |
|--------|-------------|
| obs_id | Unique observation ID |
| station_id / station_name | Weather station |
| climate_zone | semi-arid_continental / highland / temperate / semi-arid |
| latitude / longitude / elevation_m | Station location |
| timestamp / date / hour_of_day / month / day_of_week / is_weekend / season | Time features |
| **Meteorological** | |
| temperature_c | Air temperature (°C) |
| feels_like_c | Apparent temperature — wind chill or heat index (°C) |
| dew_point_c | Dew point (°C) |
| humidity_pct | Relative humidity (%) |
| pressure_hpa | Atmospheric pressure (hPa) |
| wind_speed_kmh | Wind speed (km/h) |
| wind_direction_deg | Wind direction (degrees) |
| wind_gust_kmh | Peak gust speed (km/h) |
| precipitation_mm | Hourly precipitation (mm) |
| precipitation_type | rain / snow / none |
| cloud_cover_pct | Cloud coverage (%) |
| visibility_km | Visibility (km) |
| uv_index | UV index (0–11+) |
| is_thunderstorm | 1 if thunderstorm activity |
| weather_condition | clear / partly_cloudy / cloudy / rain / heavy_rain / snow / heavy_snow / fog / thunderstorm / windy / hail / drizzle |
| road_surface | dry / wet / icy / snow_covered |
| **Action labels (targets)** | |
| outdoor_suitability_score | Comfort score 0–10 (10 = ideal) |
| umbrella_needed | 1 if umbrella recommended |
| clothing_recommendation | Human-readable clothing label |
| recommendation_headline | Short condition summary (e.g. "Clear skies") |
| recommendation_text | 1–3 sentence actionable advice |

#### 2. `daily_summaries.csv` — Day-level aggregates (1,810 rows)
One row per station per day. Useful for next-day forecast recommendation models.

| Column | Description |
|--------|-------------|
| summary_id | Unique daily summary ID |
| station_id / station_name / climate_zone | Station info |
| date / month / day_of_week / is_weekend / season | Date features |
| temp_min_c / temp_max_c / temp_avg_c | Daily temperature range |
| feels_like_min_c / feels_like_max_c | Apparent temperature range |
| total_precipitation_mm | Total daily rain/snow |
| snow_hours / rain_hours | Hours of snow or rain |
| max_wind_kmh / max_gust_kmh | Peak wind measurements |
| avg_humidity_pct | Mean daily humidity |
| max_uv_index | Highest UV of the day |
| dominant_condition | Most frequent weather condition |
| thunderstorm_occurred | 1 if any thunderstorm |
| avg_outdoor_suitability | Mean comfort score 0–10 |
| best_outdoor_hour | Hour with best outdoor conditions (6–21) |
| umbrella_recommended | 1 if any precipitation expected |
| clothing_morning / clothing_afternoon / clothing_evening | Recommended clothing by time of day |
| day_summary_text | One-sentence human-friendly day summary |

#### 3. `forecast_vs_actual.csv` — Forecast accuracy table (4,800 rows)
Simulates forecast vs. ground truth across different lead times (1h, 3h, 6h, 12h, 24h).
Useful for evaluating how well a model predicts actionable outputs in advance.

| Column | Description |
|--------|-------------|
| forecast_id | Unique record ID |
| station_id | Station |
| target_timestamp | The hour being predicted |
| lead_time_hours | How far in advance (1 / 3 / 6 / 12 / 24) |
| forecast_issued_at | When the forecast was made |
| forecasted_* | Predicted temperature, precip, wind, condition, umbrella, clothing |
| actual_* | Ground truth values |
| temp_error_c / precip_error_mm / wind_error_kmh | Prediction errors |
| umbrella_correct | 1 if umbrella forecast matched reality |
| clothing_correct | 1 if clothing recommendation matched |
| condition_correct | 1 if weather condition matched |

#### 4. `activity_recommendations.csv` — Activity-specific advice (3,000 rows)
Each row is a scenario: given weather + activity type, what is the recommendation?
Covers 8 activities: walking, running, cycling, driving, outdoor_work, picnic, sports, commute.

| Column | Description |
|--------|-------------|
| rec_id | Unique record ID |
| station_id / station_name / timestamp | Location and time |
| month / hour_of_day / day_of_week / is_weekend / season | Temporal context |
| weather_condition / temperature_c / feels_like_c | Core conditions |
| humidity_pct / wind_speed_kmh / precipitation_mm / cloud_cover_pct / uv_index | Full weather vector |
| activity_type | walking / running / cycling / driving / outdoor_work / picnic / sports / commute |
| general_suitability_score | Overall outdoor comfort [0–10] |
| activity_suitability_score | Activity-specific comfort [0–10] |
| umbrella_needed | 1 if umbrella recommended |
| clothing_recommendation | Clothing label |
| activity_advice | Short human-readable activity tip |
| go_or_no | 1 = go ahead, 0 = postpone/cancel |

---

### Key Dataset Statistics
| Metric | Value |
|--------|-------|
| Temperature range | -19.7°C to +31.9°C |
| Weather conditions | 11 distinct types |
| Hours needing umbrella | 20.3% |
| Stations | 10 (3 climate zones) |
| Date range | Jan–Jun 2025 |

### Clothing Categories (in order cold→hot)
`heavy_winter_coat_gloves_hat` → `winter_coat_scarf_gloves` → `warm_jacket_layers` →
`light_jacket_or_sweater` → `long_sleeves_light_layer` → `t_shirt_comfortable` →
`light_breathable_clothing` → `very_light_clothing_stay_hydrated`

---

### Suggested ML Tasks
1. **Recommendation generation** — given raw weather features, predict `recommendation_text` (NLG / LLM fine-tuning)
2. **Umbrella classification** — binary prediction of `umbrella_needed`. **Metric: F1**
3. **Suitability regression** — predict `outdoor_suitability_score` or `activity_suitability_score`. **Metric: MAE**
4. **Clothing classification** — multi-class prediction of `clothing_recommendation`. **Metric: Accuracy**
5. **Forecast quality** — use `forecast_vs_actual.csv` to evaluate `umbrella_correct` and `condition_correct` by lead time

### Evaluation Metrics (per case spec)
- Recommendation accuracy vs. actual conditions
- Text readability (NLP metrics or manual evaluation)
- User comprehension: advice must be understood within 1 second (UX criterion)
