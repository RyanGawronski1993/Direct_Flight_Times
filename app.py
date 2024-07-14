import streamlit as st
import folium
from streamlit_folium import st_folium
from geopy.distance import geodesic
import pandas as pd
import numpy as np
from geographiclib.geodesic import Geodesic

# function to load data
@st.cache_data
def load_data():
    file_path = '/Users/ryangawronski/Documents/IU/SUMMER2024/DSCI590-Data_Viz/Project/app/airport_locations.csv'
    return pd.read_csv(file_path)

# Load the airport locations data
df = load_data()

# dictionary of airports with their coordinates and additional details
airports = {
    row['Airport Name']: {
        'coords': (row['LATITUDE'], row['LONGITUDE']),
        'city': row['City'],
        'code': row['Airport Code']
    } for _, row in df.iterrows()
}




def calculate_flight(coords_1, coords_2):
    distance = int(geodesic(coords_1, coords_2).miles)
    if distance < 700:
        speed = 400
        haul_type = "Short Haul"
    elif 700 <= distance <= 3000:
        speed = 500
        haul_type = "Medium Haul"
    else:
        speed = 550
        haul_type = "Long Haul"
    
    flight_duration_hours = distance / speed
    hours = int(flight_duration_hours)
    minutes = int((flight_duration_hours - hours) * 60)
    return distance, (hours, minutes), haul_type




def get_great_circle_path(coords_1, coords_2, num_points=100):
    geod = Geodesic.WGS84
    line = geod.InverseLine(coords_1[0], coords_1[1], coords_2[0], coords_2[1])
    path = []

    for i in np.linspace(0, line.s13, num_points):
        g = line.Position(i, Geodesic.STANDARD | Geodesic.LONG_UNROLL)
        path.append((g['lat2'], g['lon2']))

    return path



# Streamlit app
st.title("Interactive Flight Duration Map")
st.write("Click on two airports on the map to calculate the direct flight duration")



# reset session state
if st.button("Reset Selections"):
    st.session_state.clear()
    st.experimental_rerun()


# initialize session state
if 'selected_points' not in st.session_state:
    st.session_state.selected_points = []


if len(st.session_state.selected_points) == 2:
    # cal bounds to fit the map view
    lat_min = min(st.session_state.selected_points[0]['lat'], st.session_state.selected_points[1]['lat'])
    lat_max = max(st.session_state.selected_points[0]['lat'], st.session_state.selected_points[1]['lat'])
    lng_min = min(st.session_state.selected_points[0]['lng'], st.session_state.selected_points[1]['lng'])
    lng_max = max(st.session_state.selected_points[0]['lng'], st.session_state.selected_points[1]['lng'])
    
    bounds = [[lat_min, lng_min], [lat_max, lng_max]]
    map = folium.Map(location=[(lat_min + lat_max) / 2, (lng_min + lng_max) / 2], no_wrap=True)
else:
    map = folium.Map(location=[37, -55], zoom_start=3, no_wrap=True)



# add airport markers with click functionality
for airport, details in airports.items():
    if len(st.session_state.selected_points) < 2 or details['coords'] in [tuple(point.values()) for point in st.session_state.selected_points]:
        icon = None
        if len(st.session_state.selected_points) == 2:
            if details['coords'] == tuple(st.session_state.selected_points[0].values()):
                icon = folium.Icon(prefix='fa', icon="plane-departure", color="green")
            elif details['coords'] == tuple(st.session_state.selected_points[1].values()):
                icon = folium.Icon(prefix='fa', icon="plane-arrival", color="red")
        folium.Marker(location=details['coords'], popup=airport, tooltip=details['city'], icon=icon).add_to(map)



# add flight path if it exists
if 'flight_path' in st.session_state and st.session_state.flight_path:
    folium.PolyLine(locations=st.session_state.flight_path, color="yellow", weight=2, opacity=1).add_to(map)
    map.fit_bounds(bounds)



# display map
st_map = st_folium(map, width=1200, height=500)



# add sidebar for displaying flight details
with st.sidebar:
    st.header("Flight Details")
    if 'haul_type' in st.session_state:
        st.write(f"Trip Type: {st.session_state.haul_type}")
    if 'details1' in st.session_state:
        st.write(st.session_state.details1)
    if 'details2' in st.session_state:
        st.write(st.session_state.details2)
    if 'flight_info' in st.session_state:
        st.write(st.session_state.flight_info)



if st_map['last_object_clicked'] is not None:
    clicked_lat = st_map['last_object_clicked']['lat']
    clicked_lng = st_map['last_object_clicked']['lng']
    clicked_coords = (clicked_lat, clicked_lng)
    
    
    # check if clicked point is valid airport marker
    valid_click = False
    for airport, details in airports.items():
        if details['coords'] == clicked_coords:
            valid_click = True
            break
   


    # only process click if it's a new valid click
    if valid_click and (not st.session_state.selected_points or clicked_coords != tuple(st.session_state.selected_points[-1].values())):
        if len(st.session_state.selected_points) == 2:
            st.session_state.clear()
            st.session_state.selected_points.append({'lat': clicked_lat, 'lng': clicked_lng})
        else:
            st.session_state.selected_points.append({'lat': clicked_lat, 'lng': clicked_lng})
        
        
        if len(st.session_state.selected_points) == 1:
            point1 = st.session_state.selected_points[0]
            coords_1 = (point1['lat'], point1['lng'])
            
            airport1, details1 = next((airport, details) for airport, details in airports.items() if details['coords'] == coords_1)
            
            st.session_state.details1 = f"Origin: {details1['city']} ({airport1}, {details1['code']})"
        
        
        elif len(st.session_state.selected_points) == 2:
            point1 = st.session_state.selected_points[0]
            point2 = st.session_state.selected_points[1]
            
            coords_1 = (point1['lat'], point1['lng'])
            coords_2 = (point2['lat'], point2['lng'])
            
            airport1, details1 = next((airport, details) for airport, details in airports.items() if details['coords'] == coords_1)
            airport2, details2 = next((airport, details) for airport, details in airports.items() if details['coords'] == coords_2)
            
            distance, (hours, minutes), haul_type = calculate_flight(coords_1, coords_2)
            st.session_state.details2 = f"Destination: {details2['city']} ({airport2}, {details2['code']})\n\n"
            st.session_state.flight_info = (f"Distance between: {distance} miles\n\n"
                                            f"Estimated flight duration: {hours} hours {minutes} minutes")
            st.session_state.haul_type = haul_type
            
            # get great-circle path points
            st.session_state.flight_path = get_great_circle_path(coords_1, coords_2)
        
        st.experimental_rerun()

