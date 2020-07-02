import matplotlib
matplotlib.use('Agg')

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import pickle
import requests
import json
import airbnb


import branca
from scipy.interpolate import griddata
import geojsoncontour
import scipy as sp
import scipy.ndimage
import numpy.ma as ma

import geopandas as gpd
import geopy.distance
from shapely.geometry import Point
from descartes.patch import PolygonPatch
from matplotlib.pyplot import cm

import folium
import inquirer
import psycopg2

import pdb

import googlemaps
from datetime import datetime


#######################################################################################

def extract_coordinates(geocode_result):
    #
    # Get Zip Code
    for i in range(0,len(geocode_result[0]['address_components'])):
        if geocode_result[0]['address_components'][i]['types']== ['postal_code']:
            zc = geocode_result[0]['address_components'][i]['long_name']
            
    # Get Lattitude and Longitude       
    pl_lat = geocode_result[0]['geometry']['location']['lat']
    pl_lng = geocode_result[0]['geometry']['location']['lng']
    
    return (int(zc), pl_lat,pl_lng)
    
#######################################################################################

def calculate_centerpoint(zc,pl_lat,pl_lng,points,all_zipcodes):
    distances = np.zeros(len(points))
    coords_1 = (pl_lat,pl_lng)
    #
    for j in range(0,len(points)):
        coords_2 = (points[j][0],points[j][1])
        distances[j]= geopy.distance.geodesic(coords_1, coords_2).km
    #    
    mindistance_index = distances.argmin()
    nearest_zipcode = all_zipcodes['zipcode'][mindistance_index]
    place = all_zipcodes['place_name'][mindistance_index]
    return nearest_zipcode,place
        
#######################################################################################

def get_datafromDB(nearest_zipcode,time):

    HOST, PORT, DB, PASSWORD= open("config.txt","r").read().split()
    connect_str =  "host=" + HOST + " port=" + str(PORT) + " dbname=" + DB + " user=" + DB + " 
    # Connect to Server
    connection = psycopg2.connect(connect_str)
    cursor = connection.cursor()

    if connection:
        print ('You are connected to Database on AWS')
    #    
    # Get Data    
    postgres_select_query = 'SELECT destination_zipcode, transit_time_now,transit_time_traffic FROM public."distance_matrix" WHERE origin_zipcode= ' + str(nearest_zipcode) + " AND start_time = '" + str(time)+"'"
    cursor.execute(postgres_select_query)
    record = cursor.fetchall()
    
    record = pd.DataFrame(record, columns = ['zipcode', 'transit_time_now', 'transit_time_traffic'])
    #
    # Close connection
    if connection:
        cursor.close()
        connection.close()
        print("PostgreSQL connection is closed")  
        
    #
    # Return dataset
    return record
    
#######################################################################################

def getbounds(latitude,longitude, buffer_radius):
    center_point = Point((latitude,longitude))
    df = pd.DataFrame({'id': ['Center Point']})
    gdf = gpd.GeoDataFrame(df, geometry = [center_point])
    buffer = gdf.geometry.buffer(buffer_radius).envelope
    return buffer.bounds
    
#######################################################################################
   
def get_airbnb_listings(place):
    #
    if place == 'Wholesale district':
        place = 'Little Tokyo'
    
    api = airbnb.Api(randomize=True)
    #login = 'sdivya.swaminathan@gmail.com'
    #password = 'physics241'
    #api = airbnb.Api(login, password)
    api = airbnb.Api(access_token='5pfs1hfp74rggqj6kdqk7d6v8')
    
    #
    dict = api.get_homes(place, items_per_grid = 10)
    if  (dict['explore_tabs'][0]['sections'][0]['result_type'] == 'messages'):
        print ('No Listing Found, try another place')
    else:    
        num_of_listings = len(dict['explore_tabs'][0]['sections'][0]['listings'])
        print ('Number of Listings found',num_of_listings )
    #    
        lat=list()
        lng = list()
        local_neighborhood = list()
        price = list()
        link = list()
        for i in range(0,num_of_listings):
            lat1 = dict['explore_tabs'][0]['sections'][0]['listings'][i]['listing']['lat']
            long1 = dict['explore_tabs'][0]['sections'][0]['listings'][i]['listing']['lng']
            local_neighborhood1 = dict['explore_tabs'][0]['sections'][0]['listings'][i]['listing']['localized_neighborhood']
            price1 = dict['explore_tabs'][0]['sections'][0]['listings'][i]['pricing_quote']['rate']['amount_formatted']
            id1 = dict['explore_tabs'][0]['sections'][0]['listings'][i]['listing']['id']
            link1 = 'https://www.airbnb.com/rooms/%d'%(id1)
            lat.append(lat1)
            lng.append(long1)
            local_neighborhood.append(local_neighborhood1)
            price.append(price1)
            link.append(link1)
      
    d = {'lat':lat, 'lng':lng  ,'local_neighborhood': local_neighborhood,'price': price,'link': link}
    listings_df = pd.DataFrame.from_dict(d)
    
    return listings_df
