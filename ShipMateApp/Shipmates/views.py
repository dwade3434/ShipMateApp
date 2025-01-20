from flask import Flask, render_template, request, make_response, current_app
from geopy.geocoders import Nominatim
from math import radians, cos, sin, asin, sqrt
import psycopg2
from fpdf import FPDF
from datetime import datetime
import os
import uuid
from Shipmates import app

# Database configuration
DB_CONFIG = {
    "database": "shipmates",
    "user": "postgres",
    "password": "aRiana#01",
    "host": "127.0.0.1",
    "port": "5432"
}

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

# Function to save shipment data to the database and return the tracking number
def save_to_database(data):
    shiplat = str(data["ship_lat"])
    shiplon = str(data["ship_lon"])
    deliverylat = str(data["delivery_lat"])
    deliverylon = str(data["delivery_lon"])
    distance = str(data["distance"])

    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # Insert into shipping and delivery tables
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
        ) VALUES (%s, %s, %s, %s, %s, %s) RETURNING tracking_number
        """  # Return the generated tracking number

        # Insert into shipping and delivery tables
        cursor.execute(shipper, (
            data["shipsname"], data["shipstreet"], data["shipscity"], data["shipsstate"], 
            data["shipszipcode"], data["shipsphone"], result
        ))

        cursor.execute(deliverer, (
            data["deliverysname"], data["deliverystreet"], data["deliveryscity"], data["deliverysstate"], 
            data["deliveryszipcode"], data["deliverysphone"], result
        ))

        # Insert into the tracking table and get the tracking number
        cursor.execute(tracker, (
            shiplat, shiplon, deliverylat, deliverylon, distance, result
        ))

        # Fetch the tracking ID (tracking number)
        tracking_number = cursor.fetchone()[0]  # Get the first column from the result

        conn.commit()
        cursor.close()
        conn.close()

        print("Data saved to database successfully.")
        return tracking_number  # Return the tracking number
    except Exception as e:
        print(f"Database error: {e}")
        return None

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
    pdf.cell(200, 10, ln=True, border="B")
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
    pdf.cell(200, 10, ln=True, border="B")
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
    pdf.cell(200, 10, ln=True, border="B")

    # Label barcode
    pdf.ln(10)
    pdf.set_font("Arial", size=20)
    pdf.cell(200, 10, txt=f"TRK # {data['tracking_number']}", ln=True)
    pdf.ln(10)
    pdf.set_font("Arial", size=54)
    pdf.cell(200, 10, txt=f"1CN9NA", ln=True)
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
            "deliverysphone": request.form.get("deliverysphone")
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

        # Save data to database and get the tracking number
        tracking_number = save_to_database(data)

        if not tracking_number:
            return render_template("create.html", title="Create", error="Failed to generate tracking number.")

        # Add tracking number to data dictionary
        data["tracking_number"] = tracking_number

        # Generate and return the shipping label as a PDF
        pdf_data = generate_shipping_label(data)
        response = make_response(pdf_data)
        response.headers["Content-Type"] = "application/pdf"
        response.headers["Content-Disposition"] = "inline; filename=shipping_label.pdf"
        return response

    return render_template("create.html", title="Create")
