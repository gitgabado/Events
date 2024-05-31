import streamlit as st
import pandas as pd
import googlemaps
import matplotlib.pyplot as plt
from io import StringIO
import time
import os
import tempfile

st.title("Event Location Planner")

# Sidebar for settings and inputs
st.sidebar.header("Settings")
api_key = st.sidebar.text_input("Google API Key", type="password")

# Budget input type toggle
budget_type = st.sidebar.radio("Budget Type", ["Total", "Average per Attendee"])

if budget_type == "Total":
    budget_cost = st.sidebar.number_input("Total Budget for Costs ($)", value=1000)
    budget_time = st.sidebar.number_input("Total Budget for Time (minutes)", value=120)
    budget_emissions = st.sidebar.number_input("Total Budget for Emissions (kg CO2)", value=200)
else:
    budget_cost = st.sidebar.number_input("Average Budget for Costs per Attendee ($)", value=100)
    budget_time = st.sidebar.number_input("Average Budget for Time per Attendee (minutes)", value=15)
    budget_emissions = st.sidebar.number_input("Average Budget for Emissions per Attendee (kg CO2)", value=20)

# Lookup Table for Cost and Emissions
st.sidebar.subheader("Cost and Emissions Lookup Table")
cost_per_km = st.sidebar.number_input("Cost per km ($)", value=0.5)
emission_per_km = st.sidebar.number_input("Emissions per km (kg CO2)", value=0.2)

# Potential Base Locations Input
st.sidebar.subheader("Potential Base Locations")
base_locations = st.sidebar.text_area("Enter base locations (one per line)", 
                                      "London, UK\nManchester, UK\nBirmingham, UK\nLeeds, UK\nGlasgow, UK\nEdinburgh, UK\nBristol, UK\nLiverpool, UK\nNewcastle, UK\nSheffield, UK")

