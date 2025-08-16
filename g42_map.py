import streamlit as st
import pandas as pd
import numpy as np
import pydeck as pdk
import requests
import json
from pydeck.types import String
import math

# constants for the contact source location
CONTACT_SOURCE_LATITUDE = 48.0866987
CONTACT_SOURCE_LONGITUDE = 11.5082437


# set to fullscreen
st.set_page_config(layout="wide")
st.title('München: Offene Werkstätten und Garage42 Orte')    

# carry out sparql request on wikidata instance
def get_sparql_query_result_items(url, query):

    params = {
        'query': query,
        'format': 'json'
    }

    response = requests.post(url, data=params)
    json_data = response.json()

    result = []

    for item in json_data['results']['bindings']:
        url_token = item['item']['value'].split('/')
        q_id = url_token[len(url_token)-1] 
        #print(q_id)
        result.append(q_id)
        
    return result

def get_makerspaces():
    url = "https://query.wikidata.org/sparql"
    query = """
    SELECT ?item WHERE {
      ?item wdt:P31 wd:Q45820240;
      wdt:P131 wd:Q1726.
    }
    """
    
    return get_sparql_query_result_items(url, query)

def fetch_wikidata_item(url, params):
    
    try:
        return requests.get(url, params=params)
    except:
        return 'There was an error'
        
def get_wikidata_coordinate_location(url, wikidata_item, property_coordinates):
    id = wikidata_item
    params = {
                'action': 'wbgetentities',
                'ids': id,
                'format': 'json',
                'languages': 'en'
            }
    
    data = fetch_wikidata_item(url, params)
    data = data.json()
    #print(data)

    location_value = data["entities"][id]["claims"][property_coordinates][0]['mainsnak']['datavalue']['value']
    label = data["entities"][id]["labels"]["en"]["value"]
    latitude = location_value['latitude']
    longitude = location_value['longitude']
    
    return label, latitude, longitude

def build_dataframe_makerspace_static():
    # create dataframe fro csv file data 'makerspaces.csv' 
    # with columns name, lat, lon
    with open('makerspaces.csv', 'r') as f:
        colnames=["tags", "lat", "lon"]
        df = pd.read_csv(f, index_col=False, names=colnames, header=0)
        
    return df
  
def initialize_pois(activity_level):
    with open('poi.csv', 'r') as f:
        colnames=["tags", "lat", "lon", "count", "activity_level"] 
        
        # header=0 is essential here otherwise the csv parser would assume five columns
        # also colnames lon, lat, count must be set 
        # so that they can be referenced in the pdk.Layer 
        df = pd.read_csv(f, index_col=False, names=colnames, header=0)

    df = df[df['activity_level'] == activity_level]

    return df


def get_g42_workshops():
    url = "https://flmr-db.wikibase.cloud/query/sparql"
    
    query = """
        PREFIX flmd: <https://flmr-db.wikibase.cloud/entity/>
        PREFIX flmdt: <https://flmr-db.wikibase.cloud/prop/direct/>

        select ?item where { 
            ?item flmdt:P1 flmd:Q12
        }
    """
    
    return get_sparql_query_result_items(url, query)

def build_dataframe_g42_workshops():

    workshops = get_g42_workshops()
    #print("G42 Workshops")
    #print(workshops)
    
    url = "https://flmr-db.wikibase.cloud/w/api.php"
    property_coordinates = 'P13'
    
    # retrieve base64 encoded image from file
    f = open("G42Icon.txt", "r")
    ICON_URL = f.read()
    f = open("G42IconInactive.txt", "r")
    ICON_URL_INACTIVE = f.read()

    icon_data = {
        # Icon from Wikimedia, used the Creative Commons Attribution-Share Alike 3.0
        # Unported, 2.5 Generic, 2.0 Generic and 1.0 Generic licenses
        "url": ICON_URL,
        "width": 43,
        "height": 64,
        "anchorY": 0,
    }

    icon_data_inactive = {
        # Icon from Wikimedia, used the Creative Commons Attribution-Share Alike 3.0
        # Unported, 2.5 Generic, 2.0 Generic and 1.0 Generic licenses
        "url": ICON_URL_INACTIVE,
        "width": 43,
        "height": 64,
        "anchorY": 0,
    }
    
    d = {'name': [], 'lat': [], 'lon': [], 'tags': [], 'icon_data': []}
    for item in workshops:
        
        label, lat, lon = get_wikidata_coordinate_location(url, item, property_coordinates)
        d['name'].append(label)
        d['lat'].append(lat)
        d['lon'].append(lon)
        d['tags'].append(label)
        if(item == 'Q17'):
            d['icon_data'].append(icon_data)            
        else:
            d['icon_data'].append(icon_data_inactive)
    
    return d
 

