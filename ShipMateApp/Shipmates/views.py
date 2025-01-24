from flask import Flask, render_template, request, make_response, current_app
from geopy.geocoders import Nominatim
from math import radians, cos, sin, asin, sqrt
import psycopg2
from fpdf import FPDF
from datetime import datetime
import os
import uuid
import pickle  # For saving to binary files
from Shipmates import app
import tensorflow as tf
import pandas as pd
import numpy as np
import pathlib
import glob
from sklearn.model_selection import train_test_split
from sklearn.linear_model import Ridge, LinearRegression
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import chardet
from datetime import datetime, timedelta
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import PolynomialFeatures, StandardScaler

# Database configuration
DB_CONFIG = {
    "database": "shipmates",
    "user": "postgres",
    "password": "aRiana#01",
    "host": "127.0.0.1",
    "port": "5432"
}

# Load and preprocess dataset for predictions
file_path = '/Users/hotbo/source/repos/ShipMateApp/ShipMateApp/Shipmates/static/data/deliverytime/Delivery time.csv'
data = pd.read_csv(file_path).dropna()
X = data[['Miles', 'Issue Days', 'Packages', 'Shipper preparation Days', 'Delivery loading days']]
y = data['Days']

# Split and scale the data
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# Polynomial transformation
poly_features = PolynomialFeatures(degree=1, include_bias=False)
X_train_poly = poly_features.fit_transform(X_train_scaled)
X_test_poly = poly_features.transform(X_test_scaled)

# Train Ridge regression model
ridge_model = Ridge(alpha=1.0)
ridge_model.fit(X_train_poly, y_train)

# Evaluate the model
y_train_pred = ridge_model.predict(X_train_poly)
y_test_pred = ridge_model.predict(X_test_poly)
print("Training Set - MSE: {:.4f}, MAE: {:.4f}, R2 Score: {:.4f}".format(
    mean_squared_error(y_train, y_train_pred),
    mean_absolute_error(y_train, y_train_pred),
    r2_score(y_train, y_train_pred),
))
print("Test Set - MSE: {:.4f}, MAE: {:.4f}, R2 Score: {:.4f}".format(
    mean_squared_error(y_test, y_test_pred),
    mean_absolute_error(y_test, y_test_pred),
    r2_score(y_test, y_test_pred),
))

# Constants
EARTH_RADIUS_MILES = 3959.87433
result = str(uuid.uuid4())  # Generate UUID once globally for the shipment

# Function to get shipping coordinates
def get_shipping(street, city, state, zipcode):
    geolocator = Nominatim(user_agent="geoapi")
    try:
        location = geolocator.geocode(f"{street}, {city}, {state}, {zipcode}")
        if location:
            return location.latitude, location.longitude
        else:
            return None, None
    except Exception as e:
        print(f"Geocoding error: {e}")
        return None, None

# Function to get delivery coordinates
def get_delivery(street, city, state, zipcode):
    geolocator = Nominatim(user_agent="geoapi")
    try:
        location = geolocator.geocode(f"{street}, {city}, {state}, {zipcode}")
        if location:
            return location.latitude, location.longitude
        else:
            return None, None
    except Exception as e:
        print(f"Geocoding error: {e}")
        return None, None

# Haversine formula for distance calculation
def haversine(lat1, lon1, lat2, lon2):
    d_lat = radians(lat2 - lat1)
    d_lon = radians(lon2 - lon1)
    lat1 = radians(lat1)
    lat2 = radians(lat2)
    a = sin(d_lat / 2)**2 + cos(lat1) * cos(lat2) * sin(d_lon / 2)**2
    c = 2 * asin(sqrt(a))
    return EARTH_RADIUS_MILES * c

