import os
import re
import json
import time
import shutil
import requests
import subprocess
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import anthropic

load_dotenv()

SERPAPI_KEY = os.getenv("SERPAPI_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
claude = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
DEMOS_DIR = "demos"
TEMPLATES_DIR = "templates"

# Map business types to templates and accent colors
TEMPLATE_MAP = {
    "handyman":            ("trades",      "#E07B39", "#FEF0E7"),
    "contractor":          ("trades",      "#1D4ED8", "#EFF6FF"),
    "plumber":             ("trades",      "#0369A1", "#E0F2FE"),
    "electrician":         ("trades",      "#D97706", "#FFFBEB"),
    "hvac":                ("trades",      "#0F766E", "#F0FDFA"),
    "fence installer":     ("trades",      "#4D7C0F", "#F7FEE7"),
    "flooring installer":  ("trades",      "#7C3AED", "#F5F3FF"),
    "tile installer":      ("trades",      "#B45309", "#FFFBEB"),
    "painting contractor": ("trades",      "#DC2626", "#FEF2F2"),
    "landscaping":         ("landscaping", "#16A34A", "#F0FDF4"),
    "snow removal":        ("landscaping", "#0284C7", "#E0F2FE"),
    "cleaning service":    ("trades",      "#0891B2", "#ECFEFF"),
    "junk removal":        ("trades",      "#4B5563", "#F9FAFB"),
    "moving company":      ("trades",      "#7C3AED", "#F5F3FF"),
    "gym":                 ("fitness",     "#DC2626", "#FEF2F2"),
    "personal trainer":    ("fitness",     "#EA580C", "#FFF7ED"),
    "restaurant":          ("restaurant",  "#92400E", "#FEF3C7"),
    "cafe":                ("restaurant",  "#78350F", "#FEF3C7"),
}

def get_template_and_colors(biz_type):
    key = biz_type.lower().strip()
    if key in TEMPLATE_MAP:
        template, accent, light = TEMPLATE_MAP[key]
    else:
        template, accent, light = "trades", "#1D4ED8", "#EFF6FF"
    return template, accent, light

def load_template(template_name):
    path = os.path.join(TEMPLATES_DIR, f"{template_name}.html")
    if not os.path.exists(path):
        # Fall back to trades template
        path = os.path.join(TEMPLATES_DIR, "trades.html")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def search_business_info(business_name, city):
    print(f"   🔍 Researching {business_name}...")
    info = {"name": business_name, "city": city, "phone": "", "description": ""}
    try:
        query = f'"{business_name}" {city}'
        url = f"https://www.google.com/search?q={requests.utils.quote(query)}&num=5"
        resp = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")
        text = soup.get_text()
        phones = re.findall(r'[\+\(]?[1-9][0-9 .\-\(\)]{8,}[0-9]', text)
        if phones:
            info["phone"] = phones[0].strip()
        snippets = []
        for div in soup.find_all("div"):
            t = div.get_text().strip()
            if 40 < len(t) < 300 and business_name.lower()[:4] in t.lower():
                snippets.append(t)
        info["description"] = " ".join(snippets[:2])
    except Exception as e:
        print(f"   ⚠️  Research error: {e}")
    return info

def generate_content(info, biz_type, accent_color):
    """Ask Claude to generate ONLY the content variables — not the HTML."""
    print(f"   🤖 Generating content with Claude...")

    # Smart image seeds per business type
    image_seeds = {
        "handyman": ("handyman-tools", "home-repair"),
        "landscaping": ("garden-lawn", "landscape-outdoor"),
        "snow removal": ("snow-winter", "driveway-clearing"),
        "cleaning service": ("cleaning-home", "spotless-house"),
        "painting contractor": ("painting-wall", "paint-brush"),
        "fence installer": ("wood-fence", "backyard-gate"),
        "flooring installer": ("hardwood-floor", "tile-interior"),
        "tile installer": ("bathroom-tile", "kitchen-ceramic"),
        "junk removal": ("truck-hauling", "cleanup-removal"),
        "moving company": ("moving-boxes", "relocation-truck"),
        "plumber": ("plumbing-pipes", "bathroom-repair"),
        "electrician": ("electrical-wiring", "power-tools"),
        "hvac": ("hvac-heating", "airconditioning-vent"),
        "contractor": ("construction-tools", "renovation-building"),
        "gym": ("gym-workout", "fitness-training"),
        "restaurant": ("restaurant-food", "italian-dining"),
    }
    seeds = image_seeds.get(biz_type.lower(), ("professional-work", "business-service"))

    prompt = f"""You are a professional copywriter for a web design agency. Fill in the content variables for a {biz_type} business website.

Business: {info['name']}
City: {info['city']}
Phone: {info.get('phone', 'Call for a quote')}
Info found: {info.get('description', '')}

Return ONLY a valid JSON object with these exact keys. No explanation, no markdown, just JSON:

{{
  "BUSINESS_NAME": "{info['name']}",
  "TAGLINE": "[short catchy tagline for {biz_type} in {info['city']}]",
  "ACCENT_COLOR": "{accent_color}",
  "ACCENT_LIGHT": "[very light version of accent for backgrounds, e.g. #EFF6FF]",
  "HERO_IMAGE": "https://picsum.photos/seed/{seeds[0]}/1400/700",
  "ABOUT_IMAGE": "https://picsum.photos/seed/{seeds[1]}/800/600",
  "LOGO_FIRST": "[first word or initials of business name]",
  "LOGO_SECOND": "[rest of business name]",
  "PHONE": "{info.get('phone', 'Call for a quote')}",
  "PHONE_RAW": "[phone digits only, no formatting]",
  "CITY": "{info['city']}",
  "BUSINESS_TYPE": "[professional title for {biz_type}]",
  "HOURS": "Mon-Fri 7am-6pm · Sat 8am-2pm",
  "HERO_LINE_1": "[powerful 2-3 word headline part 1]",
  "HERO_LINE_2": "[powerful 2-3 word headline part 2 - gets accent color]",
  "HERO_LINE_3": "[powerful 2-3 word headline part 3]",
  "HERO_SUB": "[1-2 sentence description of what they do and where]",
  "TRUST_1": "Licensed & Insured",
  "TRUST_2": "Serving {info['city']} & GTA",
  "TRUST_3": "Free Estimates",
  "TRUST_4": "No Hidden Fees",
  "STAT_1_N": "[realistic number like 200+]",
  "STAT_1_L": "Jobs Completed",
  "STAT_2_N": "4.9",
  "STAT_2_L": "Google Rating",
  "STAT_3_N": "[realistic number]",
  "STAT_3_L": "[relevant stat label]",
  "STAT_4_N": "100%",
  "STAT_4_L": "Satisfaction",
  "SERVICES_TITLE": "[title for services section]",
  "SERVICES_SUB": "[1 sentence describing service range]",
  "S1_TITLE": "[service 1 name for {biz_type}]",
  "S1_DESC": "[2 sentence description]",
  "S2_TITLE": "[service 2]",
  "S2_DESC": "[2 sentence description]",
  "S3_TITLE": "[service 3]",
  "S3_DESC": "[2 sentence description]",
  "S4_TITLE": "[service 4]",
  "S4_DESC": "[2 sentence description]",
  "S5_TITLE": "[service 5]",
  "S5_DESC": "[2 sentence description]",
  "S6_TITLE": "[service 6]",
  "S6_DESC": "[2 sentence description]",
  "ABOUT_TITLE": "[about section headline]",
  "ABOUT_P1": "[paragraph 1 about the business - specific to {biz_type}]",
  "ABOUT_P2": "[paragraph 2 about their approach/values]",
  "CRED_1": "Licensed & Fully Insured",
  "CRED_2": "WSIB Registered",
  "CRED_3": "$2M Liability Coverage",
  "CRED_4": "Serving GTA Since [year]",
  "WHY_TITLE": "[why choose us headline]",
  "W1_TITLE": "Licensed & Insured",
  "W1_DESC": "[2 sentence description]",
  "W2_TITLE": "Experienced Team",
  "W2_DESC": "[2 sentence description]",
  "W3_TITLE": "Transparent Pricing",
  "W3_DESC": "[2 sentence description]",
  "W4_TITLE": "Fast Response",
  "W4_DESC": "[2 sentence description]",
  "REVIEWS_TITLE": "[reviews section headline]",
  "R1_TEXT": "[realistic 5-star review from GTA homeowner about {biz_type} service]",
  "R1_NAME": "[first name + last initial]",
  "R1_LOCATION": "[GTA city]",
  "R2_TEXT": "[realistic 5-star review]",
  "R2_NAME": "[first name + last initial]",
  "R2_LOCATION": "[GTA city]",
  "R3_TEXT": "[realistic 5-star review]",
  "R3_NAME": "[first name + last initial]",
  "R3_LOCATION": "[GTA city]",
  "CONTACT_TITLE": "[contact section headline]",
  "FOOTER_DESC": "[1-2 sentence footer description of business]"
}}"""

    message = claude.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=3000,
        messages=[{"role": "user", "content": prompt}]
    )

    raw = message.content[0].text.strip()
    # Clean markdown if present
    raw = re.sub(r'^```[a-z]*\n?', '', raw)
    raw = re.sub(r'\n?```$', '', raw)

    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"   ❌ JSON parse error: {e}")
        print(f"   Raw: {raw[:200]}")
        return None

