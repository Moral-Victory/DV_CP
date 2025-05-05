import numpy as np
import pandas as pd
from scipy.stats import skewnorm
from scipy.special import expit
from pymongo import MongoClient
import os
from datetime import datetime, timedelta

# 1. Load & rename
def generate_data():
    # If available, use original dataset, otherwise generate synthetic data
    try:
        df_base = pd.read_csv('ai4i2020.csv')
        df_base.rename(columns={
            'Air temperature [K]': 'Air temperature',
            'Process temperature [K]': 'Process temperature',
            'Rotational speed [rpm]': 'Rotational speed',
            'Torque [Nm]': 'Torque',
            'Tool wear [min]': 'Tool wear'
        }, inplace=True)
    except:
        # Generate synthetic data if original file is not available
        print("Original dataset not found, generating synthetic data...")
        np.random.seed(42)
        n = 1000
        
        # Generate random data with realistic ranges
        df_base = pd.DataFrame({
            'Air temperature': np.random.normal(300, 5, n),
            'Process temperature': np.random.normal(310, 5, n),
            'Rotational speed': np.random.normal(1500, 100, n),
            'Torque': np.random.normal(40, 10, n),
            'Tool wear': np.random.uniform(0, 200, n),
            'UDI': [f'L{i:04d}' for i in range(1, n+1)],
            'Product ID': np.random.choice(['L', 'M', 'H'], n),
            'Type': np.random.choice(['L', 'M', 'H'], n)
        })
        
        # Ensure some correlation between variables
        df_base['Process temperature'] = df_base['Air temperature'] + np.random.normal(10, 2, n)
        df_base['Torque'] = 0.02 * df_base['Rotational speed'] + np.random.normal(0, 5, n)

    # 2. Constants & shifts
    feature_cols = ['Air temperature', 'Process temperature',
                    'Rotational speed', 'Torque', 'Tool wear']
    nominal = {
        'speed': df_base['Rotational speed'].mean(),
        'torque': df_base['Torque'].mean(),
        'wear_max': df_base['Tool wear'].max(),
        'temp_shift': 10
    }
    weights = {'temp': 0.2, 'speed': 0.25, 'torque': 0.25, 'wear': 0.3}
    shifts = {
        'very_good': {'air_temp': -3, 'proc_temp': -2, 'speed_pct': 1.05, 'torque_pct': 1.05, 'wear_pct': 0.90},
        'good': {'air_temp': 0, 'proc_temp': 0, 'speed_pct': 1.00, 'torque_pct': 1.00, 'wear_pct': 1.00},
        'ok': {'air_temp': +3, 'proc_temp': +2, 'speed_pct': 0.95, 'torque_pct': 0.95, 'wear_pct': 1.10},
        'very_bad': {'air_temp': +6, 'proc_temp': +4, 'speed_pct': 0.90, 'torque_pct': 0.90, 'wear_pct': 1.20}
    }

    # 3. Precompute σ for noise
    stds = df_base[feature_cols].std()

    # 4. Skewness parameters (a > 0 → right‐skew, a < 0 → left‐skew)
    skew_params = {
        'very_good': {'Air temperature': -4, 'Process temperature': -3,
                    'Rotational speed': 4, 'Torque': 3, 'Tool wear': -5},
        'good': {'Air temperature': 0, 'Process temperature': 0,
                'Rotational speed': 0, 'Torque': 0, 'Tool wear': 0},
        'ok': {'Air temperature': 2, 'Process temperature': 2,
            'Rotational speed': -2, 'Torque': -2, 'Tool wear': 2},
        'very_bad': {'Air temperature': 5, 'Process temperature': 4,
                    'Rotational speed': -5, 'Torque': -4, 'Tool wear': 6}
    }

    # 5. Enrichment
    def enrich(df):
        d = df.copy()
        vib_raw = 0.6 * d['Torque'] + 0.4 * d['Tool wear'] + np.random.normal(0, 2, len(d))
        d['Vibration'] = 100 * (vib_raw - vib_raw.min()) / (vib_raw.max() - vib_raw.min())
        h_temp = 1 - (abs(d['Air temperature'] - 300) / nominal['temp_shift']).clip(0, 1)
        h_speed = (d['Rotational speed'] / nominal['speed']).clip(0, 1)
        h_torque = (d['Torque'] / nominal['torque']).clip(0, 1)
        h_wear = (1 - d['Tool wear'] / nominal['wear_max']).clip(0, 1)
        d['Health score'] = 100 * (
            weights['temp'] * h_temp +
            weights['speed'] * h_speed +
            weights['torque'] * h_torque +
            weights['wear'] * h_wear
        )
        p_fail = 1 - expit((d['Health score'] - 50) / 10)
        d['Failure'] = np.random.binomial(1, p_fail, size=len(d))
        d['Uptime'] = 100 - 10 * d['Failure'] - np.random.uniform(0, 20, size=len(d)) * (d['Failure'] * 0.8 + 0.2)
        return d

    # 6. Enrich original
    df_orig = enrich(df_base)

    # 7. Build with skewed noise
    def build(state, noise_frac=0.05):
        s = shifts[state]
        d = df_base.copy()
        # apply shifts
        d['Air temperature'] += s['air_temp']
        d['Process temperature'] += s['proc_temp']
        d['Rotational speed'] *= s['speed_pct']
        d['Torque'] *= s['torque_pct']
        d['Tool wear'] *= s['wear_pct']
        # add skewed noise
        for f in feature_cols:
            a = skew_params[state][f]
            scale = stds[f] * noise_frac
            d[f] += skewnorm.rvs(a, loc=0, scale=scale, size=len(d))
        return enrich(d)

    # 8. Generate datasets
    datasets = {st: build(st) for st in shifts}
    
    # Map lathe conditions to lathe IDs
    lathe_ids = {
        'very_good': 1,  # M1
        'good': 3,       # M3
        'ok': 2,         # M2
        'very_bad': 4    # M4
    }
    
    # Create failure types
    failure_types = ['TWF', 'HDF', 'PWF', 'OSF', 'RNF']
    
    # Process each dataset and prepare for MongoDB
    final_datasets = {}
    for state, df in datasets.items():
        # Add LatheID
        df['LatheID'] = lathe_ids[state]
        
        # Add failure flags
        if 'Failure' in df.columns:
            for failure_type in failure_types:
                # Generate failure flags with higher probability for worse states
                if state == 'very_bad':
                    prob = 0.3
                elif state == 'ok':
                    prob = 0.1
                elif state == 'good':
                    prob = 0.03
                else:  # very_good
                    prob = 0.01
                    
                # For failed machines, distribute the failures across types
                df[failure_type] = np.where(
                    df['Failure'] == 1,
                    np.random.choice([0, 1], size=len(df), p=[1-prob, prob]),
                    0
                )
                
        # Add missing columns if not present
        if 'UDI' not in df.columns:
            df['UDI'] = [f'L{i:04d}' for i in range(1, len(df)+1)]
        
        if 'Product ID' not in df.columns:
            df['Product ID'] = np.random.choice(['L', 'M', 'H'], len(df))
            
        if 'Type' not in df.columns:
            df['Type'] = np.random.choice(['L', 'M', 'H'], len(df))
            
        # Add a timestamp field for each record
        now = datetime.now()
        timestamps = [now - timedelta(hours=i) for i in range(len(df))]
        df['timestamp'] = timestamps
        
        final_datasets[state] = df
        
    return final_datasets, lathe_ids

def upload_to_mongodb(datasets, lathe_ids):
    # Connect to MongoDB (adjust connection string as needed)
    try:
        client = MongoClient("mongodb://localhost:27017/")
        db = client["lathe_maintenance"]
        print("Connected to MongoDB successfully!")
    except Exception as e:
        print(f"Failed to connect to MongoDB: {e}")
        return False
    
    # Insert data for each lathe
    for state, df in datasets.items():
        lathe_id = lathe_ids[state]
        collection_name = f"lathe_m{lathe_id}"
        
        # Drop existing collection if it exists
        db.drop_collection(collection_name)
        
        # Convert dataframe to dictionary records
        records = df.to_dict("records")
        
        # Insert records
        collection = db[collection_name]
        collection.insert_many(records)
        print(f"Inserted {len(records)} records for {collection_name}")
    
    return True

if __name__ == "__main__":
    datasets, lathe_ids = generate_data()
    upload_to_mongodb(datasets, lathe_ids)
    print("Data generation and upload complete!")