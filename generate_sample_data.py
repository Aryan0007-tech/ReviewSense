"""
Script to generate the built-in sample dataset: product_reviews_and_sale.csv
Contains 1,000 realistic e-commerce product reviews across Amazon, Flipkart, and Myntra.
"""
import random
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

random.seed(42)
np.random.seed(42)

platforms = ["Amazon", "Flipkart", "Myntra"]
platform_weights = [0.45, 0.35, 0.20]

user_first_names = [
    "Aarav", "Priya", "Rahul", "Ananya", "Rohan", "Sneha", "Vikram", "Neha",
    "Aditya", "Pooja", "Arjun", "Kavya", "Varun", "Isha", "Kunal", "Meera",
    "Amit", "Divya", "Siddharth", "Tanvi", "Rishi", "Anjali", "Gaurav", "Simran",
    "Rajesh", "Sunita", "Deepak", "Ritu", "Suresh", "Geeta", "Manoj", "Shweta"
]
user_last_names = [
    "Sharma", "Patel", "Verma", "Gupta", "Mehta", "Iyer", "Reddy", "Singh",
    "Nair", "Chopra", "Joshi", "Bhat", "Kapoor", "Saxena", "Malhotra", "Das"
]

reviews_templates = {
    "positive": [
        ("The sound quality is crisp and bass is punchy. Truly exceeded my expectations!", "Electronics & Gadgets", 5),
        ("Battery backup is outstanding. Lasts nearly two full days on moderate usage.", "Electronics & Gadgets", 5),
        ("Superfast charging and seamless bluetooth connectivity. Great gadget for daily use.", "Electronics & Gadgets", 4),
        ("The screen display is vivid with vibrant colors. Absolute value for money.", "Electronics & Gadgets", 5),
        ("Compact, lightweight, and very durable build. Highly recommended!", "Electronics & Gadgets", 4),
        ("Very comfortable fit and pure cotton fabric. Looks stylish and breathable.", "Fashion & Apparel", 5),
        ("Color is exact as shown in the picture. Perfect size and top notch stitching.", "Fashion & Apparel", 4),
        ("Excellent sneakers with soft sole cushioning. Perfect for jogging and daily walk.", "Fashion & Apparel", 5),
        ("Fabric quality is premium and doesn't shrink after wash. Worth every penny.", "Fashion & Apparel", 5),
        ("Stunning design and fits like a glove. Received many compliments at work.", "Fashion & Apparel", 4),
        ("Non-stick coating is genuine and easy to clean. Cooking without oil is a breeze.", "Home & Kitchen", 5),
        ("Very sturdy stainless steel build. Elegant finish and works great on induction.", "Home & Kitchen", 4),
        ("The memory foam pillow gave immediate relief to my neck pain. Best purchase ever.", "Home & Kitchen", 5),
        ("Water bottle keeps drinks ice-cold for over 24 hours. Solid leakproof cap.", "Home & Kitchen", 5),
        ("Bright warm lighting that instantly transformed the aesthetic of my bedroom.", "Home & Kitchen", 4),
        ("Cleanses gently without stripping moisture. My sensitive skin feels soft and radiant.", "Beauty & Personal Care", 5),
        ("Long-lasting subtle fragrance that stays fresh all day. Loved the packaging.", "Beauty & Personal Care", 5),
        ("Remarkable difference in hair texture after just two weeks of regular use.", "Beauty & Personal Care", 4),
        ("Hydrating serum with non-sticky texture. Absorbs quickly into skin.", "Beauty & Personal Care", 5),
        ("Grippy, non-slip yoga mat with decent thickness. Does not slide on tiles.", "Sports & Fitness", 5),
        ("Heavy duty resistance bands. Great elasticity and very handy gym bag.", "Sports & Fitness", 4),
        ("Captivating storyline and beautifully written. Finished the entire book in two sittings.", "Books & Media", 5),
        ("Prompt delivery and secure package wrapping. Arrived in pristine condition.", "General", 5),
        ("Genuine product with official warranty registered smoothly. Outstanding service!", "General", 5),
    ],
    "neutral": [
        ("Decent product for this price bracket. Nothing extraordinary but works fine.", "Electronics & Gadgets", 3),
        ("Average sound output. Good for podcasts but lacks deep bass for music.", "Electronics & Gadgets", 3),
        ("Display is okay, though outdoor visibility under direct sunlight is average.", "Electronics & Gadgets", 3),
        ("Battery life is mediocre, lasts around 6-7 hours. Normal charging speed.", "Electronics & Gadgets", 3),
        ("Cloth material is okay, but feels slightly synthetic. Size is just about right.", "Fashion & Apparel", 3),
        ("The color is a little duller compared to website photos, but fit is acceptable.", "Fashion & Apparel", 3),
        ("Average comfort shoes. Decent for casual wear but not suitable for running.", "Fashion & Apparel", 3),
        ("Stitching is fine, though a couple of loose threads were visible near hem.", "Fashion & Apparel", 3),
        ("Average build quality. The plastic feels lightweight but serves everyday purpose.", "Home & Kitchen", 3),
        ("Heats up reasonably well, though temperature regulation is somewhat inconsistent.", "Home & Kitchen", 3),
        ("Fragrance is pleasant but fades away within two to three hours.", "Beauty & Personal Care", 3),
        ("Moisturizer is okay for normal skin, but might feel greasy in humid weather.", "Beauty & Personal Care", 3),
        ("Acceptable grip, though slight odor during the first few days of unboxing.", "Sports & Fitness", 3),
        ("The plot had potential but pacing in the middle chapters was rather slow.", "Books & Media", 3),
        ("Standard delivery time. Item is acceptable for routine use.", "General", 3),
        ("Reasonable quality considering the discount, but don't expect premium tier.", "General", 3)
    ],
    "negative": [
        ("Extremely disappointed. Device stopped turning on after barely one week of use.", "Electronics & Gadgets", 1),
        ("Poor battery drainage. Battery drops from 80% to 10% in just two hours.", "Electronics & Gadgets", 1),
        ("Constant bluetooth disconnection issues and terrible microphone voice quality.", "Electronics & Gadgets", 2),
        ("Charger port became loose within three days. Replacement request rejected.", "Electronics & Gadgets", 1),
        ("Overheats terribly while charging. Feels like a serious safety hazard.", "Electronics & Gadgets", 1),
        ("Very poor fabric quality. Shrunk horribly and bled color on first gentle wash.", "Fashion & Apparel", 1),
        ("Sizing is completely inaccurate. Ordered XL but fits tighter than a Medium.", "Fashion & Apparel", 1),
        ("Sole detached after wearing just twice. Extremely cheap glue and poor craftsmanship.", "Fashion & Apparel", 1),
        ("Received duplicate or counterfeit product. Tag looks suspicious and material feels cheap.", "Fashion & Apparel", 1),
        ("Defective zipper that broke on the first zip. Total waste of hard earned money.", "Fashion & Apparel", 2),
        ("Non-stick coating started peeling off within two weeks. Absolutely harmful.", "Home & Kitchen", 1),
        ("Lid does not seal properly and leaks hot liquid from sides. Very dangerous.", "Home & Kitchen", 1),
        ("Cheap brittle plastic that cracked on arrival. Packaging had zero bubble wrap.", "Home & Kitchen", 1),
        ("Caused severe skin redness and allergic rash. Strong harsh chemical smell.", "Beauty & Personal Care", 1),
        ("Bottle was half empty and seal was clearly broken when delivered.", "Beauty & Personal Care", 1),
        ("Mat tore along the edge during simple stretching. Very low durability.", "Sports & Fitness", 1),
        ("Book had missing pages from chapter 4 to 6 and inverted binding.", "Books & Media", 1),
        ("Horrible customer support and delayed delivery by 12 days. Never buying again.", "General", 1),
        ("Product received in crushed box with visible dents. Terrible experience.", "General", 1),
        ("Misleading product description. Features advertised are entirely missing.", "General", 1)
    ]
}

