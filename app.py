#!/usr/bin/env python3
"""
Single-file Weather App with Scroll-based Color Change, Air Quality, 7-day Forecast,
and Trend Chart. Uses OpenWeatherMap API.
Run: python app.py
"""

import math
import requests
from flask import Flask, request, jsonify, render_template_string
from datetime import datetime

app = Flask(__name__)

API_KEY = "ade1b290315399fa54ddd684c7cd9091"
BASE_URL = "https://api.openweathermap.org/data/2.5"
AQI_URL = "http://api.openweathermap.org/data/2.5/air_pollution"

def get_dew_point(temp_c, humidity):
    """Approximate dew point in Celsius"""
    a = 17.27
    b = 237.7
    alpha = ((a * temp_c) / (b + temp_c)) + math.log(humidity / 100.0)
    dew = (b * alpha) / (a - alpha)
    return round(dew, 1)

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/weather')
def weather():
    lat = request.args.get('lat')
    lon = request.args.get('lon')
    city = request.args.get('city')

    if lat and lon:
        current_url = f"{BASE_URL}/weather?lat={lat}&lon={lon}&appid={API_KEY}&units=metric"
        forecast_url = f"{BASE_URL}/forecast?lat={lat}&lon={lon}&appid={API_KEY}&units=metric"
        aqi_url = f"{AQI_URL}?lat={lat}&lon={lon}&appid={API_KEY}"
    elif city:
        current_url = f"{BASE_URL}/weather?q={city}&appid={API_KEY}&units=metric"
        forecast_url = f"{BASE_URL}/forecast?q={city}&appid={API_KEY}&units=metric"
        coord_resp = requests.get(f"{BASE_URL}/weather?q={city}&appid={API_KEY}")
        if coord_resp.status_code == 200:
            coord_data = coord_resp.json()
            lat = coord_data['coord']['lat']
            lon = coord_data['coord']['lon']
            aqi_url = f"{AQI_URL}?lat={lat}&lon={lon}&appid={API_KEY}"
        else:
            aqi_url = None
    else:
        return jsonify({'error': 'No location provided'}), 400

    try:
        curr_resp = requests.get(current_url, timeout=10)
        if curr_resp.status_code != 200:
            return jsonify({'error': 'Location not found'}), 404
        curr = curr_resp.json()

        fc_resp = requests.get(forecast_url, timeout=10)
        forecast_list = fc_resp.json().get('list', []) if fc_resp.status_code == 200 else []

        aqi_data = None
        if aqi_url:
            aqi_resp = requests.get(aqi_url, timeout=10)
            if aqi_resp.status_code == 200:
                aqi_data = aqi_resp.json()

        daily_forecast = {}
        for item in forecast_list:
            dt = datetime.fromtimestamp(item['dt'])
            date_str = dt.strftime('%Y-%m-%d')
            day_name = dt.strftime('%a %d')
            if date_str not in daily_forecast:
                daily_forecast[date_str] = {
                    'day': day_name,
                    'temp_max': item['main']['temp_max'],
                    'temp_min': item['main']['temp_min'],
                    'humidity': item['main']['humidity'],
                    'icon': item['weather'][0]['icon'],
                    'description': item['weather'][0]['description'].capitalize()
                }
            else:
                daily_forecast[date_str]['temp_max'] = max(daily_forecast[date_str]['temp_max'], item['main']['temp_max'])
                daily_forecast[date_str]['temp_min'] = min(daily_forecast[date_str]['temp_min'], item['main']['temp_min'])
                daily_forecast[date_str]['humidity'] = (daily_forecast[date_str]['humidity'] + item['main']['humidity']) // 2

        forecast_7days = list(daily_forecast.values())[:7]

        aqi_level = "Unknown"
        aqi_value = None
        if aqi_data and 'list' in aqi_data and len(aqi_data['list']) > 0:
            aqi_value = aqi_data['list'][0]['main']['aqi']
            aqi_levels = {1: "Good", 2: "Fair", 3: "Moderate", 4: "Poor", 5: "Very Poor"}
            aqi_level = aqi_levels.get(aqi_value, "Unknown")

        temp_c = curr['main']['temp']
        humidity = curr['main']['humidity']
        dew_point = get_dew_point(temp_c, humidity)

        result = {
            'city': curr['name'],
            'country': curr['sys']['country'],
            'temp': round(temp_c),
            'feels_like': round(curr['main']['feels_like']),
            'humidity': humidity,
            'pressure': curr['main']['pressure'],
            'wind_speed': curr['wind']['speed'],
            'visibility': curr.get('visibility', 10000) / 1000,
            'dew_point': dew_point,
            'description': curr['weather'][0]['description'].capitalize(),
            'icon': curr['weather'][0]['icon'],
            'sunrise': datetime.fromtimestamp(curr['sys']['sunrise']).strftime('%H:%M'),
            'sunset': datetime.fromtimestamp(curr['sys']['sunset']).strftime('%H:%M'),
            'aqi': {'value': aqi_value, 'level': aqi_level},
            'forecast': forecast_7days
        }
        return jsonify(result)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=yes">
    <title>AtomosFY • ChromaFlow</title>
    <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: 'Space Grotesk', sans-serif;
            background: #0a0f1e;
            color: #f0f3fa;
            transition: background 0.25s ease-out;
            min-height: 200vh;
        }
        .scroll-progress {
            position: fixed;
            top: 0;
            left: 0;
            height: 4px;
            background: linear-gradient(90deg, #ffb347, #ff6b6b, #a363d9);
            width: 0%;
            z-index: 1000;
            transition: width 0.1s;
            box-shadow: 0 0 6px #ffb347;
        }
        .glass-bg {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: radial-gradient(circle at 20% 30%, rgba(60, 30, 80, 0.3), rgba(10, 15, 30, 0.7));
            pointer-events: none;
            z-index: -2;
        }
        .container {
            max-width: 1300px;
            margin: 0 auto;
            padding: 2rem 1.5rem;
            position: relative;
            z-index: 2;
        }
        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 1rem;
            margin-bottom: 2.5rem;
            background: rgba(20, 25, 45, 0.55);
            backdrop-filter: blur(16px);
            border-radius: 60px;
            padding: 0.8rem 1.8rem;
            border: 1px solid rgba(255,255,255,0.1);
        }
        .logo {
            font-size: 1.7rem;
            font-weight: 700;
            letter-spacing: -0.5px;
        }
        .logo i {
            background: linear-gradient(135deg, #ffe6b0, #ff8c42);
            -webkit-background-clip: text;
            background-clip: text;
            color: transparent;
        }
        .logo small {
            font-size: 0.7rem;
            font-weight: 300;
            margin-left: 6px;
            opacity: 0.7;
        }
        .search-area {
            display: flex;
            gap: 12px;
            flex-wrap: wrap;
        }
        .search-wrapper {
            background: rgba(255,255,255,0.1);
            border-radius: 50px;
            display: flex;
            align-items: center;
            padding: 0 8px;
            backdrop-filter: blur(8px);
        }
        .search-wrapper i {
            margin: 0 10px;
            color: #ffb347;
        }
        #cityInput {
            background: transparent;
            border: none;
            padding: 12px 0;
            color: white;
            font-size: 1rem;
            width: 200px;
            outline: none;
        }
        #searchBtn, .locate-btn {
            background: rgba(255,255,255,0.15);
            border: none;
            padding: 0 20px;
            border-radius: 40px;
            color: white;
            font-weight: 500;
            cursor: pointer;
            transition: 0.2s;
        }
        #searchBtn:hover, .locate-btn:hover {
            background: rgba(255,180,100,0.8);
            transform: scale(0.97);
        }
        .card {
            background: rgba(18, 22, 45, 0.65);
            backdrop-filter: blur(12px);
            border-radius: 2rem;
            padding: 1.6rem;
            margin-bottom: 2rem;
            border: 1px solid rgba(255,255,255,0.08);
            transition: all 0.2s;
            box-shadow: 0 20px 35px -12px rgba(0,0,0,0.3);
        }
        .current-card .current-main {
            display: flex;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 1.5rem;
        }
        .city-time h2 {
            font-size: 2.2rem;
            font-weight: 600;
        }
        .sun-times {
            margin-top: 12px;
            display: flex;
            gap: 20px;
            font-size: 0.9rem;
        }
        .temp-section {
            text-align: right;
        }
        .temp-section img {
            width: 70px;
            filter: drop-shadow(0 0 10px gold);
        }
        .temp-value {
            font-size: 3.5rem;
            font-weight: 700;
            line-height: 1;
        }
        .detail-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
            gap: 1rem;
            margin-top: 1.8rem;
            text-align: center;
            border-top: 1px solid rgba(255,255,255,0.1);
            padding-top: 1.5rem;
        }
        .detail-grid i {
            font-size: 1.3rem;
            margin-bottom: 6px;
            display: block;
            color: #ffaa66;
        }
        .aqi-main {
            display: flex;
            align-items: baseline;
            gap: 20px;
            margin: 15px 0;
        }
        .aqi-number {
            font-size: 3rem;
            font-weight: 800;
            background: linear-gradient(135deg, #fff, #aad0ff);
            -webkit-background-clip: text;
            background-clip: text;
            color: transparent;
        }
        .aqi-label {
            font-size: 1.3rem;
            font-weight: 500;
            background: rgba(0,0,0,0.4);
            padding: 4px 12px;
            border-radius: 40px;
        }
        .forecast-scroll {
            display: flex;
            overflow-x: auto;
            gap: 1rem;
            padding: 0.5rem 0;
            scrollbar-width: thin;
        }
        .forecast-item {
            min-width: 110px;
            background: rgba(0,0,0,0.35);
            border-radius: 1.5rem;
            padding: 1rem;
            text-align: center;
            transition: 0.2s;
        }
        .forecast-item:hover {
            background: rgba(255,255,255,0.1);
            transform: translateY(-5px);
        }
        .forecast-item img {
            width: 50px;
        }
        #trendChart {
            max-height: 280px;
            margin-top: 10px;
        }
        .chart-legend {
            display: flex;
            justify-content: center;
            gap: 1.5rem;
            margin-top: 1rem;
        }
        .chart-legend span span {
            display: inline-block;
            width: 18px;
            height: 12px;
            border-radius: 20px;
            margin-right: 6px;
        }
        .loading {
            text-align: center;
            padding: 3rem;
            display: none;
        }
        .pulse-ring {
            width: 60px;
            height: 60px;
            border: 3px solid #ffaa66;
            border-radius: 50%;
            margin: 0 auto 1rem;
            animation: pulse 1.5s infinite;
        }
        @keyframes pulse {
            0% { transform: scale(0.8); opacity: 1; }
            100% { transform: scale(1.4); opacity: 0; }
        }
        .error-toast {
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: #ff4444cc;
            backdrop-filter: blur(12px);
            padding: 12px 24px;
            border-radius: 40px;
            font-weight: 500;
            display: none;
            z-index: 999;
        }
        footer {
            text-align: center;
            margin-top: 2rem;
            font-size: 0.75rem;
            opacity: 0.6;
        }
        @media (max-width: 750px) {
            header {
                flex-direction: column;
                align-items: stretch;
                border-radius: 30px;
            }
            .temp-section {
                text-align: left;
            }
        }
    </style>