# Upload Attendee Postcodes
st.subheader("Upload Attendee Postcodes CSV")
uploaded_file = st.file_uploader("Choose a CSV file", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    st.write("Attendee Postcodes:", df)

# Function to validate and format locations
def validate_location(api_key, location):
    gmaps = googlemaps.Client(key=api_key)
    try:
        result = gmaps.geocode(location)
        if result:
            formatted_address = result[0]['formatted_address']
            return formatted_address
        else:
            return None
    except Exception as e:
        st.error(f"Error validating location {location}: {e}")
        return None

# Function to calculate distances using Google Routes API
def calculate_distances(api_key, origins, destinations):
    gmaps = googlemaps.Client(key=api_key)
    distances = {}
    times = {}
    for origin in origins:
        distances[origin] = {}
        times[origin] = {}
        for destination in destinations:
            try:
                result = gmaps.directions(origin, destination, mode="driving")
                if result and result[0]['legs']:
                    distance = result[0]['legs'][0]['distance']['value'] / 1000  # in km
                    time = result[0]['legs'][0]['duration']['value'] / 60  # in minutes
                    distances[origin][destination] = distance
                    times[origin][destination] = time
                else:
                    distances[origin][destination] = float('inf')
                    times[origin][destination] = float('inf')
            except Exception as e:
                st.error(f"Error calculating distance from {origin} to {destination}: {e}")
                distances[origin][destination] = float('inf')
                times[origin][destination] = float('inf')
    return distances, times

# Function to generate recommendations
def generate_recommendations(df, base_locations, cost_per_km, emission_per_km, budget_cost, budget_time, budget_emissions, budget_type):
    origins = df['postcode'].tolist()
    valid_origins = [validate_location(api_key, origin) for origin in origins]
    valid_origins = [origin for origin in valid_origins if origin is not None]
    num_attendees = len(valid_origins)
    
    destinations = base_locations.split('\n')
    valid_destinations = [validate_location(api_key, destination) for destination in destinations]
    valid_destinations = [destination for destination in valid_destinations if destination is not None]
    
    distances, times = calculate_distances(api_key, valid_origins, valid_destinations)
    
    results = []
    for location in valid_destinations:
        total_cost = sum([distances[origin][location] * cost_per_km for origin in valid_origins])
        total_emissions = sum([distances[origin][location] * emission_per_km for origin in valid_origins])
        total_time = sum([times[origin][location] for origin in valid_origins])
        avg_cost_per_attendee = total_cost / num_attendees
        avg_emissions_per_attendee = total_emissions / num_attendees
        avg_time_per_attendee = total_time / num_attendees
        total_time_hours, total_time_minutes = divmod(total_time, 60)
        
        results.append({
            "Location": location,
            "Total Cost ($)": int(total_cost),
            "Total Emissions (kg CO2)": int(total_emissions),
            "Total Time": f"{int(total_time_hours)}h {int(total_time_minutes)}m",
            "Avg Cost per Attendee ($)": int(avg_cost_per_attendee),
            "Avg Emissions per Attendee (kg CO2)": int(avg_emissions_per_attendee),
            "Avg Time per Attendee": f"{int(avg_time_per_attendee // 60)}h {int(avg_time_per_attendee % 60)}m"
        })
    
    results = sorted(results, key=lambda x: (x["Total Cost ($)"], x["Total Emissions (kg CO2)"]))
    return results[:3], num_attendees

def display_recommendations_and_charts(recommendations, num_attendees, budget_cost, budget_time, budget_emissions, budget_type):
    df_recommendations = pd.DataFrame(recommendations)
    df_recommendations.index = df_recommendations.index + 1  # Make index start from 1

    # Styling the DataFrame for a premium look
    styled_df = df_recommendations.style.set_table_styles(
        [{'selector': 'th', 'props': [('font-size', '14pt'), ('text-align', 'center')]},
         {'selector': 'td', 'props': [('font-size', '12pt'), ('text-align', 'center')]}]
    ).set_properties(**{
        'background-color': 'white',
        'color': 'black',
        'border-color': 'black'
    }).hide(axis='index')

    st.write(styled_df.to_html(), unsafe_allow_html=True)

    locations = [rec['Location'] for rec in recommendations]
    costs = [rec['Avg Cost per Attendee ($)'] if budget_type == "Average per Attendee" else rec['Total Cost ($)'] for rec in recommendations]
    emissions = [rec['Avg Emissions per Attendee (kg CO2)'] if budget_type == "Average per Attendee" else rec['Total Emissions (kg CO2)'] for rec in recommendations]
    times = [int(rec['Avg Time per Attendee'].split('h')[0])*60 + int(rec['Avg Time per Attendee'].split('h')[1].replace('m', '')) if budget_type == "Average per Attendee" else float(rec['Total Time'].split('h')[0])*60 + float(rec['Total Time'].split('h')[1].replace('m', '')) for rec in recommendations]

    if budget_type == "Total":
        budget_cost_label = "Total Cost ($)"
        budget_time_label = "Total Time (minutes)"
        budget_emissions_label = "Total Emissions (kg CO2)"
    else:
        budget_cost_label = "Avg Cost per Attendee ($)"
        budget_time_label = "Avg Time per Attendee (minutes)"
        budget_emissions_label = "Avg Emissions per Attendee (kg CO2)"
        budget_cost *= num_attendees
        budget_time *= num_attendees
        budget_emissions *= num_attendees

    with tempfile.TemporaryDirectory() as temp_dir:
        fig, ax = plt.subplots()
        ax.bar(locations, costs, color='blue', label=budget_cost_label)
        ax.axhline(y=budget_cost, color='red', linestyle='--', label=budget_cost_label)
        ax.set_ylabel(budget_cost_label)
        ax.set_title(f'{budget_cost_label} vs Budget')
        ax.legend()
        fig.tight_layout()
        chart1_path = os.path.join(temp_dir, "chart1.png")
        fig.savefig(chart1_path)
        st.pyplot(fig)

        fig, ax = plt.subplots()
        ax.bar(locations, emissions, color='green', label=budget_emissions_label)
        ax.axhline(y=budget_emissions, color='red', linestyle='--', label=budget_emissions_label)
        ax.set_ylabel(budget_emissions_label)
        ax.set_title(f'{budget_emissions_label} vs Budget')
        ax.legend()
        fig.tight_layout()
        chart2_path = os.path.join(temp_dir, "chart2.png")
        fig.savefig(chart2_path)
        st.pyplot(fig)

        fig, ax = plt.subplots()
        ax.bar(locations, times, color='purple', label=budget_time_label)
        ax.axhline(y=budget_time, color='red', linestyle='--', label=budget_time_label)
        ax.set_ylabel(budget_time_label)
        ax.set_title(f'{budget_time_label} vs Budget')
        ax.legend()
        fig.tight_layout()
        chart3_path = os.path.join(temp_dir, "chart3.png")
        fig.savefig(chart3_path)
        st.pyplot(fig)

if st.button("Generate Recommendations"):
    if not api_key:
        st.error("Please enter your Google API Key in the settings.")
    elif not uploaded_file:
        st.error("Please upload a CSV file with attendee postcodes.")
    else:
        with st.spinner('Recommendation Engine at work ⏳'):
            recommendations, num_attendees = generate_recommendations(df, base_locations, cost_per_km, emission_per_km, budget_cost, budget_time, budget_emissions, budget_type)
            time.sleep(2)  # Simulate processing time
        
        st.subheader("Top 3 Recommended Locations")
        display_recommendations_and_charts(recommendations, num_attendees, budget_cost, budget_time, budget_emissions, budget_type)