#######################################################################################
# Selects apartments in a particular zipcode
def select_apartments_zc(apartments,zc):

    new_df = apartments[apartments['Zipcode']==zc]
    new_df = new_df.reset_index(drop = True)
    return new_df
#######################################################################################

def my_func(lat,lon,center_coordinate):
    coordinate = ([lat,lon])
    distance= geopy.distance.geodesic(center_coordinate, coordinate).km    
    return distance
    
#######################################################################################
def select_apartments_nearest_zipcodes(apartments,zc,center_coordinate,threshold):

    XX = apartments.groupby('Zipcode').mean()
    XX['distance_to_zc']=XX.apply(lambda row: my_func(row['latitude'],row['longitude'],center_coordinate) ,axis=1)
    new_XX = XX.sort_values(by = 'distance_to_zc')
    new_list = new_XX.index[new_XX['distance_to_zc']<= threshold].to_list()
    selected_apartments= apartments[apartments['Zipcode'].isin(new_list)]
    #selected_apartments = selected_apartments.sample(sample_size)
    selected_apartments = selected_apartments.reset_index(drop = True)
    return selected_apartments
    
    
#######################################################################################
#
def set_up_map(geojson,bb,pl_lat,pl_lng,center_lat,center_long,cm):

    #geomap = folium.Map([pl_lat,pl_lng], zoom_start=10,tiles="cartodbpositron" )
    geomap = folium.Map([pl_lat,pl_lng], zoom_start=10,width = 1000, height = 600)
    geomap.fit_bounds([[bb.minx[0], bb.miny[0]], [bb.maxx[0], bb.maxy[0]]])
    folium.Marker(location = [center_lat,center_long],popup='Starting Zipcode',icon=folium.Icon(color='red', icon='info-sign')).add_to(geomap)
    folium.GeoJson(
        geojson,
        style_function=lambda x: {
            'color':     x['properties']['stroke'],
            'weight':    x['properties']['stroke-width'],
            'fillColor': x['properties']['fill'],
            'opacity':   0.5,
        }).add_to(geomap)
    cm.caption = 'Driving Times (mins)'
    geomap.add_child(cm)
    
    return geomap
        
#######################################################################################

## This should take form of a funtion with 2 user inputs place and time
## that come from using the input.html
def CalculateMap(place,time):

    print ('Building Map')

    gmaps = googlemaps.Client(key='AIzaSyCNrSB13MN2K3ysapY0EFD7rmtKBFVRn_8')

    geocode_result = gmaps.geocode(place)

    (zc,pl_lat,pl_lng) = extract_coordinates(geocode_result)
    
    center_coordinate = ([pl_lat,pl_lng])
    
    # zc = 90028
#     pl_lat = 34.101323
#     pl_lng = -118.339741
    

    pickle_in = open('zipcode.pkl','rb')
    all_zipcodes = pickle.load(pickle_in)
    grid_points = all_zipcodes[['latitude','longitude']].values

    [nearest_zipcode,place] = calculate_centerpoint(zc,pl_lat,pl_lng,grid_points,all_zipcodes)

    record1 = get_datafromDB(nearest_zipcode,time)
    
    #print (record1)

    DF_toplot= pd.merge(record1, all_zipcodes, on ='zipcode')
    ff = DF_toplot.sort_values(by = 'transit_time_now')
    ff = ff.reset_index(drop=True)

    #print(ff.head())
    
    center_lat = ff['latitude'][0]
    center_long = ff['longitude'][0]
    bb = getbounds(center_lat, center_long, 0.05)

    debug = False

# Setup colormap
    vmin   = ff['transit_time_traffic'].min()
    vmax   = ff['transit_time_traffic'].max()
    
    print ('******** Set Colorbar *********')

    # colors = ['#000080', '#0000ff', '#0063ff','#00d4ff','#4effa9','#a9ff4e','#ffe600','#ff7d00','#ff1400','#800000']
