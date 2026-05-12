import os
import json
import requests
from pathlib import Path
import base64

API_KEY = os.environ["PRINTIFY_API_KEY"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]

# Publiserer til både Shopify og Etsy
SHOP_IDS = [
    {"id": "27515383", "name": "Shopify (wcmerch.shop)"},
    {"id": "27515021", "name": "Etsy (World Cup Merch)"},
]

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}

BASE_URL = "https://api.printify.com/v1"

PRODUCTS = [
    {
        "name": "T-Shirt",
        "blueprint_id": 6,
        "print_provider_id": 29,
        "variants": [
            {"id": 17887, "price": 29900},
            {"id": 17888, "price": 29900},
            {"id": 17889, "price": 29900},
            {"id": 17890, "price": 29900},
        ],
        "print_area": "front",
    },
    {
        "name": "Mug",
        "blueprint_id": 35,
        "print_provider_id": 29,
        "variants": [
            {"id": 1320, "price": 24900},
        ],
        "print_area": "front",
    },
    {
        "name": "Hoodie",
        "blueprint_id": 77,
        "print_provider_id": 29,
        "variants": [
            {"id": 34492, "price": 49900},
            {"id": 34493, "price": 49900},
            {"id": 34494, "price": 49900},
            {"id": 34495, "price": 49900},
        ],
        "print_area": "front",
    },
    {
        "name": "Tote Bag",
        "blueprint_id": 51,
        "print_provider_id": 29,
        "variants": [
            {"id": 1370, "price": 19900},
        ],
        "print_area": "front",
    },
]


def generate_seo(design_name, product_type):
    print(f"🤖 Genererer SEO for: {design_name} – {product_type}")

    prompt = f"""You are an expert Shopify/Etsy SEO copywriter for FIFA World Cup 2026 merchandise.

Design name: "{design_name}"
Product type: "{product_type}"

Generate SEO-optimized content for this product. Respond ONLY with valid JSON, no markdown, no explanation:
{{
  "title": "SEO product title (max 70 chars, include country, World Cup 2026, product type)",
  "description": "3-4 sentence product description. Mention the country, FIFA World Cup 2026, great gift idea, and product quality. Enthusiastic tone.",
  "tags": ["array", "of", "10", "relevant", "tags", "for", "shopify", "and", "etsy"]
}}"""

    response = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": "claude-haiku-4-5-20251001",
            "max_tokens": 500,
            "messages": [{"role": "user", "content": prompt}],
        },
    )

    if response.status_code != 200:
        print(f"⚠️  Claude API feil, bruker standard tekst.")
        return None

    text = response.json()["content"][0]["text"].strip()
    text = text.replace("```json", "").replace("```", "").strip()
    return json.loads(text)


def upload_image(image_path, shop_id):
    path = Path(image_path)
    print(f"📤 Laster opp bilde til shop {shop_id}: {path.name}")

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


def create_product(design_name, image_id, product_config, seo, shop_id):
    product_type = product_config["name"]

    if seo:
        title = seo["title"]
        description = seo["description"]
        tags = seo["tags"]
    else:
        title = f"{design_name} – {product_type} – World Cup 2026"
        description = f"Official FIFA World Cup 2026 {product_type} – {design_name}. Perfect gift for football fans!"
        tags = ["World Cup 2026", "FIFA", "football", design_name, product_type]

    print(f"🛍️  Oppretter produkt i shop {shop_id}: {title}")

    placeholders = [{
        "position": product_config["print_area"],
        "images": [{
            "id": image_id,
            "x": 0.5, "y": 0.5,
            "scale": 1, "angle": 0,
        }],
    }]

    payload = {
        "title": title,
        "description": description,
        "tags": tags,
        "blueprint_id": product_config["blueprint_id"],
        "print_provider_id": product_config["print_provider_id"],
        "variants": product_config["variants"],
        "print_areas": [{
            "variant_ids": [v["id"] for v in product_config["variants"]],
            "placeholders": placeholders,
        }],
    }

    response = requests.post(
        f"{BASE_URL}/shops/{shop_id}/products.json",
        headers=HEADERS,
        json=payload,
    )
    if response.status_code != 200:
        print(f"❌ Feil ved oppretting: {response.text}")
        return None

    product_id = response.json()["id"]
    print(f"✅ Produkt opprettet: {product_id}")
    return product_id


def publish_product(product_id, title, shop_id):
    print(f"🚀 Publiserer til shop {shop_id}: {title}")
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

    for design_file in design_files:
        print(f"\n{'='*50}")
        print(f"🎨 Behandler design: {design_file.name}")
        design_name = design_file.stem.replace("-", " ").replace("_", " ").title()

        for shop in SHOP_IDS:
            print(f"\n📦 Butikk: {shop['name']}")
            shop_id = shop["id"]

            image_id = upload_image(design_file, shop_id)
            if not image_id:
                continue

            for product_config in PRODUCTS:
                seo = generate_seo(design_name, product_config["name"])
                product_id = create_product(design_name, image_id, product_config, seo, shop_id)
                if product_id:
                    title = seo["title"] if seo else f"{design_name} – {product_config['name']}"
                    publish_product(product_id, title, shop_id)

    print(f"\n🎉 Ferdig! Alle produkter publisert til Shopify og Etsy.")


if __name__ == "__main__":
    main()