def build_dataframe_makerspace():
    
    spaces = get_makerspaces()
    #print("Makerspaces")
    #print(spaces)
    
    url = "https://www.wikidata.org/w/api.php"
    property_coordinates = 'P625'
    
    d = {'name': [], 'lat': [], 'lon': [], 'tags': []}
    for item in spaces:
        label, lat, lon = get_wikidata_coordinate_location(url, item, property_coordinates)
        d['name'].append(label)
        d['lat'].append(lat)
        d['lon'].append(lon)
        d['tags'].append(label)
    
    df = pd.DataFrame(data=d)
    return df

suburbs = []

def initialize_suburb_names():

    # iterate through file 'suburbs.csv' without using pandas
    with open('suburbs.csv', 'r') as f:
        # read the first line and ignore it
        next(f)
        # iterate until reaching eof
        for line in f:
            # split the line by comma
            parts = line.strip().split(',')
            # append the first part to the list
            suburbs.append(parts[0])

def initialize_contacts(level):
    # create dataframe fro csv file data 'contacts.csv' 
    # with columns name, lat_target, lon_target
    with open('contacts.csv', 'r') as f:
        colnames=["name", "lat_target", "lon_target", "activity_level"] 
        
        # header=0 is essential here otherwise the csv parser would assume four columns for some reason
        # also colnames lon_target, lat_target must be set 
        # so that they can be reference in the pdk.Layer 
        df = pd.read_csv(f, index_col=False, names=colnames, header=0)
        
    # add column 'lat_source' and 'lon_source' to contacts dataframe
    df['lat_source'] = CONTACT_SOURCE_LATITUDE
    df['lon_source'] = CONTACT_SOURCE_LONGITUDE
   
    df['dat'] = '2014-09-02 00:33:00'

    # remove lines from dataframe where column activity_level matches requested level
    df = df[df['activity_level'] == level]

    return df

def initialize():
    initialize_suburb_names()
    
    

def map_suburb_number_to_name(full_suburb_number):
    number_str = full_suburb_number.split('.')[0]
    number = int(number_str) - 1
    return suburbs[number]
     

def build_dataframe_poly(is_active_poly):
    json_data = pd.read_json('MUC_Stadtviertel_wgs84.json')
    rows = []

    for feature in json_data["features"]:
        coordinates = feature["geometry"]["coordinates"]
        vi_nummer = feature["properties"]["vi_nummer"]
        tag = map_suburb_number_to_name(vi_nummer)

        number_str = vi_nummer.split('.')[0]
        number = int(number_str) - 1
        # 4: Au-Haidhausen
        # 15: Ramersdorf-Perlach
        # 18: Thalkirchen-Obersendling-Forstenried
        if(is_active_poly==True): 
            if ((number == 4) or (number == 18) or (number ==15)):
                rows.append({
                    "coordinates": coordinates,
                    "tags": tag
                })
        else:
            if ((number != 4) and (number != 18) and (number !=15)):
                rows.append({
                    "coordinates": coordinates,
                    "tags": tag
                })
        

    df = pd.DataFrame(rows)
    return df  
       
def init_session_state():
    if "maplat" not in st.session_state:
        # U Maillinger Str
        st.session_state['maplat'] = 48.150368 
        st.session_state['maplon'] = 11.545566
              
init_session_state()
initialize()
raw_data_g42 = build_dataframe_g42_workshops()
data_g42 = pd.DataFrame(data=raw_data_g42)  
data_makerspaces = build_dataframe_makerspace()
data_makerspaces_static = build_dataframe_makerspace_static()
activity_level = 0
data_poi_inactive = initialize_pois(activity_level)
activity_level = 1
data_poi = initialize_pois(activity_level)
data_icon = pd.DataFrame(data=raw_data_g42)
is_active_poly = True
data_poly = build_dataframe_poly(is_active_poly)
is_active_poly = False
data_poly_inactive = build_dataframe_poly(is_active_poly)
activity_level = 1
data_contacts = initialize_contacts(activity_level)
activity_level = 0
data_contacts_inactive = initialize_contacts(activity_level)