def fill_template(template_html, variables):
    """Replace all {{VARIABLE}} placeholders in the template."""
    result = template_html
    for key, value in variables.items():
        result = result.replace(f"{{{{{key}}}}}", str(value) if value else "")
    return result

def save_and_deploy(business_name, html):
    if not html:
        print("   ❌ No HTML to save.")
        return None, None

    slug = re.sub(r'[^a-z0-9]+', '-', business_name.lower()).strip('-')
    folder = os.path.join(DEMOS_DIR, slug)
    os.makedirs(folder, exist_ok=True)

    filepath = os.path.join(folder, "index.html")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"   💾 Saved to {filepath}")

    print(f"   🚀 Deploying to Vercel...")
    try:
        subprocess.run(["git", "add", "."], check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", f"Add demo: {business_name}"], check=True, capture_output=True)
        subprocess.run(["git", "push", "origin", "main"], check=True, capture_output=True)
        print(f"   ✅ Deployed!")
    except subprocess.CalledProcessError as e:
        print(f"   ⚠️  Git push failed: {e}")

    url = f"https://demos.wrenchdigital.ca/{slug}"
    return url, slug

def build_demo(business_name, city, biz_type):
    print(f"\n🏗️  Building demo for {business_name}...")

    # Get template and colors
    template_name, accent_color, accent_light = get_template_and_colors(biz_type)
    print(f"   📐 Using template: {template_name} | Accent: {accent_color}")

    # Load template
    template_html = load_template(template_name)

    # Research business
    info = search_business_info(business_name, city)

    # Generate content variables
    variables = generate_content(info, biz_type, accent_color)
    if not variables:
        print("   ❌ Failed to generate content.")
        return None

    # Make sure accent light is set
    if "ACCENT_LIGHT" not in variables or not variables["ACCENT_LIGHT"]:
        variables["ACCENT_LIGHT"] = accent_light

    # Fill template
    html = fill_template(template_html, variables)

    # Deploy
    url, slug = save_and_deploy(business_name, html)
    return url

def main():
    print("\n🏗️  Wrench Digital — Demo Builder\n")
    print("Templates available: trades, landscaping (more coming soon)\n")

    mode = input("Build demo for (1) specific business or (2) all leads from CSV? [1/2]: ").strip()

    if mode == "1":
        business_name = input("Business name: ").strip()
        city = input("City (e.g. Mississauga, ON): ").strip()
        biz_type = input("Business type (e.g. handyman, plumber, landscaping): ").strip()

        url = build_demo(business_name, city, biz_type)
        if url:
            print(f"\n🎉 Demo ready!")
            print(f"   URL: {url}")
            first_name = business_name.split()[0]
            print(f"\n📱 Text to send:")
            print(f'   "Hey {first_name}! I noticed you don\'t have a website — I built you a free demo to show you what it could look like. Check it out: {url} — Shaan | Wrench Digital"')

    elif mode == "2":
        import csv, glob
        csvs = glob.glob("../cold-emailer/leads_*.csv") or glob.glob("leads_*.csv")
        if not csvs:
            print("No CSV found. Run cold-emailer first.")
            return

        latest = max(csvs)
        print(f"\n📄 Using: {latest}\n")

        with open(latest, encoding="utf-8") as f:
            leads = list(csv.DictReader(f))

        print(f"Found {len(leads)} leads. Building demos...\n")
        results = []

        for lead in leads:
            name = lead.get("name", "")
            city = lead.get("city", "")
            biz_type = lead.get("type", "")
            phone = lead.get("phone", "")

            url = build_demo(name, city, biz_type)
            if url:
                results.append({"name": name, "phone": phone, "url": url})
                print(f"   ✅ {url}")
            time.sleep(2)

        print(f"\n\n🎉 Done! {len(results)} demos built.\n")
        for r in results:
            print(f"{r['name']:<35} {r['phone']:<20} {r['url']}")

if __name__ == "__main__":
    main()