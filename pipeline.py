import os
import re
import json
import time
import csv
import requests
import subprocess
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from groq import Groq
import anthropic
from datetime import datetime

load_dotenv()

SERPAPI_KEY = os.getenv("SERPAPI_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
RESEND_API_KEY = os.getenv("RESEND_API_KEY")
FROM_EMAIL = os.getenv("FROM_EMAIL")

claude = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
groq_client = Groq(api_key=GROQ_API_KEY)

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
DEMOS_DIR = "demos"
TEMPLATES_DIR = "templates"
SENT_FILE = "sent_leads.json"

GTA_CITIES = [
    "Mississauga ON", "Brampton ON", "Etobicoke ON", "Scarborough ON",
    "North York ON", "Oakville ON", "Milton ON", "Burlington ON",
    "Vaughan ON", "Markham ON", "Richmond Hill ON", "Pickering ON",
    "Ajax ON", "Whitby ON", "Oshawa ON", "Newmarket ON",
    "Aurora ON", "Caledon ON", "Georgetown ON", "Stouffville ON"
]

BUSINESS_TYPES = [
    "nail salon", "barber", "hair salon",
    "restaurant", "auto repair",
    "landscaping", "cleaning service",
    "plumber", "electrician", "hvac",
]

TEMPLATE_MAP = {
    "handyman":            ("trades",           "#E07B39", "#FEF0E7"),
    "contractor":          ("trades",           "#1D4ED8", "#EFF6FF"),
    "plumber":             ("plumber",          "#0369A1", "#E0F2FE"),
    "electrician":         ("electrician",      "#D97706", "#FFFBEB"),
    "hvac":                ("hvac",             "#0F766E", "#F0FDFA"),
    "fence installer":     ("trades",           "#4D7C0F", "#F7FEE7"),
    "flooring installer":  ("trades",           "#7C3AED", "#F5F3FF"),
    "tile installer":      ("trades",           "#B45309", "#FFFBEB"),
    "painting contractor": ("trades",           "#DC2626", "#FEF2F2"),
    "landscaping":         ("landscaping",      "#16A34A", "#F0FDF4"),
    "snow removal":        ("trades",           "#0284C7", "#E0F2FE"),
    "cleaning service":    ("cleaning_service", "#0891B2", "#ECFEFF"),
    "junk removal":        ("trades",           "#4B5563", "#F9FAFB"),
    "moving company":      ("trades",           "#7C3AED", "#F5F3FF"),
    "nail salon":          ("nail_salon", "#EC4899", "#FDF2F8"),
    "barber":              ("barber",           "#1E293B", "#F8FAFC"),
    "hair salon":          ("hair_salon", "#7C3AED", "#F5F3FF"),
    "restaurant":          ("trades",           "#B45309", "#FFFBEB"),
    "auto repair":         ("trades",           "#DC2626", "#FEF2F2"),
}

IMAGE_URLS = {
    "nail salon": (
        "https://images.unsplash.com/photo-1604654894610-df63bc536371?w=1400&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1604654894610-df63bc536371?w=800&auto=format&fit=crop&q=80"
    ),
    "barber": (
        "https://images.unsplash.com/photo-1503951914875-452162b0f3f1?w=1400&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1622286342621-4bd786c2447c?w=800&auto=format&fit=crop&q=80"
    ),
    "hair salon": (
        "https://images.unsplash.com/photo-1560066984-138daaa4e4e1?w=1400&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1522337360788-8b13dee7a37e?w=800&auto=format&fit=crop&q=80"
    ),
    "restaurant": (
        "https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?w=1400&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1414235077428-338989a2e8c0?w=800&auto=format&fit=crop&q=80"
    ),
    "auto repair": (
        "https://images.unsplash.com/photo-1530046339160-ce3e530c7d2f?w=1400&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1486262715619-67b85e0b08d3?w=800&auto=format&fit=crop&q=80"
    ),
    "handyman": (
        "https://images.unsplash.com/photo-1621905252507-b35492cc74b4?w=1400&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1581244277943-fe4a9c777189?w=800&auto=format&fit=crop&q=80"
    ),
    "landscaping": (
        "https://images.unsplash.com/photo-1416879595882-3373a0480b5b?w=1400&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1558904541-efa843a96f01?w=800&auto=format&fit=crop&q=80"
    ),
    "snow removal": (
        "https://images.unsplash.com/photo-1547754980-3df97fed72a8?w=1400&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1612208695882-02f2322b7fee?w=800&auto=format&fit=crop&q=80"
    ),
    "cleaning service": (
        "https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=1400&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1527515545081-5db817172677?w=800&auto=format&fit=crop&q=80"
    ),
    "painting contractor": (
        "https://images.unsplash.com/photo-1589939705384-5185137a7f0f?w=1400&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1562259949-e8e7689d7828?w=800&auto=format&fit=crop&q=80"
    ),
    "fence installer": (
        "https://images.unsplash.com/photo-1564182842519-8a3b2af3e228?w=1400&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1591955506264-3f5a6834570a?w=800&auto=format&fit=crop&q=80"
    ),
    "flooring installer": (
        "https://images.unsplash.com/photo-1581858726788-75bc0f6a952d?w=1400&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1604709177225-055f99402ea3?w=800&auto=format&fit=crop&q=80"
    ),
    "tile installer": (
        "https://images.unsplash.com/photo-1552321554-5fefe8c9ef14?w=1400&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1584622650111-993a426fbf0a?w=800&auto=format&fit=crop&q=80"
    ),
    "junk removal": (
        "https://images.unsplash.com/photo-1532996122724-e3c354a0b15b?w=1400&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1600880292203-757bb62b4baf?w=800&auto=format&fit=crop&q=80"
    ),
    "moving company": (
        "https://images.unsplash.com/photo-1586528116311-ad8dd3c8310d?w=1400&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1600518464441-9154a4dea21b?w=800&auto=format&fit=crop&q=80"
    ),
    "plumber": (
        "https://images.unsplash.com/photo-1504328345606-18bbc8c9d7d1?w=1400&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1585704032915-c3400ca199e7?w=800&auto=format&fit=crop&q=80"
    ),
    "electrician": (
        "https://images.unsplash.com/photo-1558402529-d2638857f87a?w=1400&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1621905251189-08b45249ff78?w=800&auto=format&fit=crop&q=80"
    ),
    "hvac": (
        "https://images.unsplash.com/photo-1592198084033-aade902d1aae?w=1400&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1581094480099-83d51516b92e?w=800&auto=format&fit=crop&q=80"
    ),
    "contractor": (
        "https://images.unsplash.com/photo-1541888946425-d81bb19240f5?w=1400&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1504307651254-35680f356dfd?w=800&auto=format&fit=crop&q=80"
    ),
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def load_sent():
    if os.path.exists(SENT_FILE):
        with open(SENT_FILE) as f:
            return set(json.load(f))
    return set()

def save_sent(sent):
    with open(SENT_FILE, "w") as f:
        json.dump(list(sent), f)

def check_website(url):
    if not url:
        return "no website"

    # Social media / directory pages are not real websites
    social = ["facebook.com", "instagram.com", "twitter.com",
              "yelp.com", "linkedin.com", "google.com", "maps.google",
              "yellowpages", "homestars", "houzz", "fresha", "booksy"]
    if any(s in url.lower() for s in social):
        return "no website"

    try:
        resp = requests.get(url, timeout=8, headers=HEADERS)
        if resp.status_code != 200:
            return "no website"

        text = resp.text.lower()
        red_flags = [
            len(resp.text) < 2000,
            "coming soon" in text,
            "under construction" in text,
            "parked" in text,
            "domain for sale" in text,
            "buy this domain" in text,
            text.count("<div") < 5,
        ]
        if sum(red_flags) >= 2:
            return "website very poor"
        return "has website"
    except:
        return "no website"


def google_search_has_website(business_name, city):
    clean_city = city.replace(" ON", "").strip()
    query = f'"{business_name}" "{clean_city}"'
    try:
        url = f"https://www.google.com/search?q={requests.utils.quote(query)}&num=5"
        resp = requests.get(url, headers=HEADERS, timeout=10)
        domains = re.findall(r'https?://([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', resp.text)
        blocked = ["google", "facebook", "instagram", "yelp", "youtube",
                   "twitter", "linkedin", "maps", "gstatic", "googleapis",
                   "serpapi", "schema", "w3", "yellowpages", "homestars",
                   "houzz", "fresha", "booksy", "nextdoor", "tripadvisor"]
        real_sites = [d for d in domains if not any(b in d.lower() for b in blocked)]
        return len(real_sites) > 0
    except:
        return False


def find_email(business_name, city):
    for source, domain, path_key in [
        ("HomeStars", "homestars.com", "/companies/"),
        ("Houzz",     "houzz.com",     "/pro/"),
    ]:
        try:
            query = f'site:{domain} "{business_name}" {city.replace(" ON","").strip()}'
            url = f"https://www.google.com/search?q={requests.utils.quote(query)}&num=3"
            resp = requests.get(url, headers=HEADERS, timeout=10)
            soup = BeautifulSoup(resp.text, "html.parser")
            for a in soup.find_all("a", href=True):
                match = re.search(rf'url\?q=(https://{re.escape(domain)}{re.escape(path_key)}[^&]+)', a["href"])
                if match:
                    time.sleep(1)
                    page = requests.get(match.group(1), headers=HEADERS, timeout=10)
                    blocked = ["google","youtube","facebook","twitter","example","sentry","w3",domain]
                    emails = [e for e in re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', page.text)
                              if not any(b in e.lower() for b in blocked)]
                    if emails:
                        return emails[0], source
        except:
            pass
        time.sleep(0.5)
    return None, None

# ── Google Maps Search ────────────────────────────────────────────────────────

def search_maps(biz_type, city):
    params = {
        "engine": "google_maps",
        "q": f"{biz_type} in {city}",
        "api_key": SERPAPI_KEY,
        "num": "20",
    }
    try:
        resp = requests.get("https://serpapi.com/search", params=params, timeout=15)
        return resp.json().get("local_results", [])
    except:
        return []

# ── Demo Builder ──────────────────────────────────────────────────────────────

def load_template(template_name):
    path = os.path.join(TEMPLATES_DIR, f"{template_name}.html")
    if not os.path.exists(path):
        path = os.path.join(TEMPLATES_DIR, "trades.html")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def generate_content(info, biz_type, accent_color):
    imgs = IMAGE_URLS.get(biz_type.lower(), (
        "https://images.unsplash.com/photo-1504307651254-35680f356dfd?w=1400&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1541888946425-d81bb19240f5?w=800&auto=format&fit=crop"
    ))

    prompt = f"""You are a professional copywriter. Fill in content for a {biz_type} business website.

Business: {info['name']}
City: {info['city']}
Phone: {info.get('phone', 'Call for a quote')}
Info: {info.get('description', '')}

Return ONLY valid JSON, no markdown:

{{
  "BUSINESS_NAME": "{info['name']}",
  "TAGLINE": "[catchy tagline specific to {biz_type}]",
  "ACCENT_COLOR": "{accent_color}",
  "ACCENT_LIGHT": "[very light tint of {accent_color}]",
  "HERO_IMAGE": "{imgs[0]}",
  "ABOUT_IMAGE": "{imgs[1]}",
  "LOGO_FIRST": "[first word of business name]",
  "LOGO_SECOND": "[remaining words]",
  "PHONE": "{info.get('phone', 'Call for a Free Quote')}",
  "PHONE_RAW": "[digits only from phone number]",
  "CITY": "{info['city']}",
  "BUSINESS_TYPE": "[professional title e.g. Licensed Plumber, Nail Technician]",
  "HOURS": "Mon-Fri 9am-7pm · Sat-Sun 10am-6pm",
  "HERO_LINE_1": "[2-3 word bold headline]",
  "HERO_LINE_2": "[2-3 word accent line]",
  "HERO_LINE_3": "[2-3 word closing line]",
  "HERO_SUB": "[1-2 sentence description of what this business does for GTA customers]",
  "TRUST_1": "[trust point 1]",
  "TRUST_2": "Serving {info['city']} & GTA",
  "TRUST_3": "Free Consultations",
  "TRUST_4": "No Hidden Fees",
  "STAT_1_N": "500+", "STAT_1_L": "Happy Clients",
  "STAT_2_N": "4.9",  "STAT_2_L": "Google Rating",
  "STAT_3_N": "5+",   "STAT_3_L": "Years Experience",
  "STAT_4_N": "100%", "STAT_4_L": "Satisfaction",
  "SERVICES_TITLE": "[services headline for {biz_type}]",
  "SERVICES_SUB": "[1 sentence describing range of services]",
  "S1_TITLE": "[service 1 specific to {biz_type}]", "S1_DESC": "[2 sentences]",
  "S2_TITLE": "[service 2 specific to {biz_type}]", "S2_DESC": "[2 sentences]",
  "S3_TITLE": "[service 3 specific to {biz_type}]", "S3_DESC": "[2 sentences]",
  "S4_TITLE": "[service 4 specific to {biz_type}]", "S4_DESC": "[2 sentences]",
  "S5_TITLE": "[service 5 specific to {biz_type}]", "S5_DESC": "[2 sentences]",
  "S6_TITLE": "[service 6 specific to {biz_type}]", "S6_DESC": "[2 sentences]",
  "ABOUT_TITLE": "[about headline]",
  "ABOUT_P1": "[2-3 sentence paragraph about this {biz_type} business in {info['city']}]",
  "ABOUT_P2": "[2-3 sentence paragraph about their values and commitment]",
  "CRED_1": "[relevant credential for {biz_type}]",
  "CRED_2": "[relevant credential for {biz_type}]",
  "CRED_3": "[relevant credential for {biz_type}]",
  "CRED_4": "Proudly Serving the GTA",
  "WHY_TITLE": "[why choose us headline]",
  "W1_TITLE": "[reason 1]", "W1_DESC": "[2 sentences]",
  "W2_TITLE": "[reason 2]", "W2_DESC": "[2 sentences]",
  "W3_TITLE": "[reason 3]", "W3_DESC": "[2 sentences]",
  "W4_TITLE": "[reason 4]", "W4_DESC": "[2 sentences]",
  "REVIEWS_TITLE": "[reviews headline]",
  "R1_TEXT": "[realistic GTA review for {biz_type}]", "R1_NAME": "[First Name L.]", "R1_LOCATION": "[GTA city]",
  "R2_TEXT": "[realistic GTA review for {biz_type}]", "R2_NAME": "[First Name L.]", "R2_LOCATION": "[GTA city]",
  "R3_TEXT": "[realistic GTA review for {biz_type}]", "R3_NAME": "[First Name L.]", "R3_LOCATION": "[GTA city]",
  "CONTACT_TITLE": "[contact section headline]",
  "FOOTER_DESC": "[1-2 sentence footer description]"
}}"""

    message = claude.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=3000,
        messages=[{"role": "user", "content": prompt}]
    )
    raw = re.sub(r'^```[a-z]*\n?', '', message.content[0].text.strip())
    raw = re.sub(r'\n?```$', '', raw)
    for attempt in range(3):
        try:
            return json.loads(raw)
        except:
            if attempt < 2:
                print(f"   ⚠️ JSON parse failed, retrying...")
                time.sleep(2)
                message = claude.messages.create(
                    model="claude-sonnet-4-5",
                    max_tokens=3000,
                    messages=[{"role": "user", "content": prompt}]
                )
                raw = re.sub(r'^```[a-z]*\n?', '', message.content[0].text.strip())
                raw = re.sub(r'\n?```$', '', raw)
            else:
                print(f"   ❌ JSON parse failed after 3 attempts")
                return None

def fill_template(template_html, variables):
    result = template_html
    for key, value in variables.items():
        result = result.replace(f"{{{{{key}}}}}", str(value) if value else "")
    return result

def build_and_deploy(lead):
    biz_type = lead["type"].lower()
    template_name, accent_color, accent_light = TEMPLATE_MAP.get(
        biz_type, ("trades", "#1D4ED8", "#EFF6FF")
    )

    template_html = load_template(template_name)
    info = {
        "name": lead["name"],
        "city": lead["city"],
        "phone": lead.get("phone", ""),
        "description": "",
    }

    if not info["phone"]:
        info["phone"] = "Call for a Free Quote"

    variables = generate_content(info, biz_type, accent_color)
    if not variables:
        return None

    if lead.get("phone"):
        variables["PHONE"] = lead["phone"]
        variables["PHONE_RAW"] = ''.join(filter(str.isdigit, lead["phone"]))
    else:
        variables["PHONE"] = "Call for a Free Quote"
        variables["PHONE_RAW"] = ""

    if not variables.get("ACCENT_LIGHT"):
        variables["ACCENT_LIGHT"] = accent_light

    html = fill_template(template_html, variables)

    slug = re.sub(r'[^a-z0-9]+', '-', lead["name"].lower()).strip('-')
    folder = os.path.join(DEMOS_DIR, slug)
    os.makedirs(folder, exist_ok=True)

    with open(os.path.join(folder, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)

    return f"https://demos.wrenchdigital.ca/{slug}", slug

def deploy_all():
    print("   🚀 Deploying all demos...")
    try:
        subprocess.run(["git", "add", "."], check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Pipeline batch deploy"], check=True, capture_output=True)
        subprocess.run(["git", "push", "origin", "main"], check=True, capture_output=True)
        print("   ✅ All deployed!")
    except subprocess.CalledProcessError as e:
        print(f"   ⚠️  Deploy failed: {e}")

# ── Outreach Generator ────────────────────────────────────────────────────────

def generate_outreach(lead, demo_url):
    prompt = f"""Write a cold outreach email AND a text message for a local business with no website.

Business: {lead['name']}
Type: {lead['type']}
City: {lead['city']}
Phone: {lead.get('phone', '')}
Demo URL: {demo_url}

You are Shaan, a 20-year-old web designer from Mississauga. Wrench Digital — wrenchdigital.ca. Pricing starts at $699.

Return ONLY valid JSON:
{{
  "email_subject": "[subject line]",
  "email_body": "[friendly email under 120 words mentioning the free demo]",
  "text_message": "[casual text under 50 words mentioning the free demo URL]"
}}"""

    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
    )
    raw = re.sub(r'^```[a-z]*\n?', '', response.choices[0].message.content.strip())
    raw = re.sub(r'\n?```$', '', raw)
    try:
        return json.loads(raw)
    except:
        return {
            "email_subject": f"Free website demo for {lead['name']}",
            "email_body": f"Hey! I built a free demo website for your business. Check it out: {demo_url} — Shaan | Wrench Digital",
            "text_message": f"Hey! I noticed you don't have a website — I built you a free demo: {demo_url} — Shaan | Wrench Digital"
        }

# ── Main Pipeline ─────────────────────────────────────────────────────────────

def main():
    print("\n🚀 Wrench Digital — Full Pipeline\n")
    print("Finds leads → builds demos → generates outreach\n")

    target = int(input("How many leads do you want? (e.g. 10): ").strip())
    sent = load_sent()
    all_leads = []
    searched = set()

    print(f"\n🔍 Step 1: Finding {target} businesses without websites...\n")

    for city in GTA_CITIES:
        for biz_type in BUSINESS_TYPES:
            if len(all_leads) >= target:
                break

            key = f"{biz_type}_{city}"
            if key in searched:
                continue
            searched.add(key)

            print(f"   Searching {biz_type} in {city}...")
            results = search_maps(biz_type, city)
            time.sleep(1)

            for r in results:
                if len(all_leads) >= target:
                    break

                name = r.get("title", "")
                if name in sent:
                    continue

                website = r.get("website", "")
                status = check_website(website)
                if status == "has website":
                    continue

                # Double check with Google search
                if google_search_has_website(name, city):
                    print(f"   ⚠️  Skipping {name} — found website via Google")
                    continue

                phone = r.get("phone", r.get("formatted_phone_number", ""))
                address = r.get("address", "")
                rating = r.get("rating", "N/A")
                reviews = r.get("reviews", 0)

                print(f"   🎯 {name} — {status}")

                email, source = find_email(name, city)
                if email:
                    print(f"      ✉️  Email: {email} ({source})")
                else:
                    print(f"      📞 No email — phone only")

                all_leads.append({
                    "name": name,
                    "type": biz_type,
                    "city": city,
                    "address": address,
                    "phone": phone,
                    "email": email or "",
                    "email_source": source or "",
                    "rating": rating,
                    "reviews": reviews,
                    "website_status": status,
                })
                sent.add(name)
                save_sent(sent)

                print(f"      ✅ Lead {len(all_leads)}/{target}\n")

        if len(all_leads) >= target:
            break

    if not all_leads:
        print("No leads found.")
        return

    print(f"\n🏗️  Step 2: Building {len(all_leads)} demo websites...\n")

    for lead in all_leads:
        print(f"   Building demo for {lead['name']}...")
        result = build_and_deploy(lead)
        if result:
            url, slug = result
            lead["demo_url"] = url
            print(f"   ✅ {url}")
        else:
            lead["demo_url"] = ""
            print(f"   ❌ Failed to build demo for {lead['name']}")
        time.sleep(1)

    deploy_all()

    print(f"\n✉️  Step 3: Generating outreach messages...\n")

    for lead in all_leads:
        if not lead.get("demo_url"):
            continue
        print(f"   Writing outreach for {lead['name']}...")
        outreach = generate_outreach(lead, lead["demo_url"])
        lead["email_subject"] = outreach.get("email_subject", "")
        lead["email_body"] = outreach.get("email_body", "")
        lead["text_message"] = outreach.get("text_message", "")
        time.sleep(0.5)

    # Save CSV and auto open
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_file = f"pipeline_{timestamp}.csv"
    fields = ["name", "type", "city", "phone", "email", "website_status",
              "demo_url", "text_message", "email_subject", "email_body"]

    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(all_leads)

    import sys
    if sys.platform == "win32":
        os.startfile(csv_file)

    print(f"\n{'='*60}")
    print(f"✅ Pipeline complete!")
    print(f"   {len(all_leads)} leads found")
    print(f"   {len([l for l in all_leads if l.get('demo_url')])} demos built")
    print(f"   {len([l for l in all_leads if l.get('email')])} emails found")
    print(f"   Saved to: {csv_file}")
    print(f"{'='*60}")
    print(f"\n📋 CSV opened automatically — check it for all leads, demos, and messages!")

if __name__ == "__main__":
    main()