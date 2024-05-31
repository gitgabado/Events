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
                                      "London\nManchester\nBirmingham\nLeeds\nGlasgow\nEdinburgh\nBristol\nLiverpool\nNewcastle\nSheffield")

# Upload Attendee Postcodes
st.subheader("Upload Attendee Postcodes CSV")
uploaded_file = st.file_uploader("Choose a CSV file", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    st.write("Attendee Postcodes:", df)

# Function to calculate distances using Google Routes API
def calculate_distances(api_key, origins, destinations):
    gmaps = googlemaps.Client(key=api_key)
    distances = {}
    for origin in origins:
        distances[origin] = []
        for destination in destinations:
            try:
                result = gmaps.directions(origin, destination, mode="driving")
                if result:
                    distance = result[0]['legs'][0]['distance']['value'] / 1000  # in km
                    distances[origin].append(distance)
                else:
                    distances[origin].append(float('inf'))
            except Exception as e:
                st.error(f"Error calculating distance from {origin} to {destination}: {e}")
                distances[origin].append(float('inf'))
    return distances

# Function to generate recommendations
def generate_recommendations(df, base_locations, cost_per_km, emission_per_km, budget):
    origins = df['postcode'].tolist()
    destinations = base_locations.split('\n')
    
    distances = calculate_distances(api_key, origins, destinations)
    
    results = []
    for location in destinations:
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

