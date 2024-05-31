import streamlit as st
import pandas as pd
import googlemaps
import matplotlib.pyplot as plt
from io import StringIO

st.title("Event Location Planner")

# Sidebar for settings and inputs
st.sidebar.header("Settings")
api_key = st.sidebar.text_input("Google API Key", type="password")
budget = st.sidebar.number_input("Budget ($)", value=1000)

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

# Function to validate locations
def validate_location(api_key, location):
    gmaps = googlemaps.Client(key=api_key)
    try:
        result = gmaps.geocode(location)
        if result:
            return result[0]['formatted_address']
        else:
            return None
    except Exception as e:
        st.error(f"Error validating location {location}: {e}")
        return None

# Function to calculate distances using Google Routes API
def calculate_distances(api_key, origins, destinations):
    gmaps = googlemaps.Client(key=api_key)
    distances = {}
    for origin in origins:
        valid_origin = validate_location(api_key, origin)
        if not valid_origin:
            st.error(f"Invalid origin: {origin}")
            continue
        distances[origin] = []
        for destination in destinations:
            valid_destination = validate_location(api_key, destination)
            if not valid_destination:
                st.error(f"Invalid destination: {destination}")
                distances[origin].append(float('inf'))
                continue
            try:
                result = gmaps.directions(valid_origin, valid_destination, mode="driving")
                if result and result[0]['legs']:
                    distance = result[0]['legs'][0]['distance']['value'] / 1000  # in km
                    distances[origin].append(distance)
                else:
                    distances[origin].append(float('inf'))
            except Exception as e:
                st.error(f"Error calculating distance from {valid_origin} to {valid_destination}: {e}")
                distances[origin].append(float('inf'))
    return distances

# Function to generate recommendations
def generate_recommendations(df, base_locations, cost_per_km, emission_per_km, budget):
    origins = df['postcode'].tolist()
    destinations = base_locations.split('\n')
    
    distances = calculate_distances(api_key, origins, destinations)
    
    results = []
    for location in destinations:
        if location not in distances:
            continue
        total_cost = sum([dist * cost_per_km for dist in distances[location]])
        total_emissions = sum([dist * emission_per_km for dist in distances[location]])
        avg_cost_per_attendee = total_cost / len(origins)
        
        results.append({
            "Location": location,
            "Total Cost": total_cost,
            "Total Emissions": total_emissions,
            "Avg Cost per Attendee": avg_cost_per_attendee
        })
    
    results = sorted(results, key=lambda x: (x["Total Cost"], x["Total Emissions"]))
    return results[:3]

if st.button("Generate Recommendations"):
    if not api_key:
        st.error("Please enter your Google API Key in the settings.")
    elif not uploaded_file:
        st.error("Please upload a CSV file with attendee postcodes.")
    else:
        recommendations = generate_recommendations(df, base_locations, cost_per_km, emission_per_km, budget)
        st.subheader("Top 3 Recommended Locations")
        
        for idx, rec in enumerate(recommendations, 1):
            st.markdown(f"**{idx}. {rec['Location']}**")
            st.write(f"Total Cost: ${rec['Total Cost']:.2f}")
            st.write(f"Total Emissions: {rec['Total Emissions']:.2f} kg CO2")
            st.write(f"Avg Cost per Attendee: ${rec['Avg Cost per Attendee']:.2f}")

        # Visualization
        locations = [rec['Location'] for rec in recommendations]
        costs = [rec['Total Cost'] for rec in recommendations]
        emissions = [rec['Total Emissions'] for rec in recommendations]
        
        fig, ax = plt.subplots()
        ax.bar(locations, costs, color='blue', label='Total Cost')
        ax.axhline(y=budget, color='red', linestyle='--', label='Budget')
        ax.set_ylabel('Cost ($)')
        ax.set_title('Total Cost vs Budget')
        ax.legend()
        
        st.pyplot(fig)
        
        fig, ax = plt.subplots()
        ax.bar(locations, emissions, color='green', label='Total Emissions')
        ax.set_ylabel('Emissions (kg CO2)')
        ax.set_title('Total Emissions by Location')
        ax.legend()
        
        st.pyplot(fig)
