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
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
claude = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
DEMOS_DIR = "demos"

def search_business_info(business_name, city):
    """Scrape everything we can find about this business online."""
    print(f"   🔍 Researching {business_name}...")
    info = {
        "name": business_name,
        "city": city,
        "reviews": [],
        "services": [],
        "phone": "",
        "description": "",
    }

    try:
        query = f'"{business_name}" {city} reviews services'
        url = f"https://www.google.com/search?q={requests.utils.quote(query)}&num=5"
        resp = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")
        text = soup.get_text()

        # Extract phone numbers
        phones = re.findall(r'[\+\(]?[1-9][0-9 .\-\(\)]{8,}[0-9]', text)
        if phones:
            info["phone"] = phones[0]

        # Get snippet text for context
        snippets = []
        for span in soup.find_all("div", class_=re.compile("BNeawe|s3v9rd|St3YJ")):
            t = span.get_text().strip()
            if len(t) > 40 and business_name.lower()[:5] in t.lower():
                snippets.append(t)
        info["description"] = " ".join(snippets[:3])

    except Exception as e:
        print(f"   ⚠️  Could not scrape info: {e}")

    return info

def generate_website(info, biz_type):
    """Use Claude to generate a full HTML website for this business."""
    print(f"   🤖 Generating website with Claude...")

    image_keywords = {
        "handyman": ["tools", "home-repair", "renovation", "carpentry", "maintenance"],
        "landscaping": ["garden", "lawn", "landscape", "outdoor", "grass"],
        "snow removal": ["snow", "winter", "driveway", "ice", "clearing"],
        "cleaning service": ["cleaning", "spotless", "house", "mop", "hygiene"],
        "painting contractor": ["painting", "brush", "wall", "color", "interior"],
        "fence installer": ["fence", "wood", "backyard", "gate", "privacy"],
        "flooring installer": ["floor", "hardwood", "tile", "interior", "renovation"],
        "tile installer": ["tile", "bathroom", "kitchen", "ceramic", "grout"],
        "junk removal": ["truck", "removal", "hauling", "cleanup", "disposal"],
        "moving company": ["moving", "boxes", "truck", "relocation", "packing"],
        "plumber": ["plumbing", "pipes", "water", "bathroom", "tools"],
        "electrician": ["electrical", "wiring", "tools", "safety", "power"],
        "hvac": ["hvac", "airconditioning", "heating", "ventilation", "duct"],
        "contractor": ["construction", "building", "tools", "renovation", "concrete"],
    }
    keywords = image_keywords.get(biz_type.lower(), ["professional", "work", "tools", "service", "team"])

    prompt = f"""You are an expert web designer who builds high-end websites for local trades businesses. Generate a complete, beautiful, single HTML file website.

Business name: {info['name']}
City: {info['city']}
Phone: {info.get('phone', 'Call for a quote')}
Business type: {biz_type}
Info found online: {info.get('description', '')}

DESIGN STYLE:
- Clean, modern, premium feel — like a $2,000 professional website
- White or off-white background (#FAFAFA), dark charcoal text (#1a1a1a)
- ONE strong accent color that fits the business type (e.g. deep green for landscaping, navy for plumbing, warm orange for handyman)
- NO gradients on backgrounds
- NO emojis anywhere — use clean CSS icons or SVG symbols only
- Google Fonts — use Inter for body, a strong display font for headings
- Subtle box shadows, rounded corners, smooth hover effects
- Full width sections with proper padding

SECTIONS (include ALL of these in order):
1. TOP BANNER — thin bar: "Demo site by Wrench Digital — wrenchdigital.ca"
2. NAV — logo left, links right (Home, Services, About, Contact), phone number, sticky on scroll
3. HERO — full width, background image with dark overlay, large headline, subheading, two CTA buttons
4. TRUST BAR — 3-4 trust signals in a row (Licensed & Insured, Serving GTA, Free Estimates, etc.)
5. SERVICES — grid of 4-6 service cards, each with a clean SVG icon, title, 2-3 line description
6. ABOUT — two column layout, text left, image right
7. WHY CHOOSE US — 3-4 points with icons
8. REVIEWS — 3 realistic 5-star reviews with first name + last initial, CSS gold stars
9. CONTACT FORM — split layout: left has phone/hours, right has form (Name, Phone, Email, Service dropdown, Message, Submit)
10. FOOTER — dark background, logo, services list, contact info, "Website by Wrench Digital"

IMAGES:
- Hero: https://picsum.photos/seed/{keywords[0]}hero/1400/700
- About: https://picsum.photos/seed/{keywords[1]}about/800/600
- Service cards use seeds: {keywords[0]}s1, {keywords[1]}s2, {keywords[2]}s3, {keywords[3]}s4 — all 400x300

COPY:
- Write realistic specific copy for a {biz_type} business in {info['city']}
- Reviews should sound like real GTA homeowners
- NO fake statistics unless found in: {info.get('description', '')}
- All CTA buttons link to #contact or #services

TECHNICAL:
- All CSS in <style> tag
- html {{ scroll-behavior: smooth; }}
- Sticky nav with JS scroll shadow
- Mobile responsive hamburger menu
- Form submit shows thank you message via JS

Return ONLY complete HTML from <!DOCTYPE html> to </html>. No markdown. No explanation."""

    message = claude.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=8000,
        messages=[{"role": "user", "content": prompt}]
    )

    if not message.content or not message.content[0].text:
        print(f"   ❌ Claude returned empty response. Stop reason: {message.stop_reason}")
        return None

    html = message.content[0].text.strip()

    if html.startswith("```"):
        html = re.sub(r'^```[a-z]*\n?', '', html)
        html = re.sub(r'\n?```$', '', html)

    return html

