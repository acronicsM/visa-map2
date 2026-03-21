import json

with open('geodata.json', encoding='utf-8') as f:
    data = json.load(f)
aus = [f for f in data['features'] if f['properties']['iso2'] == 'AU']
print('AU count:', len(aus))
print('Total features:', len(data['features']))
if aus:
    print('AU props:', aus[0]['properties'])
else:
    print('AU NOT FOUND')