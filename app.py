import streamlit as st
import pandas as pd
import googlemaps
import plotly.graph_objs as go
from io import StringIO
import time
import os
import tempfile
import json
import matplotlib.pyplot as plt

st.title("Event Location Planner")

st.subheader("Plan your events efficiently with optimal locations 🌍🎉")
st.markdown("""
This tool helps you to find the best locations for your events based on travel time, cost, and emissions. 
Upload a CSV file with attendee postcodes, configure your cost and emission parameters, and get the top location recommendations for hosting your event.
""")

# Sidebar for settings and inputs
st.sidebar.header("⚙️ Settings")

api_key = st.sidebar.text_input("Google API Key", type="password")

st.sidebar.markdown("**💸 Budget**")
budget_type = st.sidebar.radio("", ["Total Budget for the Event", "Average Budget per Attendee"])

if budget_type == "Total Budget for the Event":
    budget_cost = st.sidebar.number_input("Total Budget for Costs (£)", value=1000)
    budget_time = st.sidebar.number_input("Total Budget for Time (minutes)", value=120)
    budget_emissions = st.sidebar.number_input("Total Budget for Emissions (kg CO2)", value=200)
else:
    budget_cost = st.sidebar.number_input("Average Budget for Costs per Attendee (£)", value=100)
    budget_time = st.sidebar.number_input("Average Budget for Time per Attendee (minutes)", value=15)
    budget_emissions = st.sidebar.number_input("Average Budget for Emissions per Attendee (kg CO2)", value=20)

# Cost and Emissions Lookup Table for Different Travel Modes
st.sidebar.subheader("💡 Cost and Emissions Lookup Table")
cost_per_km_car = st.sidebar.number_input("Cost per km by Car (£)", value=0.5)
emission_per_km_car = st.sidebar.number_input("Emissions per km by Car (kg CO2)", value=0.2)
cost_per_km_train = st.sidebar.number_input("Cost per km by Train (£)", value=0.3)
emission_per_km_train = st.sidebar.number_input("Emissions per km by Train (kg CO2)", value=0.1)

# Potential Base Locations Input
st.sidebar.subheader("📍 Potential Base Locations")
base_locations = st.sidebar.text_area("Enter base locations (one per line)")

