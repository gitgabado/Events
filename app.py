import streamlit as st
import pandas as pd
import googlemaps
import matplotlib.pyplot as plt
from io import StringIO
import time
from fpdf import FPDF
import os
import tempfile

st.title("Event Location Planner")

# Sidebar for settings and inputs
st.sidebar.header("Settings")
api_key = st.sidebar.text_input("Google API Key", type="password")
budget_cost = st.sidebar.number_input("Budget for Costs ($)", value=1000)
budget_time = st.sidebar.number_input("Budget for Time (minutes)", value=120)
budget_emissions = st.sidebar.number_input("Budget for Emissions (kg CO2)", value=200)

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
def generate_recommendations(df, base_locations, cost_per_km, emission_per_km, budget_cost, budget_time, budget_emissions):
    origins = df['postcode'].tolist()
    valid_origins = [validate_location(api_key, origin) for origin in origins]
    valid_origins = [origin for origin in valid_origins if origin is not None]
    
    destinations = base_locations.split('\n')
    valid_destinations = [validate_location(api_key, destination) for destination in destinations]
    valid_destinations = [destination for destination in valid_destinations if destination is not None]
    
    distances, times = calculate_distances(api_key, valid_origins, valid_destinations)
    
    results = []
    for location in valid_destinations:
        total_cost = sum([distances[origin][location] * cost_per_km for origin in valid_origins])
        total_emissions = sum([distances[origin][location] * emission_per_km for origin in valid_origins])
        total_time = sum([times[origin][location] for origin in valid_origins])
        avg_cost_per_attendee = total_cost / len(valid_origins)
        avg_emissions_per_attendee = total_emissions / len(valid_origins)
        avg_time_per_attendee = total_time / len(valid_origins)
        total_time_hours, total_time_minutes = divmod(total_time, 60)
        
        results.append({
            "Location": location,
            "Total Cost": total_cost,
            "Total Emissions": total_emissions,
            "Total Time": f"{int(total_time_hours)}h {int(total_time_minutes)}m",
            "Avg Cost per Attendee": avg_cost_per_attendee,
            "Avg Emissions per Attendee": avg_emissions_per_attendee,
            "Avg Time per Attendee": avg_time_per_attendee
        })
    
    results = sorted(results, key=lambda x: (x["Total Cost"], x["Total Emissions"]))
    return results[:3]

# Function to generate PDF report
def generate_pdf(report_data, charts):
    pdf = FPDF()
    pdf.add_page()
    
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Event Location Planner Report", ln=True, align='C')
    
    pdf.ln(10)
    pdf.cell(200, 10, txt=f"Total Number of Attendees: {len(report_data['origins'])}", ln=True)
    
    pdf.ln(10)
    pdf.set_font("Arial", size=10)
    
    for idx, rec in enumerate(report_data['recommendations'], 1):
        pdf.cell(200, 10, txt=f"{idx}. {rec['Location']}", ln=True)
        pdf.cell(200, 10, txt=f"   Total Cost: ${rec['Total Cost']:.2f}", ln=True)
        pdf.cell(200, 10, txt=f"   Total Emissions: {rec['Total Emissions']:.2f} kg CO2", ln=True)
        pdf.cell(200, 10, txt=f"   Total Time: {rec['Total Time']}", ln=True)
        pdf.cell(200, 10, txt=f"   Avg Cost per Attendee: ${rec['Avg Cost per Attendee']:.2f}", ln=True)
        pdf.cell(200, 10, txt=f"   Avg Emissions per Attendee: {rec['Avg Emissions per Attendee']:.2f} kg CO2", ln=True)
        pdf.cell(200, 10, txt=f"   Avg Time per Attendee: {rec['Avg Time per Attendee']:.2f} minutes", ln=True)
        pdf.ln(5)
    
    for chart in charts:
        pdf.add_page()
        pdf.image(chart, x=10, y=20, w=180)
    
    pdf_output = "/mnt/data/event_location_report.pdf"
    pdf.output(pdf_output)
    return pdf_output

if st.button("Generate Recommendations"):
    if not api_key:
        st.error("Please enter your Google API Key in the settings.")
    elif not uploaded_file:
        st.error("Please upload a CSV file with attendee postcodes.")
    else:
        with st.spinner('Recommendation Engine at work ⏳'):
            recommendations = generate_recommendations(df, base_locations, cost_per_km, emission_per_km, budget_cost, budget_time, budget_emissions)
            time.sleep(2)  # Simulate processing time
        
        st.subheader("Top 3 Recommended Locations")
        
        df_recommendations = pd.DataFrame(recommendations)
        st.table(df_recommendations)

        # Visualization
        locations = [rec['Location'] for rec in recommendations]
        costs = [rec['Total Cost'] for rec in recommendations]
        emissions = [rec['Total Emissions'] for rec in recommendations]
        times = [float(rec['Total Time'].split('h')[0])*60 + float(rec['Total Time'].split('h')[1].replace('m', '')) for rec in recommendations]

        # Use temporary directory for charts
        with tempfile.TemporaryDirectory() as temp_dir:
            fig, ax = plt.subplots()
            ax.bar(locations, costs, color='blue', label='Total Cost')
            ax.axhline(y=budget_cost, color='red', linestyle='--', label='Cost Budget')
            ax.set_ylabel('Cost ($)')
            ax.set_title('Total Cost vs Budget')
            ax.legend()
            fig.tight_layout()
            
            chart1_path = os.path.join(temp_dir, "chart1.png")
            try:
                fig.savefig(chart1_path)
            except Exception as e:
                st.error(f"Error saving chart: {e}")
            st.pyplot(fig)

            fig, ax = plt.subplots()
            ax.bar(locations, emissions, color='green', label='Total Emissions')
            ax.axhline(y=budget_emissions, color='red', linestyle='--', label='Emissions Budget')
            ax.set_ylabel('Emissions (kg CO2)')
            ax.set_title('Total Emissions vs Budget')
            ax.legend()
            fig.tight_layout()
            
            chart2_path = os.path.join(temp_dir, "chart2.png")
            try:
                fig.savefig(chart2_path)
            except Exception as e:
                st.error(f"Error saving chart: {e}")
            st.pyplot(fig)

            fig, ax = plt.subplots()
            ax.bar(locations, times, color='purple', label='Total Time')
            ax.axhline(y=budget_time, color='red', linestyle='--', label='Time Budget')
            ax.set_ylabel('Time (minutes)')
            ax.set_title('Total Time vs Budget')
            ax.legend()
            fig.tight_layout()
            
            chart3_path = os.path.join(temp_dir, "chart3.png")
            try:
                fig.savefig(chart3_path)
            except Exception as e:
                st.error(f"Error saving chart: {e}")
            st.pyplot(fig)
            
            if st.button("Download Report 📄"):
                report_data = {
                    "origins": df['postcode'].tolist(),
                    "recommendations": recommendations
                }
                pdf_output = generate_pdf(report_data, [chart1_path, chart2_path, chart3_path])
                st.success(f"Report generated successfully! [Download Report]({pdf_output})")
