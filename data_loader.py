import json
import os

# Loads all the data from the data folder and the kits folder and returns it as a dictionary

def load_data():
    data = {}
    folders = ['data','./data/kits']

    # Loop through each folder and load the JSON files into the data dictionary
    for folder in folders:
        for file in os.listdir(folder):
            if file.endswith('.json'):
                with open(os.path.join(folder, file), 'r') as f:
                    data[file.removesuffix(".json")] = json.load(f)
    return data

# Load the data when the module is imported
data = load_data()