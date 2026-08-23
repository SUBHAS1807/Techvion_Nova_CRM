"""Seed the database with 20 clearly-marked DEMO leads."""

import os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import SessionLocal, engine, Base, run_migrations
from backend.models import Lead, OutreachActivity
from datetime import datetime, timezone, timedelta

def seed():
    run_migrations()
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # Clear existing demo leads or check count
    if db.query(Lead).count() > 0:
        print(f"Database already has {db.query(Lead).count()} leads.")
        db.close()
        return

    now = datetime.now(timezone.utc)

    demo_data = [
        ("TVN-000001", "[DEMO] Brew Haven Cafe", "Amit Roy", "Cafe", "Kolkata", "Google Places API",
         "+91 98300 12345", "info@brewhaven.demo", "https://brewhaven.demo", "@brewhaven", "fb.com/brewhaven",
         "Outdated", "Park Street, Kolkata, West Bengal", 4.4, 210, 50, "ChIJN1t_tDeuEmsRUsoyG83frY4"),

        ("TVN-000002", "[DEMO] The Daily Grind Coffee", "Sneha Mukherjee", "Coffee Shop", "Kolkata", "Google Places API",
         "+91 98300 23456", "contact@dailygrind.demo", "", "@dailygrindkol", "",
         "No Website", "Salt Lake Sector 5, Kolkata", 4.6, 430, 70, "ChIJ2eUgeAK6j4AR30S_4nd4kKg"),

        ("TVN-000003", "[DEMO] Sugar & Spice Artisan Bakery", "Priya Sen", "Bakery", "Howrah", "Google Places API",
         "+91 98300 34567", "hello@sugarspice.demo", "https://sugarspice.demo", "@sugarspice", "fb.com/sugarspice",
         "Good", "GT Road, Howrah", 4.2, 115, 25, "ChIJ3Zl59eY9j4ARr_eE_oY19eU"),

        ("TVN-000004", "[DEMO] Chai Sutta Bar & Cafe", "Rahul Das", "Tea Shop", "Delhi", "Google Places API",
         "+91 98110 45678", "", "", "@csbdelhi", "fb.com/csbdelhi",
         "No Website", "Connaught Place, New Delhi", 4.1, 520, 70, "ChIJ4Xk55uX0j4ARjFf64aY18yT"),

        ("TVN-000005", "[DEMO] Midnight Espresso Bistro", "Kavita Sharma", "Bistro", "Mumbai", "Google Places API",
         "+91 98200 56789", "reservations@midnightbistro.demo", "https://midnightbistro.demo", "@midnightbistro", "",
         "Good", "Bandra West, Mumbai, Maharashtra", 4.7, 890, 20, "ChIJ5Zl68w_1j4ARhUj75aY19zX"),

        ("TVN-000006", "[DEMO] QuickBite Cafe & Bites", "Manish Tiwari", "Fast Food Restaurant", "Bengaluru", "Google Places API",
         "+91 98450 67890", "orders@quickbite.demo", "https://quickbite.demo", "", "",
         "Broken", "Indiranagar, Bengaluru, Karnataka", 3.8, 85, 65, "ChIJ6Zl79x_2j4ARiVk86aY20aY"),

        ("TVN-000007", "[DEMO] CloudChef Artisanal Kitchen", "Ananya Patel", "Cloud Kitchen", "Pune", "Google Places API",
         "+91 98600 78901", "partner@cloudchef.demo", "", "@cloudchefpune", "fb.com/cloudchefpune",
         "No Website", "Koregaon Park, Pune, Maharashtra", 4.5, 310, 75, "ChIJ7Zl80y_3j4ARjWl97aY21bZ"),

        ("TVN-000008", "[DEMO] The Sweet Spot Patisserie", "Rohan Banerjee", "Dessert Shop", "Kolkata", "Google Places API",
         "+91 98300 89012", "sweets@sweetspot.demo", "https://sweetspot.demo", "@thesweetspot", "",
         "Under Construction", "Ballygunge, Kolkata, West Bengal", 4.3, 140, 45, "ChIJ8Zl91z_4j4ARkXm08aY22ca"),

        ("TVN-000009", "[DEMO] Brew & Barrel Roastery", "Siddharth Joshi", "Cafe", "Goa", "Google Places API",
         "+91 98220 90123", "", "https://brewbarrel.demo", "", "fb.com/brewbarrel",
         "Outdated", "Anjuna, Goa", 4.8, 620, 50, "ChIJ9Zl02a_5j4ARlYn19aY23db"),

        ("TVN-000010", "[DEMO] FoodCourt Central Cafe", "Deepa Nair", "Food Court", "Chennai", "Google Places API",
         "+91 98400 01234", "admin@foodcourtcentral.demo", "https://foodcourtcentral.demo", "", "",
         "E-commerce Website", "T Nagar, Chennai, Tamil Nadu", 3.9, 190, 20, "ChIJaZl13b_6j4ARmZo20aY24ec"),

        ("TVN-000011", "[DEMO] Aroma Royal Cafe", "Vikram Singh", "Cafe", "Jaipur", "Google Places API",
         "+91 98290 12345", "hello@aromacafe.demo", "", "@aromajaipur", "fb.com/aromajaipur",
         "No Website", "C-Scheme, Jaipur, Rajasthan", 4.6, 380, 75, "ChIJbZl24c_7j4ARnap31aY25fd"),

        ("TVN-000012", "[DEMO] Beans & Brews Cafe", "Tanvi Desai", "Coffee Shop", "Ahmedabad", "Google Places API",
         "+91 98250 23456", "info@beansbrews.demo", "https://beansbrews.demo", "@beansbrews", "",
         "Outdated", "Bodakdev, Ahmedabad, Gujarat", 4.3, 240, 55, "ChIJcZl35d_8j4ARobq42aY26ge"),

        ("TVN-000013", "[DEMO] Crust & Cream Specialty Bakery", "Nikhil Kapoor", "Bakery", "Lucknow", "Google Places API",
         "+91 98390 34567", "", "", "@crustandcream", "fb.com/crustandcream",
         "No Website", "Hazratganj, Lucknow, Uttar Pradesh", 4.4, 175, 70, "ChIJdZl46e_9j4ARpcr53aY27hf"),

        ("TVN-000014", "[DEMO] Spice Route Heritage Cafe", "Meera Iyer", "Restaurant", "Hyderabad", "Google Places API",
         "+91 98490 45678", "book@spiceroute.demo", "https://spiceroute.demo", "@spiceroute", "fb.com/spiceroute",
         "Good", "Banjara Hills, Hyderabad, Telangana", 4.7, 730, 20, "ChIJeZl57f_0j4ARqds64aY28ig"),

        ("TVN-000015", "[DEMO] Filter Kaapi House", "Arun Kumar", "Cafe", "Chennai", "Google Places API",
         "+91 98400 56789", "welcome@filterkaapi.demo", "https://filterkaapi.demo", "", "",
         "Broken", "Mylapore, Chennai, Tamil Nadu", 4.5, 410, 60, "ChIJfZl68g_1j4ARret75aY29jh"),

        ("TVN-000016", "[DEMO] Wok & Roll Asian Cafe", "Jenny Chang", "Restaurant", "Kolkata", "Google Places API",
         "+91 98300 67890", "eat@wokandroll.demo", "", "@wokandrollkol", "fb.com/wokandrollkol",
         "No Website", "Tangra, Kolkata, West Bengal", 4.6, 560, 75, "ChIJgZl79h_2j4ARsfu86aY30ki"),

        ("TVN-000017", "[DEMO] The Frosting Factory", "Ishita Ghosh", "Dessert Shop", "Kolkata", "Google Places API",
         "+91 98300 78901", "", "https://frostingfactory.demo", "@frostingfactory", "",
         "Under Construction", "New Town, Kolkata, West Bengal", 4.2, 95, 40, "ChIJhZl80i_3j4ARtgv97aY31lj"),

        ("TVN-000018", "[DEMO] Perk Up Speciality Roasters", "Aman Gupta", "Coffee Shop", "Noida", "Google Places API",
         "+91 98180 89012", "hello@perkup.demo", "https://perkup.demo", "@perkupcoffee", "fb.com/perkup",
         "Outdated", "Sector 18, Noida, Uttar Pradesh", 4.5, 310, 50, "ChIJiZl91j_4j4ARugw08aY32mk"),

        ("TVN-000019", "[DEMO] Green Leaf Organic Cafe", "Swati Reddy", "Cafe", "Bengaluru", "Google Places API",
         "+91 98450 90123", "organic@greenleaf.demo", "", "@greenleafcafe", "",
         "No Website", "Koramangala, Bengaluru, Karnataka", 4.8, 640, 80, "ChIJjZl02k_5j4ARvhx19aY33nl"),

        ("TVN-000020", "[DEMO] Chaat & Chai Lounge", "Kunal Agarwal", "Tea Shop", "Surat", "Google Places API",
         "+91 98250 01234", "", "https://chaatchai.demo", "@chaatchaisurat", "fb.com/chaatchai",
         "Good", "Vesu, Surat, Gujarat", 4.4, 280, 20, "ChIJkZl13l_6j4ARwiy20aY34om"),
    ]

    for item in demo_data:
        lead = Lead(
            lead_id=item[0],
            business_name=item[1],
            owner_name=item[2],
            business_type=item[3],
            city=item[4],
            lead_source=item[5],
            phone=item[6],
            email=item[7],
            email_source="Business Website" if item[7] else None,
            email_source_url=item[8] if item[7] and item[8] else None,
            email_verification_status="Valid Format" if item[7] else "Not Checked",
            current_website=item[8],
            instagram=item[9],
            facebook=item[10],
            website_status=item[11],
            address=item[12],
            rating=item[13],
            google_rating=item[13],
            review_count=item[14],
            google_reviews=item[14],
            lead_score=item[15],
            google_place_id=item[16],
            google_maps_url=f"https://www.google.com/maps/place/?q=place_id:{item[16]}",
            source_url=f"https://www.google.com/maps/place/?q=place_id:{item[16]}",
            is_demo=True,
            outreach_status="Not Contacted" if "TVN-00001" in item[0] else ("Contacted" if "TVN-00000" in item[0] else "Follow-up"),
            response_status="Replied" if item[15] < 30 else "No Response",
            deal_status="Negotiation" if item[15] == 20 else "Open",
            project_status="UI/UX Design" if item[0] == "TVN-000003" else "Not Started",
            first_contact_date=now - timedelta(days=5) if item[6] else None,
            next_followup_date=now + timedelta(days=2) if item[15] >= 50 else None,
            remarks=f"Sample demo record ({item[3]} in {item[4]})",
        )
        db.add(lead)
        db.add(OutreachActivity(
            lead_id=item[0],
            activity_type="Lead Created",
            description="Demo lead initialized",
            result="Demo",
            created_by="Seed Script",
        ))

    db.commit()
    print("Successfully seeded 20 DEMO leads.")
    db.close()

if __name__ == "__main__":
    seed()