# Upload Attendee Postcodes
st.subheader("Upload Attendee Postcodes CSV")
uploaded_file = st.file_uploader("Choose a CSV file", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    if 'postcode' not in df.columns:
        st.error("The uploaded CSV file must contain a 'postcode' column.")
    else:
        st.write("Attendee Postcodes:", df)

# Function to validate and format locations
def validate_location(api_key, location):
    gmaps = googlemaps.Client(key=api_key)
    try:
        result = gmaps.geocode(location)
        if result:
            formatted_address = result[0]['formatted_address']
            if 'UK' in formatted_address or 'United Kingdom' in formatted_address:  # Only accept UK locations
                return formatted_address
            else:
                return None
        else:
            return None
    except Exception as e:
        return None

# Function to calculate distances using Google Routes API
def calculate_distances(api_key, origins, destinations, travel_mode):
    gmaps = googlemaps.Client(key=api_key)
    distances = {}
    times = {}
    for origin in origins:
        distances[origin] = {}
        times[origin] = {}
        for destination in destinations:
            try:
                result = gmaps.directions(origin, destination, mode=travel_mode)
                if result and result[0]['legs']:
                    distance = result[0]['legs'][0]['distance']['value'] / 1000  # in km
                    time = result[0]['legs'][0]['duration']['value'] / 60  # in minutes
                    distances[origin][destination] = distance
                    times[origin][destination] = time
                else:
                    distances[origin][destination] = float('inf')
                    times[origin][destination] = float('inf')
            except Exception as e:
                distances[origin][destination] = float('inf')
                times[origin][destination] = float('inf')
    return distances, times

# Function to choose travel mode based on conditions
def choose_travel_mode(api_key, origin, destination, cost_per_km_car, emission_per_km_car, cost_per_km_train, emission_per_km_train):
    car_distances, car_times = calculate_distances(api_key, [origin], [destination], 'driving')
    train_distances, train_times = calculate_distances(api_key, [origin], [destination], 'transit')
    
    car_time = car_times[origin][destination]
    train_time = train_times[origin][destination]

    if car_time == float('inf') and train_time == float('inf'):
        return 'transit'  # Default to train if both are unavailable
    if car_time == float('inf'):
        return 'transit'
    if train_time == float('inf'):
        return 'driving'
    if train_time > 1.5 * car_time:
        return 'driving'
    return 'transit'

# Function to extract city names from postcodes
def extract_city_names(api_key, postcodes):
    gmaps = googlemaps.Client(key=api_key)
    cities = []
    for postcode in postcodes:
        try:
            result = gmaps.geocode(postcode)
            if result:
                address_components = result[0]['address_components']
                for component in address_components:
                    if 'locality' in component['types']:
                        cities.append(component['long_name'])
                        break  # Stop after finding the first locality component
        except Exception as e:
            continue
    return list(set(cities))  # Return unique city names

# Function to generate recommendations
def generate_recommendations(df, base_locations, cost_per_km_car, emission_per_km_car, cost_per_km_train, emission_per_km_train, budget_cost, budget_time, budget_emissions, budget_type):
    origins = df['postcode'].tolist()
    valid_origins = [validate_location(api_key, origin) for origin in origins]
    valid_origins = [origin for origin in valid_origins if origin is not None]
    num_attendees = len(valid_origins)
    invalid_attendees = len(origins) - num_attendees

    if not base_locations.strip():
        # Extract unique city names from the attendee postcodes
        unique_cities = extract_city_names(api_key, valid_origins)
        destinations = unique_cities
    else:
        destinations = base_locations.split('\n')
    
    valid_destinations = [validate_location(api_key, destination) for destination in destinations]
    valid_destinations = [destination for destination in valid_destinations if destination is not None]
    invalid_destinations = len(destinations) - len(valid_destinations)

    results = []
    for location in valid_destinations:
        total_cost = 0
        total_emissions = 0
        total_time = 0
        for origin in valid_origins:
            travel_mode = choose_travel_mode(api_key, origin, location, cost_per_km_car, emission_per_km_car, cost_per_km_train, emission_per_km_train)
            if travel_mode == 'driving':
                cost_per_km = cost_per_km_car
                emission_per_km = emission_per_km_car
            else:
                cost_per_km = cost_per_km_train
                emission_per_km = emission_per_km_train
            
            distances, times = calculate_distances(api_key, [origin], [location], travel_mode)
            distance = distances[origin][location]
            time = times[origin][location]
            
            if distance == float('inf') or time == float('inf'):
                continue

            total_cost += distance * cost_per_km
            total_emissions += distance * emission_per_km
            total_time += time
        
        if num_attendees == 0:
            avg_cost_per_attendee = 0
            avg_emissions_per_attendee = 0
            avg_time_per_attendee = 0
        else:
            avg_cost_per_attendee = total_cost / num_attendees
            avg_emissions_per_attendee = total_emissions / num_attendees
            avg_time_per_attendee = total_time / num_attendees
        
        total_time_hours, total_time_minutes = divmod(total_time, 60)
        
        results.append({
            "Location": location.split(",")[0],  # Extracting city name
            "Avg Cost per Attendee (£)": int(avg_cost_per_attendee),
            "Avg Emissions per Attendee (kg CO2)": int(avg_emissions_per_attendee),
            "Avg Time per Attendee": f"{int(avg_time_per_attendee // 60)}h {int(avg_time_per_attendee % 60)}m",
            "Total Cost (£)": int(total_cost),
            "Total Emissions (kg CO2)": int(total_emissions),
            "Total Time": f"{int(total_time_hours)}h {int(total_time_minutes)}m"
        })
    
        results = sorted(results, key=lambda x: (x["Avg Cost per Attendee (£)"], x["Avg Emissions per Attendee (kg CO2)"]))
    return results[:3], num_attendees, invalid_attendees, len(valid_destinations), invalid_destinations

def display_recommendations_and_charts(recommendations, num_attendees, invalid_attendees, valid_destinations_count, invalid_destinations_count, budget_cost, budget_time, budget_emissions, budget_type):
    df_recommendations = pd.DataFrame(recommendations)
    df_recommendations.index = df_recommendations.index + 1  # Make index start from 1

    st.write(df_recommendations)

    # Additional details about the number of attendees
    st.markdown(f"**Number of Attendees Processed: {num_attendees}**")
    st.markdown(f"**Invalid Attendees: {invalid_attendees}**")
    st.markdown(f"**Valid Potential Locations Considered: {valid_destinations_count}**")
    st.markdown(f"**Invalid Potential Locations: {invalid_destinations_count}**")
    st.markdown("This number reflects the total attendees considered to provide these location recommendations based on the provided postcodes.")

    # Create charts
    locations = [rec['Location'] for rec in recommendations]
    avg_costs = [rec['Avg Cost per Attendee (£)'] for rec in recommendations]
    avg_emissions = [rec['Avg Emissions per Attendee (kg CO2)'] for rec in recommendations]
    avg_times = [int(rec['Avg Time per Attendee'].split('h')[0]) * 60 + int(rec['Avg Time per Attendee'].split('h')[1].replace('m', '')) for rec in recommendations]
    total_costs = [rec['Total Cost (£)'] for rec in recommendations]
    total_emissions = [rec['Total Emissions (kg CO2)'] for rec in recommendations]
    total_times = [int(rec['Total Time'].split('h')[0]) * 60 + int(rec['Total Time'].split('h')[1].replace('m', '')) for rec in recommendations]

    if budget_type == "Total Budget for the Event":
        budget_cost_label = "Total Cost (£)"
        budget_time_label = "Total Time (minutes)"
        budget_emissions_label = "Total Emissions (kg CO2)"
    else:
        budget_cost_label = "Avg Cost per Attendee (£)"
        budget_time_label = "Avg Time per Attendee (minutes)"
        budget_emissions_label = "Avg Emissions per Attendee (kg CO2)"

    with tempfile.TemporaryDirectory() as temp_dir:
        fig, ax = plt.subplots()
        ax.bar(locations, avg_costs, color='blue', label=budget_cost_label)
        ax.axhline(y=budget_cost, color='red', linestyle='--', label=f'Budgeted {budget_cost_label}')
        ax.set_ylabel(budget_cost_label)
        ax.set_title(f'{budget_cost_label} vs Budget')
        ax.legend()
        fig.tight_layout()
        chart1_path = os.path.join(temp_dir, "chart1.png")
        fig.savefig(chart1_path)
        st.pyplot(fig)

        fig, ax = plt.subplots()
        ax.bar(locations, avg_emissions, color='green', label=budget_emissions_label)
        ax.axhline(y=budget_emissions, color='red', linestyle='--', label=f'Budgeted {budget_emissions_label}')
        ax.set_ylabel(budget_emissions_label)
        ax.set_title(f'{budget_emissions_label} vs Budget')
        ax.legend()
        fig.tight_layout()
        chart2_path = os.path.join(temp_dir, "chart2.png")
        fig.savefig(chart2_path)
        st.pyplot(fig)

        fig, ax = plt.subplots()
        ax.bar(locations, avg_times, color='purple', label=budget_time_label)
        ax.axhline(y=budget_time, color='red', linestyle='--', label=f'Budgeted {budget_time_label}')
        ax.set_ylabel(budget_time_label)
        ax.set_title(f'{budget_time_label} vs Budget')
        ax.legend()
        fig.tight_layout()
        chart3_path = os.path.join(temp_dir, "chart3.png")
        fig.savefig(chart3_path)
        st.pyplot(fig)

    # Summary of calculations and assumptions
    st.subheader("Summary of Recommendations Calculation")
    st.markdown("""
    ### How Recommendations are Calculated:
    1. **Validation of Locations**: All input locations (attendee postcodes and potential event locations) are validated using the Google Maps API to ensure they are correctly formatted and can be geocoded.
    2. **Distance and Time Calculation**: The Google Maps API is used to calculate the travel distances and times between each attendee's postcode and each potential event location. Both car and train travel modes are considered.
    3. **Travel Mode Selection**: The default travel mode is train. If the train travel time is more than 1.5 times the car travel time, car travel is selected instead.
    4. **Cost and Emissions Calculation**: Based on the selected travel mode, the total travel cost and emissions are calculated using the provided cost and emissions per km values. Average costs and emissions per attendee are also calculated.
    5. **Recommendation Ranking**: The potential event locations are ranked based on average cost and emissions per attendee, with the top three locations being recommended.

    ### Assumptions Made:
    - **Travel Mode**: Train is the default travel mode. Car travel is considered only if it significantly reduces travel time (less than 1.5 times the train travel time).
    - **Cost and Emissions Values**: The cost and emissions per km for car and train travel are user-provided estimates and may not reflect actual values.
    - **Distance and Time Calculations**: The distances and times calculated using the Google Maps API are assumed to be accurate representations of real-world travel.
    - **Budget Considerations**: The budget can be entered as either a total amount or an average per attendee, and the recommendations and charts are adjusted accordingly.

    These recommendations are intended to provide an optimized selection of event locations based on travel costs, emissions, and times. Please adjust the input values and consider other factors as needed for your specific event planning needs.
    """)

# Initialize the usage count file
usage_count_file = "usage_count.json"

# Function to load usage data
def load_usage_data():
    if os.path.exists(usage_count_file):
        with open(usage_count_file, "r") as f:
            return json.load(f)
    else:
        return {"usage_count": 0, "total_attendees": 0, "total_time": 0, "last_processing_time": 0}

# Function to save usage data
def save_usage_data(data):
    with open(usage_count_file, "w") as f:
        json.dump(data, f)

# Load current usage data
usage_data = load_usage_data()

if st.button("Generate Recommendations"):
    if not api_key:
        st.error("Please enter your Google API Key in the settings.")
    elif not uploaded_file:
        st.error("Please upload a CSV file with attendee postcodes.")
    else:
        start_time = time.time()
        with st.spinner('Recommendation Engine at work ⏳🚂...'):
            recommendations, num_attendees, invalid_attendees, valid_destinations_count, invalid_destinations_count = generate_recommendations(df, base_locations, cost_per_km_car, emission_per_km_car, cost_per_km_train, emission_per_km_train, budget_cost, budget_time, budget_emissions, budget_type)
            time.sleep(2)  # Simulate processing time
        end_time = time.time()
        processing_time = end_time - start_time
        
        st.subheader("Top 3 Recommended Locations")
        display_recommendations_and_charts(recommendations, num_attendees, invalid_attendees, valid_destinations_count, invalid_destinations_count, budget_cost, budget_time, budget_emissions, budget_type)

        # Update and save usage data
        usage_data["usage_count"] += 1
        usage_data["total_attendees"] += num_attendees
        usage_data["total_time"] += processing_time
        usage_data["last_processing_time"] = processing_time
        save_usage_data(usage_data)

# Display cumulative usage data in the sidebar
average_time = usage_data["total_time"] / usage_data["usage_count"] if usage_data["usage_count"] > 0 else 0
average_time_formatted = time.strftime("%M:%S", time.gmtime(average_time))
last_processing_time_formatted = time.strftime("%M:%S", time.gmtime(usage_data["last_processing_time"]))

st.sidebar.markdown("---")
st.sidebar.subheader("📊 Usage Statistics")
st.sidebar.markdown(f"**Total Events Planned:** {usage_data['usage_count']}")
st.sidebar.markdown(f"**Total Attendees Processed:** {usage_data['total_attendees']}")
st.sidebar.markdown(f"**Average Processing Time:** {average_time_formatted} min:sec")
st.sidebar.markdown(f"**Last Processing Time:** {last_processing_time_formatted} min:sec")

