import streamlit as st
import pandas as pd
import googlemaps
import matplotlib.pyplot as plt
import time
import json

st.title("Event Location Planner")

st.subheader("Plan your events efficiently with optimal locations 🌍🎉")
st.markdown("""
This tool helps you to find the best locations for your events based on travel time, cost, and emissions. 
Upload a CSV file with attendee postcodes, configure your cost and emission parameters, and get the top location recommendations for hosting your event.
""")

# Sidebar for settings and inputs
st.sidebar.header("⚙️ Settings")

api_key = st.sidebar.text_input("Google API Key", type="password")

st.sidebar.subheader("💸 Budget")
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
base_locations_input = st.sidebar.text_area("Enter base locations separated by commas", "London, Manchester, Birmingham")
base_locations = [location.strip() for location in base_locations_input.split(",")]

# File uploader for attendee postcodes
uploaded_file = st.file_uploader("Upload a CSV file with attendee postcodes", type="csv")

# Helper functions
def calculate_cost_and_emissions(distance, cost_per_km, emission_per_km):
    return distance * cost_per_km, distance * emission_per_km

def load_usage_data():
    try:
        with open("usage_data.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"usage_count": 0, "total_attendees": 0, "total_time": 0}

def save_usage_data(data):
    with open("usage_data.json", "w") as f:
        json.dump(data, f)

def generate_recommendations(df, base_locations, cost_per_km_car, emission_per_km_car, cost_per_km_train, emission_per_km_train, budget_cost, budget_time, budget_emissions, budget_type):
    gmaps = googlemaps.Client(key=api_key)
    recommendations = []

    for base in base_locations:
        total_cost, total_time, total_emissions = 0, 0, 0
        valid_postcodes = 0

        for postcode in df["postcode"]:
            try:
                directions = gmaps.directions(postcode, base, mode="driving")
                if not directions:
                    st.error(f"No directions found for postcode: {postcode}")
                    continue

                distance_km = directions[0]["legs"][0]["distance"]["value"] / 1000
                time_minutes = directions[0]["legs"][0]["duration"]["value"] / 60

                cost_car, emissions_car = calculate_cost_and_emissions(distance_km, cost_per_km_car, emission_per_km_car)
                cost_train, emissions_train = calculate_cost_and_emissions(distance_km, cost_per_km_train, emission_per_km_train)

                total_cost += min(cost_car, cost_train)
                total_time += time_minutes
                total_emissions += min(emissions_car, emissions_train)
                valid_postcodes += 1

            except googlemaps.exceptions.ApiError as e:
                st.error(f"API error for postcode {postcode}: {e}")
            except Exception as e:
                st.error(f"Unexpected error for postcode {postcode}: {e}")

        if valid_postcodes > 0:
            if budget_type == "Total Budget for the Event":
                if total_cost <= budget_cost and total_time <= budget_time and total_emissions <= budget_emissions:
                    recommendations.append((base, total_cost, total_time, total_emissions))
            else:
                avg_cost = total_cost / valid_postcodes
                avg_time = total_time / valid_postcodes
                avg_emissions = total_emissions / valid_postcodes
                if avg_cost <= budget_cost and avg_time <= budget_time and avg_emissions <= budget_emissions:
                    recommendations.append((base, avg_cost, avg_time, avg_emissions))

    recommendations.sort(key=lambda x: (x[1], x[2], x[3]))
    return recommendations[:3], len(df)

def display_recommendations_and_charts(recommendations, num_attendees, budget_cost, budget_time, budget_emissions, budget_type):
    for i, (location, cost, time, emissions) in enumerate(recommendations):
        st.subheader(f"Recommendation {i+1}: {location}")
        st.markdown(f"**Total Cost:** £{cost:.2f}")
        st.markdown(f"**Total Time:** {time:.2f} minutes")
        st.markdown(f"**Total Emissions:** {emissions:.2f} kg CO2")

        labels = ["Cost", "Time", "Emissions"]
        values = [cost, time, emissions]
        if budget_type == "Total Budget for the Event":
            limits = [budget_cost, budget_time, budget_emissions]
        else:
            limits = [budget_cost * num_attendees, budget_time * num_attendees, budget_emissions * num_attendees]

        fig, ax = plt.subplots()
        ax.bar(labels, values, color=["blue", "green", "red"])
        ax.axhline(y=limits[0], color="blue", linestyle="--", label=f"Budget Cost: £{limits[0]:.2f}")
        ax.axhline(y=limits[1], color="green", linestyle="--", label=f"Budget Time: {limits[1]:.2f} minutes")
        ax.axhline(y=limits[2], color="red", linestyle="--", label=f"Budget Emissions: {limits[2]:.2f} kg CO2")
        ax.legend()
        st.pyplot(fig)

# Load current usage data
usage_data = load_usage_data()

if st.button("Generate Recommendations"):
    if not api_key:
        st.error("Please enter your Google API Key in the settings.")
    elif not uploaded_file:
        st.error("Please upload a CSV file with attendee postcodes.")
    else:
        df = pd.read_csv(uploaded_file)
        if 'postcode' not in df.columns:
            st.error("The uploaded CSV file must contain a 'postcode' column.")
        else:
            start_time = time.time()
            with st.spinner('Recommendation Engine at work ⏳'):
                recommendations, num_attendees = generate_recommendations(
                    df, base_locations, cost_per_km_car, emission_per_km_car,
                    cost_per_km_train, emission_per_km_train, budget_cost,
                    budget_time, budget_emissions, budget_type
                )
                time.sleep(2)  # Simulate processing time
            end_time = time.time()
            processing_time = end_time - start_time

            if recommendations:
                st.subheader("Top 3 Recommended Locations")
                display_recommendations_and_charts(recommendations, num_attendees, budget_cost, budget_time, budget_emissions, budget_type)
            else:
                st.write("No recommendations could be generated based on the input criteria.")

            # Update and save usage data
            usage_data["usage_count"] += 1
            usage_data["total_attendees"] += num_attendees
            usage_data["total_time"] += processing_time
            save_usage_data(usage_data)

# Display cumulative usage data in the sidebar
average_time = usage_data["total_time"] / usage_data["usage_count"] if usage_data["usage_count"] > 0 else 0
average_time_formatted = time.strftime("%M:%S", time.gmtime(average_time))

st.sidebar.markdown("---")
st.sidebar.subheader("📊 Usage Statistics")
st.sidebar.markdown(f"**Total Events Planned:** {usage_data['usage_count']}")
st.sidebar.markdown(f"**Total Attendees Processed:** {usage_data['total_attendees']}")
st.sidebar.markdown(f"**Average Processing Time:** {average_time_formatted} minutes")