def save_and_deploy(business_name, html):
    """Save the HTML file and push to GitHub so Vercel deploys it."""
    if not html:
        print("   ❌ No HTML to save, skipping.")
        return None, None
    # Create URL-friendly slug
    slug = re.sub(r'[^a-z0-9]+', '-', business_name.lower()).strip('-')
    folder = os.path.join(DEMOS_DIR, slug)
    os.makedirs(folder, exist_ok=True)

    # Save as index.html
    filepath = os.path.join(folder, "index.html")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"   💾 Saved to {filepath}")

    # Push to GitHub
    print(f"   🚀 Deploying to Vercel...")
    try:
        subprocess.run(["git", "add", "."], check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", f"Add demo: {business_name}"],
                      check=True, capture_output=True)
        subprocess.run(["git", "push", "origin", "main"],
                      check=True, capture_output=True)
        print(f"   ✅ Deployed!")
    except subprocess.CalledProcessError as e:
        print(f"   ⚠️  Git push failed: {e}")

    url = f"https://demos.wrenchdigital.ca/{slug}"
    return url, slug

def main():
    print("\n🏗️  Wrench Digital — Demo Builder\n")

    mode = input("Build demo for (1) specific business or (2) leads from CSV? [1/2]: ").strip()

    if mode == "1":
        business_name = input("Business name: ").strip()
        city = input("City: ").strip()
        biz_type = input("Business type (e.g. handyman, landscaping): ").strip()

        info = search_business_info(business_name, city)
        html = generate_website(info, biz_type)
        result = save_and_deploy(business_name, html)
        if not result[0]:
            print("Demo generation failed. Try again.")
            return
        url, slug = result

        print(f"\n🎉 Demo ready!")
        print(f"   URL: {url}")
        print(f"\n📱 Text to send:")
        print(f'   "Hey {business_name.split()[0]}! I noticed you don\'t have a website — I took 10 minutes and built you a free demo. Check it out: {url} — Shaan | Wrench Digital"')

    elif mode == "2":
        import csv
        import glob

        # Find latest CSV
        csvs = glob.glob("../cold-emailer/leads_*.csv")
        if not csvs:
            csvs = glob.glob("leads_*.csv")
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

            print(f"\n🏗️  Building demo for {name}...")
            info = search_business_info(name, city)
            if phone:
                info["phone"] = phone

            html = generate_website(info, biz_type)
            url, slug = save_and_deploy(name, html)

            results.append({"name": name, "phone": phone, "demo_url": url})
            print(f"   ✅ {url}")
            time.sleep(2)

        print(f"\n\n🎉 Done! {len(results)} demos built.\n")
        print(f"{'Business':<35} {'Phone':<20} {'Demo URL'}")
        print("-" * 80)
        for r in results:
            print(f"{r['name']:<35} {r['phone']:<20} {r['demo_url']}")

if __name__ == "__main__":
    main()