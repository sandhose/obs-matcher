import json
import os
from pathlib import Path

from unidecode import unidecode
import requests


data = []


def load_data(app):
    global data
    if data:
        return data
    DATA_FILE = Path(app.instance_path).joinpath('countries.json')
    UPDATE_URL = 'https://raw.githubusercontent.com/mledoze/countries/' \
                 'master/dist/countries.json'
    try:
        data += json.load(open(str(DATA_FILE), 'r'))
    except OSError:
        r = requests.get(UPDATE_URL)
        assert r.status_code == 200
        data += r.json()
        os.makedirs(str(DATA_FILE.parent), exist_ok=True)
        with open(str(DATA_FILE), 'w') as handle:
            json.dump(data, handle)
    return data


def lookup(name):
    name = unidecode(name).lower()
    for country in data:
        if name.lower() in [s.lower() for s in country['altSpellings']]:
            return country['cca2']

        native = country['name'].get('native', False)
        native = list(native.values()) if native else []

        for translation in list(country['translations'].values()) \
                + [country['name']] + native:
            for attr in ['official', 'common']:
                n = unidecode(translation.get(attr, '')).lower()
                if n == name:
                    return country['cca2']

        for attr in ['cca3', 'ccn3', 'cioc']:
            n = unidecode(country.get(attr, '')).lower()
            if n == name:
                return country['cca2']

    return None
