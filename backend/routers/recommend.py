from fastapi import APIRouter, HTTPException
from services.weather import fetch_current_weather
from services.normalizer import normalize_to_model_features
from services.predictor import predictor

router = APIRouter(prefix="/recommend")

# تعديل بسيط هنا: الدالة بقت بتاخد "جزء" البيانات (سواء الحالي أو بتاع ساعة معينة)
def _weather_effect(data_slice: dict) -> str:
    code = data_slice.get("weather_code", 0)
    precip = data_slice.get("precipitation", 0)
    temp   = data_slice.get("temperature_2m", 20)
    
    if code in range(95, 100): return "thunder"
    if code in range(71, 78):  return "snow"
    if precip > 2:             return "heavy-rain"
    if precip > 0:             return "rain"
    if temp < 0:               return "snow"
    if data_slice.get("cloud_cover", 0) > 70: return "clouds"
    return "clear"

@router.get("/")
async def get_recommendation(city: str):
    if not city or not city.strip():
        raise HTTPException(status_code=400, detail="City parameter is required")

    # 1. جلب البيانات (الحالية + 24 ساعة)
    weather_data = fetch_current_weather(city)
    
    # 2. معالجة الطقس الحالي (Current)
    current_raw = weather_data["current_raw"]
    current_features = normalize_to_model_features(current_raw, weather_data["utc_offset"])
    current_result = predictor.predict(current_features)
    current_effect = _weather_effect(current_raw)

    # 3. دورة المعالجة لـ 24 ساعة (The ML Loop)
    hourly_forecast = []
    hourly_raw = weather_data["hourly_raw"]
    
    # الـ API بيرجع 24 عنصر، هنلف عليهم واحد واحد
    for i in range(24):
        # بناء قاموس صغير لكل ساعة كأنها "حالة طقس مستقلة"
        hour_data = {
            "time": hourly_raw["time"][i],
            "temperature_2m": hourly_raw["temperature_2m"][i],
            "relative_humidity_2m": hourly_raw["relative_humidity_2m"][i],
            "precipitation": hourly_raw["precipitation"][i],
            "wind_speed_10m": hourly_raw["wind_speed_10m"][i],
            "cloud_cover": hourly_raw["cloud_cover"][i],
            "weather_code": hourly_raw["weather_code"][i],
        }
        
        # تمرير الساعة للـ Normalizer ثم للموديل
        h_features = normalize_to_model_features(hour_data, weather_data["utc_offset"])
        h_result = predictor.predict(h_features)
        h_effect = _weather_effect(hour_data)
        
        # تخزين النتيجة للساعة دي
        hourly_forecast.append({
            "time": hour_data["time"],
            "temperature": h_features["temperature"],
            "weather_effect": h_effect,  # عشان مايار تغير الأيقونة لكل ساعة
            "umbrella_needed": h_result["umbrella_needed"],
            "clothing_recommendation": h_result["clothing_recommendation"],
            "suitability_score": h_result["suitability_score"],
            "go_or_no": h_result["go_or_no"]
        })

    # 4. الـ Master JSON (المنتج النهائي للفرونت-إند)
    return {
        "location": {
            "city": weather_data["location"], 
            "country": weather_data["country"],
            "utc_offset": weather_data["utc_offset"], 
            "timezone": weather_data["timezone"]
        },
        "current": {
            "temperature": current_features["temperature"],
            "weather_effect": current_effect,
            "umbrella_needed": current_result["umbrella_needed"],
            "clothing_recommendation": current_result["clothing_recommendation"],
            "suitability_score": current_result["suitability_score"],
            "go_or_no": current_result["go_or_no"],
            "mode": current_result["mode"],
            "hour_local": current_features["hour_of_day"]
        },
        "forecast_24h": hourly_forecast  # دي المصفوفة اللي فيها الساعات كلها
        # مكانه هنا هيكون الـ RAG/AI Advice في الخطوة الجاية
    }