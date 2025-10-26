# app.py

import os
import random
import datetime
import mysql.connector
from mysql.connector import Error
from flask import Flask, request, jsonify, send_file
from dotenv import load_dotenv
import requests
from PIL import Image, ImageDraw, ImageFont

# --- Initialization ---
load_dotenv()
app = Flask(__name__)

# --- Database Configuration ---
db_config = {
    'host': os.getenv('DB_HOST'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'database': os.getenv('DB_NAME')
}

def get_db_connection():
    """Establishes a connection to the MySQL database."""
    try:
        conn = mysql.connector.connect(**db_config)
        return conn
    except Error as e:
        print(f"Error connecting to MySQL Database: {e}")
        return None

def init_db():
    """Initializes the database tables if they don't exist."""
    conn = get_db_connection()
    if conn is None:
        print("Could not connect to DB, table initialization failed.")
        return
    cursor = conn.cursor()
    
    # Countries table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS countries (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(255) NOT NULL UNIQUE,
        capital VARCHAR(255),
        region VARCHAR(255),
        population INT NOT NULL,
        currency_code VARCHAR(10),
        exchange_rate FLOAT,
        estimated_gdp DOUBLE,
        flag_url VARCHAR(255),
        last_refreshed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    );
    """)
    
    # Status table to hold global app state
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS app_status (
        id INT PRIMARY KEY,
        last_refreshed_at TIMESTAMP
    );
    """)
    
    # Ensure a single row exists in app_status
    cursor.execute("INSERT IGNORE INTO app_status (id, last_refreshed_at) VALUES (1, NULL);")

    conn.commit()
    cursor.close()
    conn.close()
    print("Database initialized successfully.")

# --- Helper Functions ---
def generate_summary_image():
    """Generates a summary image with stats and saves it."""
    conn = get_db_connection()
    if not conn: return
    cursor = conn.cursor(dictionary=True)

    # Fetch data
    cursor.execute("SELECT COUNT(*) as total FROM countries;")
    total_countries = cursor.fetchone()['total']

    cursor.execute("SELECT name, estimated_gdp FROM countries ORDER BY estimated_gdp DESC LIMIT 5;")
    top_5_gdp = cursor.fetchall()
    
    cursor.execute("SELECT last_refreshed_at FROM app_status WHERE id = 1;")
    last_refreshed = cursor.fetchone()['last_refreshed_at']
    
    cursor.close()
    conn.close()

    # Create image
    img_width, img_height = 800, 600
    img = Image.new('RGB', (img_width, img_height), color='white')
    draw = ImageDraw.Draw(img)
    
    try:
        # Use a readily available font, or specify a path to a .ttf file
        font_title = ImageFont.truetype("arial.ttf", 40)
        font_text = ImageFont.truetype("arial.ttf", 20)
    except IOError:
        font_title = ImageFont.load_default()
        font_text = ImageFont.load_default()

    # Draw text
    draw.text((50, 50), "Country Data Summary", fill='black', font=font_title)
    draw.text((50, 120), f"Total Countries Cached: {total_countries}", fill='black', font=font_text)
    draw.text((50, 160), f"Last Refresh: {last_refreshed.strftime('%Y-%m-%d %H:%M:%S UTC') if last_refreshed else 'N/A'}", fill='black', font=font_text)
    
    draw.text((50, 220), "Top 5 Countries by Estimated GDP:", fill='black', font=font_text)
    y_pos = 260
    for country in top_5_gdp:
        gdp_in_billions = country['estimated_gdp'] / 1_000_000_000 if country['estimated_gdp'] else 0
        draw.text((70, y_pos), f"- {country['name']}: ${gdp_in_billions:.2f} Billion", fill='black', font=font_text)
        y_pos += 30

    # Save image
    if not os.path.exists('cache'):
        os.makedirs('cache')
    img.save('cache/summary.png')
    print("Summary image generated successfully.")

# --- API Endpoints ---

