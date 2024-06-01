    results = sorted(results, key=lambda x: (x["Total Cost (£)"], x["Total Emissions (kg CO2)"]))
    return results[:3], num_attendees

def display_recommendations_and_charts(recommendations, num_attendees, budget_cost, budget_time, budget_emissions, budget_type):
    df_recommendations = pd.DataFrame(recommendations)
    df_recommendations.index = df_recommendations.index + 1  # Make index start from 1

    st.write(df_recommendations)

    # Additional details about the number of attendees
    st.markdown(f"**Number of Attendees Processed: {num_attendees}**")
    st.markdown("This number reflects the total attendees considered to provide these location recommendations based on the provided postcodes.")

    # Create charts
    locations = [rec['Location'] for rec in recommendations]
    costs = [rec['Avg Cost per Attendee (£)'] if budget_type == "Average Budget per Attendee" else rec['Total Cost (£)'] for rec in recommendations]
    emissions = [rec['Avg Emissions per Attendee (kg CO2)'] if budget_type == "Average Budget per Attendee" else rec['Total Emissions (kg CO2)'] for rec in recommendations]
    times = [int(rec['Avg Time per Attendee'].split('h')[0]) * 60 + int(rec['Avg Time per Attendee'].split('h')[1].replace('m', '')) if budget_type == "Average Budget per Attendee" else float(rec['Total Time'].split('h')[0]) * 60 + float(rec['Total Time'].split('h')[1].replace('m', '')) for rec in recommendations]

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
        ax.bar(locations, costs, color='blue', label=budget_cost_label)
        ax.axhline(y=budget_cost, color='red', linestyle='--', label=f'Budgeted {budget_cost_label}')
        ax.set_ylabel(budget_cost_label)
        ax.set_title(f'{budget_cost_label} vs Budget')
        ax.legend()
        fig.tight_layout()
        chart1_path = os.path.join(temp_dir, "chart1.png")
        fig.savefig(chart1_path)
        st.pyplot(fig)

        fig, ax = plt.subplots()
        ax.bar(locations, emissions, color='green', label=budget_emissions_label)
        ax.axhline(y=budget_emissions, color='red', linestyle='--', label=f'Budgeted {budget_emissions_label}')
        ax.set_ylabel(budget_emissions_label)
        ax.set_title(f'{budget_emissions_label} vs Budget')
        ax.legend()
        fig.tight_layout()
        chart2_path = os.path.join(temp_dir, "chart2.png")
        fig.savefig(chart2_path)
        st.pyplot(fig)

        fig, ax = plt.subplots()
        ax.bar(locations, times, color='purple', label=budget_time_label)
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
    5. **Recommendation Ranking**: The potential event locations are ranked based on total cost and emissions, with the top three locations being recommended.

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
        with st.spinner('Recommendation Engine at work ⏳'):
            recommendations, num_attendees = generate_recommendations(df, base_locations, cost_per_km_car, emission_per_km_car, cost_per_km_train, emission_per_km_train, budget_cost, budget_time, budget_emissions, budget_type)
            time.sleep(2)  # Simulate processing time
        end_time = time.time()
        processing_time = end_time - start_time
        
        st.subheader("Top 3 Recommended Locations")
        display_recommendations_and_charts(recommendations, num_attendees, budget_cost, budget_time, budget_emissions, budget_type)

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
st.sidebar.markdown(f"**Average Processing Time:** {average_time_formatted} minutes")
st.sidebar.markdown(f"**Last Processing Time:** {last_processing_time_formatted} minutes")
