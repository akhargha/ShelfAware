from flask import Flask, render_template, request, jsonify
from flask_bootstrap import Bootstrap
import pytesseract
from PIL import Image
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)
Bootstrap(app)

# Sustainability Index Calculation
def calculate_sustainability_index(co2_emission, renewable_energy, waste_recycling, transport_distance):
    co2_score = max(0, 5 - co2_emission / 50)  # CO2 감점: 50tCO2 기준
    renewable_score = min(5, renewable_energy / 20)  # 재생 가능 에너지 20% 이상 최고
    recycling_score = min(5, waste_recycling / 20)  # 재활용 비율 20% 이상 최고
    transport_score = max(0, 5 - transport_distance / 500)  # 물류 거리 기준

    sustainability_score = (
        0.3 * co2_score +
        0.3 * renewable_score +
        0.2 * recycling_score +
        0.2 * transport_score
    )
    return round(min(5, sustainability_score), 2)

# Health Index Calculation
def calculate_health_index(sugar, sodium, saturated_fat, fiber, vitamins, organic, gmo_free, no_preservatives, allergen_free, calories):
    sugar_score = max(0, 5 - sugar / 10)  # 설탕
    sodium_score = max(0, 5 - sodium / 200)  # 나트륨
    fat_score = max(0, 5 - saturated_fat / 5)  # 포화지방

    fiber_score = min(5, fiber / 5)  # 식이섬유
    vitamin_score = min(5, vitamins / 20)  # 비타민

    quality_bonus = 0
    if organic: quality_bonus += 1
    if gmo_free: quality_bonus += 1
    if no_preservatives: quality_bonus += 1
    if allergen_free: quality_bonus += 1

    calorie_score = max(0, 5 - abs(calories - 350) / 150)  # 칼로리 적정 범위

    health_score = (
        0.4 * (sugar_score + sodium_score + fat_score) / 3 +
        0.3 * (fiber_score + vitamin_score) / 2 +
        0.2 * (quality_bonus / 4 * 5) +
        0.1 * calorie_score
    )
    return round(min(5, health_score), 2)

# Route for Home
@app.route('/')
def index():
    return render_template('index.html')

# Route for Sustainability Index Calculation
@app.route('/calculate_sustainability', methods=['POST'])
def calculate_sustainability():
    data = request.json
    co2_emission = data['co2_emission']
    renewable_energy = data['renewable_energy']
    waste_recycling = data['waste_recycling']
    transport_distance = data['transport_distance']
    score = calculate_sustainability_index(co2_emission, renewable_energy, waste_recycling, transport_distance)
    return jsonify({"sustainability_score": score})

# Route for Health Index Calculation
@app.route('/calculate_health', methods=['POST'])
def calculate_health():
    data = request.json
    sugar = data['sugar']
    sodium = data['sodium']
    saturated_fat = data['saturated_fat']
    fiber = data['fiber']
    vitamins = data['vitamins']
    organic = data['organic']
    gmo_free = data['gmo_free']
    no_preservatives = data['no_preservatives']
    allergen_free = data['allergen_free']
    calories = data['calories']
    score = calculate_health_index(sugar, sodium, saturated_fat, fiber, vitamins, organic, gmo_free, no_preservatives, allergen_free, calories)
    return jsonify({"health_score": score})

# OCR for Nutrition Data Extraction
@app.route('/extract_nutrition', methods=['POST'])
def extract_nutrition():
    file = request.files['image']
    img = Image.open(file)
    text = pytesseract.image_to_string(img)
    return jsonify({"extracted_text": text})

# Scraper for CO2 Emission Data
@app.route('/scrape_co2', methods=['POST'])
def scrape_co2():
    url = request.json['url']
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        co2_emission = soup.find('div', {'class': 'co2-emission'}).text.strip()
        return jsonify({"co2_emission": co2_emission})
    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == '__main__':
    app.run(debug=True)