@app.route('/countries/refresh', methods=['POST'])
def refresh_countries():
    try:
        countries_res = requests.get('https://restcountries.com/v2/all?fields=name,capital,region,population,flag,currencies', timeout=10)
        countries_res.raise_for_status()
        countries_data = countries_res.json()

        rates_res = requests.get('https://open.er-api.com/v6/latest/USD', timeout=10)
        rates_res.raise_for_status()
        rates_data = rates_res.json()['rates']
    except requests.exceptions.RequestException as e:
        api_name = "restcountries.com" if "restcountries" in str(e.request.url) else "open.er-api.com"
        return jsonify({"error": "External data source unavailable", "details": f"Could not fetch data from {api_name}"}), 503

    conn = get_db_connection()
    if not conn: return jsonify({"error": "Internal server error", "details": "Could not connect to the database"}), 500
    cursor = conn.cursor()
    
    refresh_timestamp = datetime.datetime.now(datetime.timezone.utc)

    for country in countries_data:
        name = country.get('name')
        population = country.get('population')

        # Basic validation
        if not name or population is None: continue
            
        capital = country.get('capital')
        region = country.get('region')
        flag_url = country.get('flag')
        
        currency_code = None
        exchange_rate = None
        estimated_gdp = 0

        if country.get('currencies'):
            currency_code = country['currencies'][0].get('code')
            if currency_code and currency_code in rates_data:
                exchange_rate = rates_data[currency_code]
                if exchange_rate and exchange_rate > 0:
                    random_multiplier = random.randint(1000, 2000)
                    estimated_gdp = (population * random_multiplier) / exchange_rate

        # Upsert logic
        sql_check = "SELECT id FROM countries WHERE name = %s"
        cursor.execute(sql_check, (name,))
        result = cursor.fetchone()
        
        if result: # Update
            sql_upsert = """
            UPDATE countries SET capital=%s, region=%s, population=%s, currency_code=%s, exchange_rate=%s, estimated_gdp=%s, flag_url=%s
            WHERE id=%s
            """
            params = (capital, region, population, currency_code, exchange_rate, estimated_gdp, flag_url, result[0])
        else: # Insert
            sql_upsert = """
            INSERT INTO countries (name, capital, region, population, currency_code, exchange_rate, estimated_gdp, flag_url)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            params = (name, capital, region, population, currency_code, exchange_rate, estimated_gdp, flag_url)
        
        cursor.execute(sql_upsert, params)
    
    # Update global refresh timestamp
    cursor.execute("UPDATE app_status SET last_refreshed_at = %s WHERE id = 1", (refresh_timestamp,))
    
    conn.commit()
    cursor.close()
    conn.close()
    
    # Generate image after successful refresh
    generate_summary_image()
    
    return jsonify({"message": "Country data refreshed and cached successfully"}), 200

@app.route('/countries', methods=['GET'])
def get_countries():
    conn = get_db_connection()
    if not conn: return jsonify({"error": "Internal server error"}), 500
    cursor = conn.cursor(dictionary=True)

    query = "SELECT * FROM countries WHERE 1=1"
    params = []

    # Filtering
    if 'region' in request.args:
        query += " AND region = %s"
        params.append(request.args['region'])
    if 'currency' in request.args:
        query += " AND currency_code = %s"
        params.append(request.args['currency'])
    
    # Sorting
    if 'sort' in request.args:
        if request.args['sort'] == 'gdp_desc':
            query += " ORDER BY estimated_gdp DESC"
        # Can add more sorting options here
    
    cursor.execute(query, tuple(params))
    countries = cursor.fetchall()
    
    cursor.close()
    conn.close()
    return jsonify(countries)

@app.route('/countries/<name>', methods=['GET'])
def get_country_by_name(name):
    conn = get_db_connection()
    if not conn: return jsonify({"error": "Internal server error"}), 500
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT * FROM countries WHERE name = %s", (name,))
    country = cursor.fetchone()
    
    cursor.close()
    conn.close()
    
    if country:
        return jsonify(country)
    else:
        return jsonify({"error": "Country not found"}), 404

@app.route('/countries/<name>', methods=['DELETE'])
def delete_country_by_name(name):
    conn = get_db_connection()
    if not conn: return jsonify({"error": "Internal server error"}), 500
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM countries WHERE name = %s", (name,))
    
    if cursor.rowcount == 0:
        conn.close()
        return jsonify({"error": "Country not found"}), 404
    
    conn.commit()
    cursor.close()
    conn.close()
    return '', 204

@app.route('/status', methods=['GET'])
def get_status():
    conn = get_db_connection()
    if not conn: return jsonify({"error": "Internal server error"}), 500
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT COUNT(*) as total_countries FROM countries;")
    total = cursor.fetchone()['total_countries']

    cursor.execute("SELECT last_refreshed_at FROM app_status WHERE id = 1;")
    last_refresh = cursor.fetchone()['last_refreshed_at']

    cursor.close()
    conn.close()

    return jsonify({
        "total_countries": total,
        "last_refreshed_at": last_refresh
    })

@app.route('/countries/image', methods=['GET'])
def get_summary_image():
    image_path = 'cache/summary.png'
    if os.path.exists(image_path):
        return send_file(image_path, mimetype='image/png')
    else:
        return jsonify({"error": "Summary image not found"}), 404

# --- Main Execution ---
if __name__ == '__main__':
    init_db() # Run initialization on startup
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)