#     levels = len(colors)
#     cm = branca.colormap.LinearColormap(colors, vmin=vmin, vmax=vmax).to_step(levels)

    colors = ['#000080', '#0080ff','#7bff7b','#ff9700','#800000' ]
    levels = len(colors)
    cm = branca.colormap.LinearColormap(colors, vmin=vmin, vmax=vmax).to_step(levels)


 # The original data
    print ('******** Get Data *********')
    x_orig = np.asarray(ff.longitude.tolist()) # long
    y_orig = np.asarray(ff.latitude.tolist()) # lat
    z_orig = np.asarray(ff['transit_time_traffic'].tolist())

# Make a grid
    print ('******** Make a grid *********')
    n_grid = 100
    x_arr = np.linspace(np.min(x_orig), np.max(x_orig), n_grid)
    y_arr = np.linspace(np.min(y_orig), np.max(y_orig), n_grid)
    x_mesh, y_mesh = np.meshgrid(x_arr, y_arr)
    
# Grid the values
    print ('******** Create Z mesh *********')
    z_mesh = griddata((x_orig, y_orig), z_orig, (x_mesh, y_mesh), method='cubic')

# Gaussian filter the grid to make it smoother
    if n_grid>=300:
        sigma = [5, 5]
        z_mesh = sp.ndimage.filters.gaussian_filter(z_mesh, sigma, mode='constant')

    
# Create the contour
    #contourf = plt.contourf(x_mesh, y_mesh, z_mesh, levels, linestyles='None', vmin=vmin, vmax=vmax)
    print ('******** Get Countourf *********')
    contourf = plt.contourf(x_mesh, y_mesh, z_mesh, cmap = plt.cm.jet , alpha=0.75,linestyles='None',vmin=vmin, vmax=vmax )


    
# Convert matplotlib contourf to geojson
    print ('******** Save geojson *********')
    geojson = geojsoncontour.contourf_to_geojson(
            contourf=contourf,
            min_angle_deg=3.0,
            ndigits=5,
            stroke_width=2,
            fill_opacity=1.0)
            
    # cm.caption = 'Driving Times (mins)'
#     geomap.add_child(cm)
    
#    return geojson

    Mapit = set_up_map(geojson,bb,pl_lat,pl_lng,center_lat,center_long,cm)
    
    #pdb.set_trace()

    print('*****',place, 'and now we are accessing Airbnb')

    listings_df = get_airbnb_listings(place)
    
    if not listings_df.empty:
        for i in range(0,len(listings_df)):
            link_html = '<a href="{0}" rel="noopener noreferrer" target="_blank"> {1} </a>'.format(listings_df['link'][i], listings_df['local_neighborhood'][i])
            my_string = 'Place :{0}, Price: {1}'.format(link_html, listings_df['price'][i])
            mypopup = folium.Popup(folium.IFrame(my_string, width = 220, height = 50), max_width=2650)
            folium.Marker([listings_df['lat'][i], listings_df['lng'][i]], 
                          icon=folium.Icon(color='green', icon='home'),
                           popup= mypopup).add_to(Mapit)
    else:
        print ('No Listings Found')                       
#                   
    print('Get Apartments.com data and plot rentals')
    
    pickle_in = open('Final_ApartmentList.pkl','rb')
    apartments = pickle.load(pickle_in)
    
    # Threshold sets distance threshold. You will return all the rental listings within 
    # this boundary. But randomly sample them as it could be a lot of listings- 
    threshold = 2.5
    sample_number = 20
    
    dfg = select_apartments_nearest_zipcodes(apartments,zc,center_coordinate,threshold)
    dfg = dfg.sample(sample_number).reset_index(drop = True)
    
    
    for i in range(0,len(dfg)):
        link_html = '<a href="{0}" rel="noopener noreferrer" target="_blank"> {1} </a>'.format(dfg['Link'][i], dfg['Title'][i])
        my_string = 'Place :{0}, Price: {1}'.format(link_html, dfg['Price'][i])
        mypopup = folium.Popup(folium.IFrame(my_string, width = 220, height = 50), max_width=2650)
        folium.Marker([dfg['latitude'][i], dfg['longitude'][i]],icon=folium.Icon(color='orange', icon='home'),
                      popup= mypopup).add_to(Mapit)


    return Mapit
    
#######################################################################################