# Function to save shipment data to the database
def save_to_database(data):
    shiplat = str(data["ship_lat"])
    shiplon = str(data["ship_lon"])
    deliverylat = str(data["delivery_lat"])
    deliverylon = str(data["delivery_lon"])
    distance = str(data["distance"])

    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # Insert shipping and delivery data
        shipper = """
        INSERT INTO shipping (
            ship_name, ship_address, ship_city, ship_state, ship_zipcode, ship_phone, id
        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        deliverer = """
        INSERT INTO deliveries (
            delivery_name, delivery_address, delivery_city, delivery_state, delivery_zipcode, delivery_phone, id
        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        tracker = """
        INSERT INTO tracking (
            ship_lat, ship_lon, delivery_lat, delivery_lon, distance, id
        ) VALUES (%s, %s, %s, %s, %s, %s)
        """

        # Insert data into the shipping and delivery tables
        cursor.execute(shipper, (
            data["shipsname"], data["shipstreet"], data["shipscity"], data["shipsstate"], 
            data["shipszipcode"], data["shipsphone"], result
        ))

        cursor.execute(deliverer, (
            data["deliverysname"], data["deliverystreet"], data["deliveryscity"], data["deliverysstate"], 
            data["deliveryszipcode"], data["deliverysphone"], result
        ))

        # Insert data into the tracking table
        cursor.execute(tracker, (
            shiplat, shiplon, deliverylat, deliverylon, distance, result
        ))

        conn.commit()
        cursor.close()
        conn.close()

        print("Data saved to database successfully.")
    except Exception as e:
        print(f"Database error: {e}")

# Function to save data to a binary file
def save_to_binary_file(data, filename):
    try:
        # Open the binary file in write mode
        with open(filename, 'wb') as file:
            # Use pickle to serialize and write data to the file
            pickle.dump(data, file)
        print(f"Data has been written to {filename}")
    except Exception as e:
        print(f"Error saving data: {e}")

# Function to generate a shipping label as a PDF
def generate_shipping_label(data):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=10)

    # Shipping Details
    pdf.cell(50, 10, txt=f"ORIGIN ID: NSFA          {data['shipsphone']}", ln=True)
    pdf.cell(50, 10, txt=f"{data['shipsname']}", ln=True)
    pdf.cell(50, 10, txt=f"{data['shipstreet']}", ln=True)
    pdf.cell(50, 10, txt=f"{data['shipscity']}, {data['shipsstate']} {data['shipszipcode']}", ln=True)
    pdf.cell(50, 10, txt=f"United States US", ln=True)
    pdf.cell(200, 10, ln=True, border = "B")
    pdf.ln(10)

    # Delivery Details
    pdf.set_font("Arial", size=20)
    pdf.cell(100, 10, txt=f"To  {data['deliverysname']}", ln=True)
    pdf.cell(100, 10, txt=f"      {data['deliverystreet']}", ln=True)
    pdf.cell(100, 10, txt=f"      {data['deliveryscity']}, {data['deliverysstate']} {data['deliveryszipcode']}", ln=True)
    pdf.set_font("Arial", size=8)
    pdf.cell(100, 10, txt=f"    {data['deliverysphone']}                   REF", ln=True)
    pdf.cell(100, 10, txt=f"    NV:", ln=True)
    pdf.cell(100, 10, txt=f"    PO:                                                     DEPT", ln=True)
    pdf.cell(200, 10, ln=True, border = "B")
    pdf.ln(10)

    # Shipping barcode
    pdf.ln(20)
    pdf.cell(200, 10, ln=True)
    image_path = os.path.join(current_app.root_path, 'static', 'assets', '9185570.png')
    image_path2 = os.path.join(current_app.root_path, 'static', 'assets', '9185914.png')
    image_path3 = os.path.join(current_app.root_path, 'static', 'assets', 'smlogo.png')
    pdf.image(image_path, x=10, y=141, w=100)
    pdf.image(image_path2, x=10, y=143, w=100, h=25)
    pdf.image(image_path3, x=140, y=155, w=25, h=25)
    pdf.cell(200, 10, ln=True, border = "B")

    # Label barcode
    pdf.ln(10)
    pdf.set_font("Arial", size=20)
    pdf.cell(200, 10, txt=f"TRK #", ln=True)
    pdf.cell(100, 10, txt=f"      {data['predicted_days']}", ln=True)
    pdf.ln(10)
    pdf.set_font("Arial", size=54)
    pdf.cell(200, 10, txt=f"1CESPA", ln=True)
    image_path4 = os.path.join(current_app.root_path, 'static', 'assets', 'deliver.png')
    pdf.image(image_path4, x=120, y=75, w=70, h=50)
    pdf.image(image_path, x=50, y=225, w=100)
    pdf.ln(30)
    pdf.set_font("Arial", size=8)
    pdf.cell(50, 10, txt=f"By accepting this package, you consent to the collection and use of your delivery address information", ln=True)
    pdf.cell(50, 10, txt=f"by Ship Mates for order fulfillment and tracking purposes, in accordance with our Privacy Policy.", ln=True)
    return pdf.output(dest="S").encode("latin1")  # Return the PDF as a byte string

# Route to create shipment and generate PDF
@app.route("/create", methods=["GET", "POST"])
def create():
    if request.method == "POST":
        # Extract shipment and delivery details from form
        data = {
            "shipsname": request.form.get("shipsname"),
            "shipstreet": request.form.get("shipstreet"),
            "shipscity": request.form.get("shipscity"),
            "shipsstate": request.form.get("shipsstate"),
            "shipszipcode": request.form.get("shipszipcode"),
            "shipsphone": request.form.get("shipsphone"),
            "deliverysname": request.form.get("deliverysname"),
            "deliverystreet": request.form.get("deliverystreet"),
            "deliveryscity": request.form.get("deliveryscity"),
            "deliverysstate": request.form.get("deliverysstate"),
            "deliveryszipcode": request.form.get("deliveryszipcode"),
            "deliverysphone": request.form.get("deliverysphone"),
            "packagecount": request.form.get("packagecount")
        }

        # Get coordinates for shipping and delivery addresses
        ship_lat, ship_lon = get_shipping(data["shipstreet"], data["shipscity"], data["shipsstate"], data["shipszipcode"])
        delivery_lat, delivery_lon = get_delivery(data["deliverystreet"], data["deliveryscity"], data["deliverysstate"], data["deliveryszipcode"])

        if ship_lat is None or delivery_lat is None:
            return render_template("create.html", title="Create", error="Address could not be geocoded.")

        # Calculate distance and save data
        distance = haversine(ship_lat, ship_lon, delivery_lat, delivery_lon)
        data["distance"] = round(distance, 2)
        data["ship_lat"] = ship_lat
        data["ship_lon"] = ship_lon
        data["delivery_lat"] = delivery_lat
        data["delivery_lon"] = delivery_lon

        # Predict delivery days
        new_input = pd.DataFrame([{
            'Miles': data['distance'],
            'Issue Days': 0,
            'Packages': data['packagecount'],
            'Shipper preparation Days': 1,
            'Delivery loading days': 1,
        }])
        new_input_scaled = scaler.transform(new_input)
        new_input_poly = poly_features.transform(new_input_scaled)
        data['predicted_days'] = ridge_model.predict(new_input_poly)[0]

        save_to_database(data)

        # Save data to a binary file
        save_to_binary_file(data, 'shipment_data.dat')

        # Generate and return the shipping label as a PDF
        pdf_data = generate_shipping_label(data)
        response = make_response(pdf_data)
        response.headers["Content-Type"] = "application/pdf"
        response.headers["Content-Disposition"] = "inline; filename=shipping_label.pdf"
        return response

    return render_template("create.html", title="Create")
