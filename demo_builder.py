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

    prompt = f"""You are an expert web designer. Generate a complete, beautiful, single-file HTML website for a local {biz_type} business.

Business name: {info['name']}
City: {info['city']}
Phone: {info.get('phone', 'Call for a quote')}
Info found online: {info.get('description', 'Local ' + biz_type + ' business')}

Design requirements:
- Modern, professional design with a color scheme that fits a {biz_type} business
- Single HTML file with all CSS and JS embedded
- Sections: Hero, About, Services, Why Choose Us, Reviews, Contact/CTA, Footer
- Mobile responsive with hamburger menu
- Smooth scroll animations
- Include a prominent "Get a Free Quote" button
- Use images from Unsplash Source with relevant keywords:
  - Hero: https://source.unsplash.com/1200x600/?{biz_type.replace(' ', '+')},professional
  - Each service gets a unique keyword, never repeat the same URL
- Add a subtle top banner: "⚡ Demo site built by Wrench Digital — wrenchdigital.ca"
- Services section: 5-6 realistic services for a {biz_type} business
- Reviews section: 3 realistic 5-star Google-style reviews with names
- Contact section with phone number prominently displayed
- Footer with business name, city, phone, copyright
- Make it look like a $2000 professional website

Return ONLY the complete HTML. Start with <!DOCTYPE html> and end with </html>. No markdown, no explanation."""

    message = claude.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=8000,
        messages=[{"role": "user", "content": prompt}]
    )

    html = message.content[0].text.strip()

    if html.startswith("```"):
        html = re.sub(r'^```[a-z]*\n?', '', html)
        html = re.sub(r'\n?```$', '', html)

    return html

def save_and_deploy(business_name, html):
    """Save the HTML file and push to GitHub so Vercel deploys it."""
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
        url, slug = save_and_deploy(business_name, html)

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