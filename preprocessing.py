from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.impute import KNNImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
import numpy as np
import pandas as pd

DUMMY_ATTRS = [
    'Balcony',
    'Dishwasher',
    'In Unit Laundry',
    'On Site Laundry',
    'Assigned Parking',
    'Garage Parking',
    'Concierge Service',
]

NUM_ATTRS = [
    'lng',
    'lat',
    'Bedrooms',
    'Bathrooms',
    'Size',
    'index_right',
    'AREA_SHORT_CODE',
    'AREA_NAME',
    'Average Total Income',
    'Median Age',
    'Average Household Size',
    'Total private dwellings',
    'Average Commute Time',
    'Car, truck, van - as a driver %',
    'Car, truck, van - as a passenger %',
    'Public transit %',
    'Walked %',
    'Bicycle %',
    'Single-detached house %',
    'Apartment in a building w/ >= 5 stories %',
    'Semi-detached house %',
    'Row house %',
    'Apartment or flat in a duplex %',
    'Apartment in a building w/ < 5 stories %',
    'No certificate, diploma or degree',
    'Secondary (high) school diploma or equivalent',
    'Postsecondary certificate, diploma or degree',
    'geometry'
]

class SizeImputer(KNNImputer):
    def __init__(self, n_neighbors=5):
        # Features to base imputation on
        self.cols = ['Size', 'Bedrooms', 'Bathrooms', 'lng', 'lat']
        super().__init__(n_neighbors=n_neighbors, copy=True)

    def fit(self, X, y=None):
        tr_X = X[self.cols]
        return super().fit(tr_X)

    def transform(self, X):
        tr_X = X[self.cols]
        X[['Size']] = super().transform(tr_X)[:, 0]
        return X

class FeatureCombiner(BaseEstimator, TransformerMixin):
    def __init__(self, mul=True):
        self.multiply = mul

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        if self.multiply:
            X['Bed*Bath'] = X['Bedrooms'] * X['Bathrooms']
        else:
            X['Bed+Bath'] = X['Bedrooms'] + X['Bathrooms']
        X = X.drop(['Bedrooms', 'Bathrooms'], axis=1)
        return X


class FeatureDropper(BaseEstimator, TransformerMixin):
    # For dropping extra attributes and fixing Laundry attribute
    def __init__(self, dwellings=False, education=False, commute=False, pvt_dwellings=False, m_age=False):
        self.dwellings = dwellings
        self.education = education
        self.commute = commute
        self.pvt_dwellings = pvt_dwellings
        self.m_age = m_age

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        X = X.drop(['index_right', 'AREA_SHORT_CODE', 'AREA_NAME', 'geometry'], axis=1)
        if self.dwellings:
            X = X.drop([
                'Single-detached house %',
                'Semi-detached house %',
                'Row house %',
                'Apartment or flat in a duplex %',
                'Apartment in a building w/ < 5 stories %',
            ], axis=1)
        if self.education:
            X = X.drop([
                'No certificate, diploma or degree',
                'Secondary (high) school diploma or equivalent',
            ], axis=1)
        if self.commute:
            X = X.drop([
                'Car, truck, van - as a driver %',
                'Car, truck, van - as a passenger %',
            ], axis=1)
        if self.pvt_dwellings:
            X = X.drop(['Total private dwellings'], axis=1)
        if self.m_age:
            X = X.drop(['Median Age'], axis=1)
        return X

def pipeline(n_neighbors=5, mul=True):
    num_pipeline = Pipeline([
        ('size_imputer', SizeImputer(n_neighbors=n_neighbors)),
        ('bed+bath_combiner', FeatureCombiner(mul=mul)),
        ('feature_dropper', FeatureDropper(
            dwellings=True,
            education=True,
            commute=True,
            pvt_dwellings=True,
            m_age=True
        )),
        ('std_scaler', StandardScaler())
    ])

    data_pipeline = ColumnTransformer([
        ('num', num_pipeline, NUM_ATTRS),
        ('cat', 'passthrough', DUMMY_ATTRS)
    ])

    return data_pipeline
