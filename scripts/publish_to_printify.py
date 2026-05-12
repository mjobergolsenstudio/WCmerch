import os
import json
import requests
from pathlib import Path
import base64

API_KEY = os.environ[“PRINTIFY_API_KEY”]
ANTHROPIC_API_KEY = os.environ[“ANTHROPIC_API_KEY”]

SHOP_IDS = [
{“id”: “27515383”, “name”: “Shopify (wcmerch.shop)”},
{“id”: “27515021”, “name”: “Etsy (World Cup Merch)”},
]

HEADERS = {
“Authorization”: f”Bearer {API_KEY}”,
“Content-Type”: “application/json”,
}

BASE_URL = “https://api.printify.com/v1”

# Blueprint IDs — variants fetched dynamically from catalog

# Provider 29 = Monster Digital (works for T-shirt + Hoodie)

# Provider 99 = Printify Choice (auto-selects best provider)

PRODUCTS = [
{“name”: “T-Shirt”,       “blueprint_id”: 6,   “print_provider_id”: 29,  “print_area”: “front”, “price”: 29900},
{“name”: “Hoodie”,        “blueprint_id”: 77,  “print_provider_id”: 29,  “print_area”: “front”, “price”: 49900},
{“name”: “Snapback Cap”,  “blueprint_id”: 75,  “print_provider_id”: 99,  “print_area”: “front”, “price”: 27900},
{“name”: “Water Bottle”,  “blueprint_id”: 384, “print_provider_id”: 99,  “print_area”: “front”, “price”: 32900},
]

def fetch_variants(blueprint_id, print_provider_id):
“”“Fetch available providers if default fails, then get variants.”””
# First try the specified provider
url = f”{BASE_URL}/catalog/blueprints/{blueprint_id}/print_providers/{print_provider_id}/variants.json”
response = requests.get(url, headers=HEADERS)

```
if response.status_code == 404:
    print(f"⚠️  Provider {print_provider_id} ikke tilgjengelig for blueprint {blueprint_id}, prøver andre...")
    # Get available providers for this blueprint
    providers_url = f"{BASE_URL}/catalog/blueprints/{blueprint_id}/print_providers.json"
    pr = requests.get(providers_url, headers=HEADERS)
    if pr.status_code == 200:
        providers = pr.json()
        if providers:
            alt_id = providers[0]["id"]
            print(f"✅ Bruker provider {alt_id}: {providers[0].get('title','')}")
            url = f"{BASE_URL}/catalog/blueprints/{blueprint_id}/print_providers/{alt_id}/variants.json"
            response = requests.get(url, headers=HEADERS)
            if response.status_code == 200:
                # Store the working provider ID back
                return response.json().get("variants", [])[:6], alt_id
    return [], print_provider_id

if response.status_code != 200:
    print(f"⚠️  Feil ved henting av varianter: {response.text}")
    return [], print_provider_id

return response.json().get("variants", [])[:6], print_provider_id
```

def generate_seo(design_name, product_type):
print(f”🤖 Genererer SEO for: {design_name} – {product_type}”)
prompt = f””“You are an expert Shopify/Etsy SEO copywriter for FIFA World Cup 2026 merchandise.
Design name: “{design_name}”
Product type: “{product_type}”
Respond ONLY with valid JSON, no markdown:
{{
“title”: “SEO title max 70 chars, include country name, World Cup 2026, product type”,
“description”: “3-4 sentences. Mention country, FIFA World Cup 2026, gift idea, quality.”,
“tags”: [“10”, “relevant”, “seo”, “tags”, “for”, “shopify”, “and”, “etsy”]
}}”””
try:
response = requests.post(
“https://api.anthropic.com/v1/messages”,
headers={“x-api-key”: ANTHROPIC_API_KEY, “anthropic-version”: “2023-06-01”, “content-type”: “application/json”},
json={“model”: “claude-haiku-4-5-20251001”, “max_tokens”: 500, “messages”: [{“role”: “user”, “content”: prompt}]},
timeout=15,
)
if response.status_code == 200:
text = response.json()[“content”][0][“text”].strip().replace(”`json","").replace("`”,””).strip()
return json.loads(text)
except Exception as e:
print(f”⚠️  Claude API feil: {e}”)
return None