#print(data_contacts['lat_target'].iloc[0])

with st.empty():
    
    layer_g42 = pdk.Layer(
                'ScatterplotLayer',
                data = data_g42,
                get_position = '[lon, lat]',
                get_color = '[0, 30, 200, 200]',
                get_radius = 250,
                pickable=True,
                auto_highlight=True,
                tooltip={"text": "{tags}"}
            )
    layer_makerspaces = pdk.Layer(
                'ScatterplotLayer',
                data = data_makerspaces,
                get_position = '[lon, lat]',
                get_color = '[200, 30, 0, 200]',
                get_radius = 250,     
                pickable=True,
                auto_highlight=True,
                tooltip={"text": "{tags}"}        
            )
    layer_makerspaces_static = pdk.Layer(
                'ScatterplotLayer',
                data = data_makerspaces_static,
                get_position = '[lon, lat]',
                get_color = '[200, 30, 0, 200]',
                get_radius = 250,
                pickable=True,
                auto_highlight=True,
                tooltip={"text": "{tags}"}
            )
    layer_poi = pdk.Layer(
            "ColumnLayer",
            data=data_poi,
            get_position=["lon", "lat"],
            get_elevation="count",
            elevation_scale=200,
            radius=30,
            get_fill_color=[255,0,0,255],
            pickable=True,
            auto_highlight=True,
            tooltip={"text": "{tags}"}
        )
    layer_poi_inactive = pdk.Layer(
            "ColumnLayer",
            data=data_poi_inactive,
            get_position=["lon", "lat"],
            get_elevation="count",
            elevation_scale=100,
            radius=30,
            get_fill_color=[255,255,255,255],
            pickable=True,
            auto_highlight=True,
            tooltip={"text": "{tags}"}
        )
            
    layer_suburbs = pdk.Layer(
                "PolygonLayer",
                data_poly,
                id = "geojson",
                opacity = 1.0,
                stroked = False,
                get_polygon = "coordinates",
                filled = True,
                extruded = True,
                wireframe = True,
                get_elevation = -10,
                get_fill_color = [64, 64, 255, 128],
                get_line_color = [0,102,169],
                auto_highlight = False,
                pickable = True,
            )
    layer_suburbs_active = pdk.Layer(
                "PolygonLayer",
                data_poly_inactive,
                id = "geojson",
                opacity = 1.0,
                stroked = False,
                get_polygon = "coordinates",
                filled = True,
                extruded = True,
                wireframe = True,
                get_elevation = -10,
                get_fill_color = [64, 64, 64, 128],
                get_line_color = [0,102,169],
                auto_highlight = False,
                pickable = True,
            )
    layer_contacts = pdk.Layer(
                'ArcLayer',
                data=data_contacts,
                get_source_position='[lon_source, lat_source]',
                get_target_position='[lon_target, lat_target]',
                get_source_color=[0, 0, 255, 255],
                get_target_color=[255, 255, 255, 255],
                get_radius=100,
                get_tilt=0,
                get_height=1,
                width_scale= 1
            )
    layer_icons = pdk.Layer(
                type = "IconLayer",
                data = data_icon,
                get_icon = "icon_data",
                get_size = 4,
                size_scale = 15,
                get_position = ['lon', 'lat'],
                get_elevation = 0,
                pickable = True,
                billboard = False,                
            )
    st.pydeck_chart(pdk.Deck(
        map_style='light',
        initial_view_state=pdk.ViewState(
            latitude=st.session_state['maplat'],
            longitude=st.session_state['maplon'],
            zoom=10.15,
            pitch=0,
        ),
        tooltip={"text": "{tags}"},
        layers=[layer_g42, layer_makerspaces, layer_makerspaces_static, layer_poi, layer_poi_inactive, layer_suburbs, layer_suburbs_active, layer_contacts, layer_icons ]
    ))




