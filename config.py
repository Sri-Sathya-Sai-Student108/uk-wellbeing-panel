"""
Configuration and ONS Area Classification lookups.
"""

DATA_DIR = "data"
OUTPUT_DIR = "output"

MEASURES = ['life-satisfaction', 'worthwhile', 'happiness', 'anxiety']

MEASURE_LABELS = {
    'life-satisfaction': 'Life Satisfaction',
    'worthwhile': 'Worthwhile',
    'happiness': 'Happiness',
    'anxiety': 'Anxiety'
}

# ONS 2011 Area Classification for Local Authorities (version 2)
# 8 Supergroups, 16 Groups, 24 Subgroups
SUPERGROUP_NAMES = {
    '1': 'Affluent England',
    '2': 'Business, Education and Heritage Centres',
    '3': 'Countryside Living',
    '4': 'Ethnically Diverse Metropolitan Living',
    '5': 'London Cosmopolitan',
    '6': 'Services and Industrial Legacy',
    '7': 'Town and Country Living',
    '8': 'Urban Settlements'
}

GROUP_NAMES = {
    '1a': 'Rural-Urban Fringe',
    '1b': 'Prosperous Semirural',
    '1c': 'Commuter Suburbs',
    '2a': 'University Cities and Towns',
    '2b': 'Regional Centres',
    '3a': 'Rural England',
    '3b': 'Rural Wales and Scotland',
    '4a': 'Inner London Diversity',
    '4b': 'Outer London and Urban Fringe',
    '5a': 'Central London',
    '5b': 'Inner London Terraces',
    '6a': 'Former Mining and Industrial',
    '6b': 'Seaside and Industrial Legacy',
    '7a': 'Market Towns',
    '7b': 'Mixed Rural',
    '8a': 'Manufacturing Traits',
    '8b': 'Suburban Traits'
}