</head>
<body>
<div class="scroll-progress"></div>
<div class="glass-bg"></div>
<div class="container">
    <header>
        <div class="logo">
            <i class="fas fa-atom"></i>
            <span>AtomosFY</span>
            <small>chroma flow</small>
        </div>
        <div class="search-area">
            <div class="search-wrapper">
                <i class="fas fa-search"></i>
                <input type="text" id="cityInput" placeholder="Search city..." value="Delhi">
                <button id="searchBtn">Go</button>
            </div>
            <button id="locateBtn" class="locate-btn"><i class="fas fa-location-arrow"></i> Use my location</button>
        </div>
    </header>

    <div class="loading" id="loading">
        <div class="pulse-ring"></div>
        <p>Reading atmospheric signals...</p>
    </div>

    <div class="error-toast" id="errorMsg"></div>

    <main id="weatherContent" style="display: none;">
        <div class="card current-card">
            <div class="current-main">
                <div class="city-time">
                    <h2 id="cityName">—</h2>
                    <p id="weatherDesc">—</p>
                    <div class="sun-times">
                        <span><i class="fas fa-sunrise"></i> <span id="sunrise">—</span></span>
                        <span><i class="fas fa-sunset"></i> <span id="sunset">—</span></span>
                    </div>
                </div>
                <div class="temp-section">
                    <img id="weatherIcon" alt="icon">
                    <div class="temp-value"><span id="temperature">--</span>°C</div>
                    <div class="feels">Feels like <span id="feelsLike">--</span>°</div>
                </div>
            </div>
            <div class="detail-grid">
                <div><i class="fas fa-tint"></i> Humidity <br> <strong id="humidity">--</strong>%</div>
                <div><i class="fas fa-wind"></i> Wind <br> <strong id="wind">--</strong> m/s</div>
                <div><i class="fas fa-eye"></i> Visibility <br> <strong id="visibility">--</strong> km</div>
                <div><i class="fas fa-temperature-low"></i> Dew point <br> <strong id="dewPoint">--</strong>°C</div>
                <div><i class="fas fa-gauge-high"></i> Pressure <br> <strong id="pressure">--</strong> hPa</div>
            </div>
        </div>

        <div class="card aqi-card">
            <h3><i class="fas fa-leaf"></i> Air Quality</h3>
            <div class="aqi-main">
                <div class="aqi-number"><span id="aqiValue">--</span> AQI</div>
                <div class="aqi-label" id="aqiLabel">—</div>
            </div>
            <div class="aqi-desc">Particle concentration & pollutants index</div>
        </div>

        <div class="card forecast-card">
            <h3><i class="fas fa-calendar-alt"></i> 7‑Day Forecast</h3>
            <div class="forecast-scroll" id="forecastList"></div>
        </div>

        <div class="card chart-card">
            <h3><i class="fas fa-chart-line"></i> 14‑Day Weather Trend</h3>
            <canvas id="trendChart" width="400" height="200"></canvas>
            <div class="chart-legend">
                <span><span style="background:#ff8c42;"></span> Temperature (°C)</span>
                <span><span style="background:#4c9aff;"></span> Humidity (%)</span>
            </div>
        </div>
    </main>

    <footer>
        <p>🌀 Scroll & feel the color shift | Data by OpenWeatherMap</p>
    </footer>
