import pandas as pd
import geopandas as gpd
import numpy as np
import sklearn as sk
import os
from sklearn.model_selection import StratifiedShuffleSplit

NBHDS_PATH = os.path.join("data", "Neighbourhoods.geojson")
NBHD_PROFILES_PATH = os.path.join("data", "neighbourhood_profiles.csv")
RENT_LISTINGS_PATH = os.path.join("data", "rent_data.csv")
DF_FINAL_PATH = os.path.join('data', 'rent_final.geojson')


def _load_data():
    data_matrix = gpd.read_file(DF_FINAL_PATH)
    data_matrix = data_matrix[data_matrix['Bathrooms'].notna()]

    # Removing points in certain neighbourhoods so that we can use stratified splitting
    remove_nbhds = [3.0, 5.0, 133.0, 21.0]
    data_matrix = data_matrix[~data_matrix["AREA_SHORT_CODE"].isin(remove_nbhds)]

    # Make 'Laundry' feature into one hot vector
    data_matrix['On Site Laundry'] = data_matrix[['On Site Laundry']].replace({2: 1})

    # Make 'Price' values in 1000s ($)
    data_matrix['Price'] = data_matrix['Price'] / 1000

    # Remove outliers and fix data collection mistakes
    data_matrix.drop(index=2663, inplace=True) # Listing error
    data_matrix.drop(index=2752, inplace=True) # Parsing error
    data_matrix.loc[data_matrix.index == 6006, 'Price'] = 9.5 # Update listing; parsing error
    data_matrix['Bathrooms'] = data_matrix[['Bathrooms']].replace({11: 1, 21: 2}) # Parsing error: 11 -> 1, 21 -> 2
    return data_matrix

def train_test_split(test_prop=0.15):
    data_matrix = _load_data()
    # Stratify on area code
    split = StratifiedShuffleSplit(n_splits = 1, test_size=test_prop, random_state=69)
    for train_idx, test_idx in split.split(data_matrix, data_matrix[['AREA_SHORT_CODE']]):
        training_set = data_matrix.iloc[train_idx]
        test_set = data_matrix.iloc[test_idx]
    return {
        'train': {
            'data': training_set.drop('Price', axis=1),
            'labels': training_set['Price'].copy()
        },
        'test': {
            'data': test_set.drop('Price', axis=1),
            'labels': test_set['Price'].copy()
        }
    }