data = []
start_date = datetime(2024, 1, 1)

# Generate 1000 records
for i in range(1, 1001):
    sentiment = np.random.choice(["positive", "neutral", "negative"], p=[0.58, 0.20, 0.22])
    platform = np.random.choice(platforms, p=platform_weights)
    
    template, cat, base_rating = random.choice(reviews_templates[sentiment])
    
    # Add minor variations or repeated reviews
    # ~8% chance of repeating an exact popular review to showcase unique text optimization!
    if i > 50 and random.random() < 0.08:
        # Pick from earlier entry
        prev = random.choice(data[:min(i-1, 100)])
        review_text = prev["Text"]
        cat = prev["Category"]
        sentiment = prev["Label"]
        base_rating = prev["Rating"]
    else:
        # Subtle variations
        prefixes = ["", "Honest feedback: ", "Update: ", "Purchased recently. ", "Verified review: "]
        suffixes = ["", " Would recommend.", " Not worth it.", " Just okay.", " Excellent choice.", " Beware!"]
        if sentiment == "positive" and random.random() < 0.3:
            review_text = random.choice(prefixes) + template + (random.choice(suffixes) if random.random() < 0.5 else "")
        elif sentiment == "negative" and random.random() < 0.3:
            review_text = random.choice(prefixes) + template + (random.choice(suffixes) if random.random() < 0.5 else "")
        else:
            review_text = template
            
    # Rating tweak with minor noise
    if sentiment == "positive":
        rating = random.choices([4, 5, 3], weights=[0.25, 0.70, 0.05])[0]
    elif sentiment == "neutral":
        rating = random.choices([2, 3, 4], weights=[0.20, 0.65, 0.15])[0]
    else:
        rating = random.choices([1, 2, 3], weights=[0.70, 0.25, 0.05])[0]
        
    user_name = f"{random.choice(user_first_names)} {random.choice(user_last_names)}"
    user_id = f"USR-{random.randint(10000, 99999)}"
    price = round(random.uniform(299, 4999), 2)
    random_days = random.randint(0, 320)
    rev_date = (start_date + timedelta(days=random_days)).strftime("%Y-%m-%d")
    
    data.append({
        "Text": review_text.strip(),
        "Label": sentiment,
        "Window": platform,
        "User Name": user_name,
        "User ID": user_id,
        "Rating": rating,
        "Category": cat,
        "Price": price,
        "Date": rev_date
    })

df = pd.DataFrame(data)
import os
os.makedirs("data", exist_ok=True)
csv_path = "data/product_reviews_and_sale.csv"
df.to_csv(csv_path, index=False)
print(f"Generated {len(df)} rows in {csv_path}")
print(df.head(3))
