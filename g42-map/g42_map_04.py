import streamlit as st
import pandas as pd
import numpy as np
import pydeck as pdk
import requests
import json
from pydeck.types import String
import math

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
    d = {
        'lat': [48.1231168709479, 48.12902956184886, 48.12564020411458, 48.158668521339685, 48.13082479077407, 48.14215853679493, 48.17730210285392, 48.1031950282566], 
        'lon': [11.556521818246615, 11.602367411348682, 11.605100109496648, 11.550326266563493, 11.591690781905553, 11.515945526085256, 11.722072468415234, 11.427128268104944], 
        'name': ['Erfindergarten', 'Haus der Eigenarbeit', 'Precious Plastic', 'Werkbox 3', 'Werkzeugbibliothek', 'Machwerk', 'Teamwerk', 'machBar']
    }
    df = pd.DataFrame(data=d)
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

    icon_data = {
        # Icon from Wikimedia, used the Creative Commons Attribution-Share Alike 3.0
        # Unported, 2.5 Generic, 2.0 Generic and 1.0 Generic licenses
        "url": ICON_URL,
        "width": 43,
        "height": 64,
        "anchorY": 64,
    }    
    
    d = {'name': [], 'lat': [], 'lon': [], 'tags': [], 'icon_data': []}
    for item in workshops:
        label, lat, lon = get_wikidata_coordinate_location(url, item, property_coordinates)
        d['name'].append(label)
        d['lat'].append(lat)
        d['lon'].append(lon)
        d['tags'].append(label)
        d['icon_data'].append(icon_data)
    
    return d
 

def build_dataframe_makerspace():
    
    spaces = get_makerspaces()
    #print("Makerspaces")
    #print(spaces)
    
    url = "https://www.wikidata.org/w/api.php"
    property_coordinates = 'P625'
    
    d = {'name': [], 'lat': [], 'lon': []}
    for item in spaces:
        label, lat, lon = get_wikidata_coordinate_location(url, item, property_coordinates)
        d['name'].append(label)
        d['lat'].append(lat)
        d['lon'].append(lon)
    
    df = pd.DataFrame(data=d)
    return df
     
suburb_names = ['Altstadt-Lehel', 'Ludwigvorstadt-Isarvorstadt', 'Maxvorstadt', 'Schwabing-West', 'Au-Haidhausen',
"Sendling", "Sendling-Westpark", "Schwanthalerhöhe", "Neuhausen-Nymphenburg", "Moosach", "Milbertshofen-Am Hart",
"Schwabing-Freimann", "Bogehausen", "Berg am Laim", "Trudering-Riem", "Ramersdorf-Perlach", "Obergiesing-Fasangarten",
"Untergiesing-Harlaching", "Thalkirchen-Obersendling-Forstenried", "Hadern", "Pasing-Obermenzing", "Aubing-Lochhausen-Langwied",
"Allach-Untermenzing", "Feldmoching-Hasenbergl", "Laim"]
     
def map_suburb_number_to_name(full_suburb_number):
    number_str = full_suburb_number.split('.')[0]
    number = int(number_str) - 1
    return suburb_names[number]
     
def build_dataframe_poly():

    json = pd.read_json('MUC_Stadtviertel_wgs84.json')
    df = pd.DataFrame()
    df["coordinates"] = json["features"].apply(lambda row: row["geometry"]["coordinates"])
    df["tags"] = json["features"].apply(lambda row: map_suburb_number_to_name(row["properties"]["vi_nummer"]))
                
    return df
       
def init_session_state():
    if "maplat" not in st.session_state:
        # U Maillinger Str
        st.session_state['maplat'] = 48.150368 
        st.session_state['maplon'] = 11.545566
              
init_session_state()
raw_data_g42 = build_dataframe_g42_workshops()
data_g42 = pd.DataFrame(data=raw_data_g42)  
data_makerspaces = build_dataframe_makerspace()
data_makerspaces_static = build_dataframe_makerspace_static()
data_icon = pd.DataFrame(data=raw_data_g42)
data_poly = build_dataframe_poly()


with st.empty():
    st.pydeck_chart(pdk.Deck(
        map_style='light',
        initial_view_state=pdk.ViewState(
            latitude=st.session_state['maplat'],
            longitude=st.session_state['maplon'],
            zoom=10.15,
            pitch=0,
        ),
        tooltip={"text": "{tags}"},
        layers=[
            pdk.Layer(
                'ScatterplotLayer',
                data = data_g42,
                get_position = '[lon, lat]',
                get_color = '[0, 30, 200, 200]',
                get_radius = 400,
            ),
            pdk.Layer(
                'ScatterplotLayer',
                data = data_makerspaces,
                get_position = '[lon, lat]',
                get_color = '[200, 30, 0, 200]',
                get_radius = 250,
            ),
            pdk.Layer(
                'ScatterplotLayer',
                data = data_makerspaces_static,
                get_position = '[lon, lat]',
                get_color = '[200, 30, 0, 200]',
                get_radius = 250,
            ),
            pdk.Layer(
                type = "IconLayer",
                data = data_icon,
                get_icon = "icon_data",
                get_size = 4,
                size_scale = 15,
                get_position = ['lon', 'lat'],
                get_elevation = 0,
                pickable = True,
            ),            
            pdk.Layer(
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
                get_fill_color = [64, 64, 64, 128],
                get_line_color = [0,102,169],
                auto_highlight = False,
                pickable = True,
            )
        ]
    ))