def upload_image(image_path):
path = Path(image_path)
print(f”📤 Laster opp: {path.name}”)
with open(path, “rb”) as f:
encoded = base64.b64encode(f.read()).decode(“utf-8”)
response = requests.post(
f”{BASE_URL}/uploads/images.json”,
headers=HEADERS,
json={“file_name”: path.name, “contents”: encoded},
)
response.raise_for_status()
image_id = response.json()[“id”]
print(f”✅ Bilde lastet opp: {image_id}”)
return image_id

def create_product(design_name, image_id, product_config, variants, actual_provider_id, seo, shop_id):
if seo:
title = seo[“title”]
description = seo[“description”]
tags = seo[“tags”]
else:
title = f”{design_name} – {product_config[‘name’]} – FIFA World Cup 2026”
description = f”Show your support with this FIFA World Cup 2026 {product_config[‘name’]}! Perfect gift for football fans.”
tags = [“World Cup 2026”, “FIFA”, “football”, “soccer”, design_name, product_config[‘name’], “sport”, “gift”]

```
print(f"🛍️  Oppretter: {title[:50]}...")

priced_variants = [{"id": v["id"], "price": product_config["price"]} for v in variants]
placeholders = [{"position": product_config["print_area"], "images": [{"id": image_id, "x": 0.5, "y": 0.5, "scale": 1, "angle": 0}]}]

payload = {
    "title": title,
    "description": description,
    "tags": tags,
    "blueprint_id": product_config["blueprint_id"],
    "print_provider_id": actual_provider_id,
    "variants": priced_variants,
    "print_areas": [{"variant_ids": [v["id"] for v in variants], "placeholders": placeholders}],
}

response = requests.post(f"{BASE_URL}/shops/{shop_id}/products.json", headers=HEADERS, json=payload)
if response.status_code != 200:
    print(f"❌ Feil: {response.text[:200]}")
    return None
product_id = response.json()["id"]
print(f"✅ Produkt opprettet: {product_id}")
return product_id
```

def publish_product(product_id, shop_id):
response = requests.post(
f”{BASE_URL}/shops/{shop_id}/products/{product_id}/publish.json”,
headers=HEADERS,
json={“title”: True, “description”: True, “images”: True, “variants”: True, “tags”: True},
)
if response.status_code == 200:
print(f”✅ Publisert!”)
else:
print(f”❌ Publisering feilet: {response.text[:200]}”)

def main():
designs_dir = Path(“designs/new”)
design_files = list(designs_dir.glob(”*.png”)) + list(designs_dir.glob(”*.jpg”)) + list(designs_dir.glob(”*.jpeg”))

```
if not design_files:
    print("Ingen nye designfiler funnet.")
    return

# Pre-fetch variants
print("🔍 Henter variant ID-er fra Printify...")
for product in PRODUCTS:
    variants, actual_provider = fetch_variants(product["blueprint_id"], product["print_provider_id"])
    product["variants"] = variants
    product["actual_provider"] = actual_provider
    if variants:
        print(f"✅ {product['name']}: {len(variants)} varianter (provider {actual_provider})")
    else:
        print(f"❌ {product['name']}: ingen varianter funnet — hoppes over")

for design_file in design_files:
    print(f"\n{'='*50}")
    print(f"🎨 {design_file.name}")
    design_name = design_file.stem.replace("-"," ").replace("_"," ").title()

    for shop in SHOP_IDS:
        shop_id = shop["id"]
        print(f"\n📦 {shop['name']}")

        image_id = upload_image(design_file)
        if not image_id:
            continue

        for product in PRODUCTS:
            if not product.get("variants"):
                continue
            seo = generate_seo(design_name, product["name"])
            product_id = create_product(design_name, image_id, product, product["variants"], product["actual_provider"], seo, shop_id)
            if product_id:
                publish_product(product_id, shop_id)

print(f"\n🎉 Ferdig!")
```

if **name** == “**main**”:
main()
