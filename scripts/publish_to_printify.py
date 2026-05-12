import os
import json
import requests
from pathlib import Path
import base64

API_KEY = os.environ["PRINTIFY_API_KEY"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]

SHOP_IDS = [
    {"id": "27515383", "name": "Shopify (wcmerch.shop)"},
    {"id": "27515021", "name": "Etsy (World Cup Merch)"},
]

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}

BASE_URL = "https://api.printify.com/v1"

# Blueprint + provider combos — variants fetched dynamically
PRODUCTS = [
    {"name": "T-Shirt",   "blueprint_id": 6,  "print_provider_id": 29, "print_area": "front", "price": 29900},
    {"name": "Mug",       "blueprint_id": 35, "print_provider_id": 29, "print_area": "front", "price": 24900},
    {"name": "Hoodie",    "blueprint_id": 77, "print_provider_id": 29, "print_area": "front", "price": 49900},
    {"name": "Tote Bag",  "blueprint_id": 51, "print_provider_id": 29, "print_area": "front", "price": 19900},
]


def fetch_variants(blueprint_id, print_provider_id):
    """Fetch real variant IDs from Printify catalog."""
    url = f"{BASE_URL}/catalog/blueprints/{blueprint_id}/print_providers/{print_provider_id}/variants.json"
    response = requests.get(url, headers=HEADERS)
    if response.status_code != 200:
        print(f"⚠️  Kunne ikke hente varianter for blueprint {blueprint_id}: {response.text}")
        return []
    data = response.json()
    variants = data.get("variants", [])
    # Pick max 6 variants (e.g. sizes S-2XL or colors) and set price
    selected = variants[:6]
    return [{"id": v["id"], "price": None} for v in selected]


def generate_seo(design_name, product_type):
    print(f"🤖 Genererer SEO for: {design_name} – {product_type}")
    prompt = f"""You are an expert Shopify/Etsy SEO copywriter for FIFA World Cup 2026 merchandise.
Design name: "{design_name}"
Product type: "{product_type}"
Generate SEO-optimized content. Respond ONLY with valid JSON, no markdown:
{{
  "title": "SEO product title (max 70 chars, include country, World Cup 2026, product type)",
  "description": "3-4 sentence product description. Mention the country, FIFA World Cup 2026, great gift idea, and product quality.",
  "tags": ["array", "of", "10", "relevant", "tags"]
}}"""
    response = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={"x-api-key": ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"},
        json={"model": "claude-haiku-4-5-20251001", "max_tokens": 500, "messages": [{"role": "user", "content": prompt}]},
    )
    if response.status_code != 200:
        print(f"⚠️  Claude API feil, bruker standard tekst.")
        return None
    text = response.json()["content"][0]["text"].strip().replace("```json","").replace("```","").strip()
    try:
        return json.loads(text)
    except:
        return None


def upload_image(image_path):
    path = Path(image_path)
    print(f"📤 Laster opp bilde: {path.name}")
    with open(path, "rb") as f:
        image_data = f.read()
    encoded = base64.b64encode(image_data).decode("utf-8")
    response = requests.post(
        f"{BASE_URL}/uploads/images.json",
        headers=HEADERS,
        json={"file_name": path.name, "contents": encoded},
    )
    response.raise_for_status()
    image_id = response.json()["id"]
    print(f"✅ Bilde lastet opp: {image_id}")
    return image_id


def create_product(design_name, image_id, product_config, variants, seo, shop_id):
    if seo:
        title = seo["title"]
        description = seo["description"]
        tags = seo["tags"]
    else:
        title = f"{design_name} – {product_config['name']} – World Cup 2026"
        description = f"Official FIFA World Cup 2026 {product_config['name']} – {design_name}. Perfect gift for football fans!"
        tags = ["World Cup 2026", "FIFA", "football", design_name, product_config['name']]

    print(f"🛍️  Oppretter: {title} i shop {shop_id}")

    # Set price on variants
    priced_variants = [{"id": v["id"], "price": product_config["price"]} for v in variants]

    placeholders = [{"position": product_config["print_area"], "images": [{"id": image_id, "x": 0.5, "y": 0.5, "scale": 1, "angle": 0}]}]

    payload = {
        "title": title,
        "description": description,
        "tags": tags,
        "blueprint_id": product_config["blueprint_id"],
        "print_provider_id": product_config["print_provider_id"],
        "variants": priced_variants,
        "print_areas": [{"variant_ids": [v["id"] for v in variants], "placeholders": placeholders}],
    }

    response = requests.post(f"{BASE_URL}/shops/{shop_id}/products.json", headers=HEADERS, json=payload)
    if response.status_code != 200:
        print(f"❌ Feil: {response.text}")
        return None
    product_id = response.json()["id"]
    print(f"✅ Produkt opprettet: {product_id}")
    return product_id


def publish_product(product_id, shop_id):
    response = requests.post(
        f"{BASE_URL}/shops/{shop_id}/products/{product_id}/publish.json",
        headers=HEADERS,
        json={"title": True, "description": True, "images": True, "variants": True, "tags": True},
    )
    if response.status_code == 200:
        print(f"✅ Publisert!")
    else:
        print(f"❌ Publisering feilet: {response.text}")


def main():
    designs_dir = Path("designs/new")
    design_files = (
        list(designs_dir.glob("*.png")) +
        list(designs_dir.glob("*.jpg")) +
        list(designs_dir.glob("*.jpeg"))
    )

    if not design_files:
        print("Ingen nye designfiler funnet.")
        return

    # Pre-fetch variants for all product types
    print("🔍 Henter variant ID-er fra Printify...")
    for product in PRODUCTS:
        variants = fetch_variants(product["blueprint_id"], product["print_provider_id"])
        if not variants:
            print(f"❌ Ingen varianter funnet for {product['name']} – hopper over")
        else:
            print(f"✅ {product['name']}: {len(variants)} varianter hentet")
        product["variants"] = variants

    for design_file in design_files:
        print(f"\n{'='*50}")
        print(f"🎨 Behandler design: {design_file.name}")
        design_name = design_file.stem.replace("-"," ").replace("_"," ").title()

        for shop in SHOP_IDS:
            shop_id = shop["id"]
            print(f"\n📦 Butikk: {shop['name']}")

            image_id = upload_image(design_file)
            if not image_id:
                continue

            for product in PRODUCTS:
                if not product.get("variants"):
                    continue
                seo = generate_seo(design_name, product["name"])
                product_id = create_product(design_name, image_id, product, product["variants"], seo, shop_id)
                if product_id:
                    publish_product(product_id, shop_id)

    print(f"\n🎉 Ferdig!")


if __name__ == "__main__":
    main()
