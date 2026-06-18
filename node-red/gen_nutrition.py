"""Extend calories.json with estimated macros (protein/fat/carbs grams per serving).

Macros are estimated from kcal using category-based macro splits
(protein/carbs = 4 kcal/g, fat = 9 kcal/g). Clearly approximate — good enough
for a tracking demo; swap in a real nutrition DB later for production.
"""
import json, os, re

base = os.path.dirname(os.path.abspath(__file__))
src = json.load(open(os.path.join(base, '..', 'data', 'calories.json'), encoding='utf-8'))

# (protein%, fat%, carb%) of calories, by category keywords (first match wins)
CATS = [
    (r'cake|pie|pudding|donut|beignet|baklava|cannoli|churro|mousse|brulee|cotta|tiramisu|macaron|cupcake|shortcake|red_velvet|ice_cream|frozen_yogurt|waffle|pancake|french_toast|cheesecake|bread_pudding', (8, 38, 54)),
    (r'fries|onion_rings|calamari|nachos|poutine|spring_rolls|samosa|falafel|croquet', (10, 48, 42)),
    (r'steak|ribs|filet|prime_rib|pork|chop|duck|foie|carpaccio|tartare|escargot|brisket', (38, 54, 8)),
    (r'chicken|wings|quesadilla|hamburger|hot_dog|club_sandwich|pulled_pork|lobster_roll|grilled_cheese|croque|breakfast_burrito', (26, 40, 34)),
    (r'salmon|sashimi|sushi|oyster|mussel|scallop|shrimp|tuna|ceviche|crab|fish_and_chips|paella|takoyaki', (44, 30, 26)),
    (r'spaghetti|lasagna|risotto|ramen|pho|pad_thai|fried_rice|gnocchi|ravioli|macaroni|noodle|bibimbap|dumpling|gyoza', (18, 27, 55)),
    (r'salad|edamame|hummus|guacamole|caprese|bruschetta|beet|seaweed|deviled_eggs', (18, 46, 36)),
    (r'soup|chowder|bisque|miso', (22, 33, 45)),
    (r'omelette|eggs_benedict|huevos', (28, 55, 17)),
]
DEFAULT = (18, 37, 45)

def split(name):
    for pat, s in CATS:
        if re.search(pat, name):
            return s
    return DEFAULT

out = {}
for food, v in src.items():
    kcal = v['kcal']
    p, f, c = split(food)
    out[food] = {
        'kcal': kcal,
        'serving': v['serving'],
        'protein': round(kcal * p / 100 / 4),
        'fat': round(kcal * f / 100 / 9),
        'carbs': round(kcal * c / 100 / 4),
    }

# write to data/ (source of truth) and node-red/model/ (served to the UI)
json.dump(out, open(os.path.join(base, '..', 'data', 'calories.json'), 'w', encoding='utf-8'), indent=2)
json.dump(out, open(os.path.join(base, 'model', 'calories.json'), 'w', encoding='utf-8'), indent=2)
print('nutrition written for %d foods. sample:' % len(out))
for k in list(out)[:3]:
    print(' ', k, out[k])