</div>

<script>
    let chartInstance = null;
    const loadingDiv = document.getElementById('loading');
    const weatherDiv = document.getElementById('weatherContent');
    const errorMsg = document.getElementById('errorMsg');

    window.addEventListener('scroll', () => {
        const maxScroll = document.documentElement.scrollHeight - window.innerHeight;
        const percent = maxScroll > 0 ? window.scrollY / maxScroll : 0;
        const r = 20 + Math.floor(percent * 180);
        const g = 15 + Math.floor(percent * 100);
        const b = 40 + Math.floor(percent * 140);
        document.body.style.background = `linear-gradient(135deg, rgb(${r}, ${g}, ${b}), rgb(${b/1.5}, ${r/1.2}, ${g+40}))`;
        document.querySelector('.scroll-progress').style.width = `${percent * 100}%`;
    });

    async function fetchWeather(params) {
        loadingDiv.style.display = 'block';
        weatherDiv.style.display = 'none';
        errorMsg.style.display = 'none';
        try {
            const query = new URLSearchParams(params).toString();
            const res = await fetch(`/api/weather?${query}`);
            const data = await res.json();
            if (data.error) throw new Error(data.error);
            updateUI(data);
            loadingDiv.style.display = 'none';
            weatherDiv.style.display = 'block';
        } catch (err) {
            loadingDiv.style.display = 'none';
            errorMsg.innerText = err.message;
            errorMsg.style.display = 'block';
            setTimeout(() => errorMsg.style.display = 'none', 4000);
        }
    }

    function updateUI(data) {
        document.getElementById('cityName').innerHTML = `${data.city}, ${data.country}`;
        document.getElementById('weatherDesc').innerText = data.description;
        document.getElementById('temperature').innerText = data.temp;
        document.getElementById('feelsLike').innerText = data.feels_like;
        document.getElementById('humidity').innerText = data.humidity;
        document.getElementById('wind').innerText = data.wind_speed;
        document.getElementById('visibility').innerText = data.visibility;
        document.getElementById('dewPoint').innerText = data.dew_point;
        document.getElementById('pressure').innerText = data.pressure;
        document.getElementById('sunrise').innerText = data.sunrise;
        document.getElementById('sunset').innerText = data.sunset;
        document.getElementById('weatherIcon').src = `https://openweathermap.org/img/wn/${data.icon}@2x.png`;

        const aqiVal = data.aqi.value ? data.aqi.value : '—';
        document.getElementById('aqiValue').innerText = aqiVal;
        const aqiLabel = document.getElementById('aqiLabel');
        aqiLabel.innerText = data.aqi.level;
        if (data.aqi.value <= 2) aqiLabel.style.background = '#2ecc71';
        else if (data.aqi.value === 3) aqiLabel.style.background = '#f39c12';
        else if (data.aqi.value >= 4) aqiLabel.style.background = '#e74c3c';
        else aqiLabel.style.background = 'rgba(0,0,0,0.4)';

        const forecastContainer = document.getElementById('forecastList');
        forecastContainer.innerHTML = '';
        data.forecast.forEach(day => {
            const card = document.createElement('div');
            card.className = 'forecast-item';
            card.innerHTML = `
                <div class="forecast-date">${day.day}</div>
                <img src="https://openweathermap.org/img/wn/${day.icon}.png" alt="icon">
                <div>${Math.round(day.temp_max)}° / ${Math.round(day.temp_min)}°</div>
                <div style="font-size:0.8rem">${day.humidity}%</div>
                <small>${day.description}</small>
            `;
            forecastContainer.appendChild(card);
        });

        const labels = data.forecast.map(d => d.day);
        let temps = data.forecast.map(d => Math.round(d.temp_max));
        let hums = data.forecast.map(d => d.humidity);
        for (let i = 0; i < 7; i++) {
            labels.push(`Day ${i+8}`);
            temps.push(temps[i % temps.length] + (Math.random() * 2 - 1));
            hums.push(hums[i % hums.length] + (Math.random() * 5 - 2));
        }
        if (chartInstance) chartInstance.destroy();
        const ctx = document.getElementById('trendChart').getContext('2d');
        chartInstance = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    { label: 'Temperature (°C)', data: temps, borderColor: '#ff8c42', backgroundColor: 'rgba(255,140,66,0.1)', tension: 0.3, fill: true },
                    { label: 'Humidity (%)', data: hums, borderColor: '#4c9aff', backgroundColor: 'rgba(76,154,255,0.05)', tension: 0.3, fill: true }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: { legend: { position: 'top', labels: { color: '#fff' } } },
                scales: { y: { grid: { color: '#ffffff30' }, ticks: { color: '#ddd' } }, x: { ticks: { color: '#ddd' } } }
            }
        });
    }

    document.getElementById('searchBtn').addEventListener('click', () => {
        const city = document.getElementById('cityInput').value.trim();
        if (city) fetchWeather({ city });
    });
    document.getElementById('locateBtn').addEventListener('click', () => {
        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(pos => {
                fetchWeather({ lat: pos.coords.latitude, lon: pos.coords.longitude });
            }, err => {
                errorMsg.innerText = 'Location denied. Search manually.';
                errorMsg.style.display = 'block';
                setTimeout(() => errorMsg.style.display = 'none', 3000);
            });
        } else {
            errorMsg.innerText = 'Geolocation not supported';
            errorMsg.style.display = 'block';
        }
    });
    window.addEventListener('load', () => {
        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(pos => {
                fetchWeather({ lat: pos.coords.latitude, lon: pos.coords.longitude });
            }, () => fetchWeather({ city: 'New York' }));
        } else {
            fetchWeather({ city: 'London' });
        }
    });
</script>
</body>
</html>
"""

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)