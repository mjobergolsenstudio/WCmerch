import os
import json
import requests
from pathlib import Path
from PIL import Image
import io
import base64

API_KEY = os.environ["PRINTIFY_API_KEY"]
SHOP_ID = os.environ["PRINTIFY_SHOP_ID"]

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}

BASE_URL = "https://api.printify.com/v1"

# Product blueprints + print providers (Printify catalog IDs)
# Using Monster Digital as provider (id: 29) - ships to Norway
PRODUCTS = [
    {
        "name": "T-skjorte",
        "blueprint_id": 6,       # Unisex Softstyle T-Shirt (Gildan 64000)
        "print_provider_id": 29, # Monster Digital
        "variants": [
            {"id": 17887, "price": 29900},  # S White
            {"id": 17888, "price": 29900},  # M White
            {"id": 17889, "price": 29900},  # L White
            {"id": 17890, "price": 29900},  # XL White
        ],
        "print_area": "front",
    },
    {
        "name": "Krus",
        "blueprint_id": 35,      # White Mug 11oz
        "print_provider_id": 29,
        "variants": [
            {"id": 1320, "price": 24900},
        ],
        "print_area": "front",
    },
    {
        "name": "Hoodie",
        "blueprint_id": 77,      # Unisex Heavy Blend Hoodie (Gildan 18500)
        "print_provider_id": 29,
        "variants": [
            {"id": 34492, "price": 49900},  # S Black
            {"id": 34493, "price": 49900},  # M Black
            {"id": 34494, "price": 49900},  # L Black
            {"id": 34495, "price": 49900},  # XL Black
        ],
        "print_area": "front",
    },
    {
        "name": "Tote bag",
        "blueprint_id": 51,      # Heavy Tote
        "print_provider_id": 29,
        "variants": [
            {"id": 1370, "price": 19900},
        ],
        "print_area": "front",
    },
]


def svg_to_png(svg_path):
    """Convert SVG to PNG using cairosvg if available, else skip."""
    try:
        import cairosvg
        png_data = cairosvg.svg2png(url=str(svg_path), output_width=4000, output_height=4000)
        return png_data
    except ImportError:
        print(f"⚠️  cairosvg ikke installert – hopper over SVG: {svg_path}")
        return None


def upload_image(image_path):
    """Upload image to Printify and return image ID."""
    path = Path(image_path)
    print(f"📤 Laster opp bilde: {path.name}")

    if path.suffix.lower() == ".svg":
        image_data = svg_to_png(path)
        if not image_data:
            return None
        filename = path.stem + ".png"
        mime_type = "image/png"
    else:
        with open(path, "rb") as f:
            image_data = f.read()
        filename = path.name
        mime_type = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"

    encoded = base64.b64encode(image_data).decode("utf-8")

    response = requests.post(
        f"{BASE_URL}/uploads/images.json",
        headers=HEADERS,
        json={
            "file_name": filename,
            "contents": encoded,
        },
    )
    response.raise_for_status()
    image_id = response.json()["id"]
    print(f"✅ Bilde lastet opp: {image_id}")
    return image_id


def create_product(design_name, image_id, product_config):
    """Create a product in Printify."""
    name = f"{design_name} – {product_config['name']}"
    print(f"🛍️  Oppretter produkt: {name}")

    placeholders = [
        {
            "position": product_config["print_area"],
            "images": [
                {
                    "id": image_id,
                    "x": 0.5,
                    "y": 0.5,
                    "scale": 1,
                    "angle": 0,
                }
            ],
        }
    ]

    payload = {
        "title": name,
        "description": f"Eksklusivt VM 2026-design – {product_config['name']}",
        "blueprint_id": product_config["blueprint_id"],
        "print_provider_id": product_config["print_provider_id"],
        "variants": product_config["variants"],
        "print_areas": [
            {
                "variant_ids": [v["id"] for v in product_config["variants"]],
                "placeholders": placeholders,
            }
        ],
    }

    response = requests.post(
        f"{BASE_URL}/shops/{SHOP_ID}/products.json",
        headers=HEADERS,
        json=payload,
    )
    if response.status_code != 200:
        print(f"❌ Feil ved oppretting: {response.text}")
        return None

    product_id = response.json()["id"]
    print(f"✅ Produkt opprettet: {product_id}")
    return product_id


def publish_product(product_id, product_name):
    """Publish product to Shopify store."""
    print(f"🚀 Publiserer: {product_name}")
    response = requests.post(
        f"{BASE_URL}/shops/{SHOP_ID}/products/{product_id}/publish.json",
        headers=HEADERS,
        json={
            "title": True,
            "description": True,
            "images": True,
            "variants": True,
            "tags": True,
        },
    )
    if response.status_code == 200:
        print(f"✅ Publisert!")
    else:
        print(f"❌ Publisering feilet: {response.text}")


def main():
    designs_dir = Path("designs/new")
    design_files = list(designs_dir.glob("*.png")) + \
                   list(designs_dir.glob("*.jpg")) + \
                   list(designs_dir.glob("*.jpeg")) + \
                   list(designs_dir.glob("*.svg"))

    if not design_files:
        print("Ingen nye designfiler funnet.")
        return

    for design_file in design_files:
        print(f"\n{'='*50}")
        print(f"🎨 Behandler design: {design_file.name}")
        design_name = design_file.stem.replace("-", " ").replace("_", " ").title()

        image_id = upload_image(design_file)
        if not image_id:
            continue

        for product_config in PRODUCTS:
            product_id = create_product(design_name, image_id, product_config)
            if product_id:
                publish_product(product_id, f"{design_name} – {product_config['name']}")

    print(f"\n🎉 Ferdig! Alle produkter er publisert til Shopify.")


if __name__ == "__main__":
    main()
