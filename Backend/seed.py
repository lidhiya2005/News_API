"""Startup seeding — populates the database with demo content on first run."""
from datetime import timedelta

from sqlalchemy.orm import Session

from auth import hash_password
from database import SessionLocal
from models import Article, Category, Source, User, utcnow
from utils import slugify, unique_slug

DEMO_USER = {
    "email": "demo@newsapp.com",
    "username": "demo",
    "password": "demo123",
    "full_name": "Demo Editor",
    "is_superuser": True,
}

CATEGORIES = [
    ("Technology", "Innovation, software, hardware, and the digital world."),
    ("Business", "Markets, startups, and corporate news."),
    ("Science", "Research, space, and scientific breakthroughs."),
    ("Health", "Medicine, wellness, and public health."),
    ("Sports", "Results, leagues, and athletes."),
    ("Entertainment", "Film, music, television, and celebrity culture."),
    ("World", "International affairs and global headlines."),
    ("Politics", "Government, policy, and elections."),
    ("Economy", "Finance, inflation, and economic policy."),
    ("Environment", "Climate, energy, and conservation."),
]

SOURCES = [
    ("TechCrunch", "https://techcrunch.com", "Technology", "Startup and technology news."),
    ("The Verge", "https://www.theverge.com", "Technology", "Technology, science, art, and culture."),
    ("Wired", "https://www.wired.com", "Technology", "Emerging technology and culture."),
    ("Reuters", "https://www.reuters.com", "World", "Global news agency."),
    ("BBC News", "https://www.bbc.com/news", "World", "International news and analysis."),
    ("Bloomberg", "https://www.bloomberg.com", "Business", "Business and financial news."),
    ("Forbes", "https://www.forbes.com", "Business", "Business, investing, and entrepreneurship."),
    ("Nature News", "https://www.nature.com/news", "Science", "Science research and discovery."),
    ("ESPN", "https://www.espn.com", "Sports", "Sports coverage and scores."),
    ("The Guardian", "https://www.theguardian.com", "Politics", "News, opinion, and analysis."),
    ("WHO News", "https://www.who.int/news", "Health", "Global public health updates."),
    ("National Geographic", "https://www.nationalgeographic.com", "Environment", "Science and exploration."),
    ("Variety", "https://variety.com", "Entertainment", "Entertainment industry news."),
]

# (title, category, source, author, days_ago, featured, breaking)
ARTICLE_SEEDS = [
    ("AI Assistants Are Moving From Chatbots to Autonomous Agents", "Technology", "Wired", "Aisha Khan", 0, True, True),
    ("Startup Funding Rebounds as Investors Return to Seed Stage", "Business", "TechCrunch", "Marcus Chen", 0, True, False),
    ("Quantum Computing Milestone Reached in Error Correction", "Science", "Nature News", "Dr. Lena Okafor", 1, True, False),
    ("New Global Health Initiative Targets Vaccine Equity", "Health", "WHO News", "Priya Sharma", 1, False, True),
    ("Underdog Stuns Champions in Season-Opening Upset", "Sports", "ESPN", "Tom Bradley", 2, False, False),
    ("Streaming Services Bet Big on Live Sports Rights", "Entertainment", "Variety", "Sofia Reyes", 2, False, False),
    ("Major Powers Agree on New Climate Accord Framework", "World", "Reuters", "James Whitfield", 3, True, False),
    ("Central Banks Signal Patience on Interest Rate Path", "Economy", "Bloomberg", "Elena Petrova", 3, False, True),
    ("Chipmakers Race to Meet Surging AI Hardware Demand", "Technology", "The Verge", "Daniel Kim", 4, False, False),
    ("Ocean Cleanup Project Removes Record Tonnage of Plastic", "Environment", "National Geographic", "Hannah Lee", 4, True, False),
    ("Election Commission Unveils Digital Voting Pilot", "Politics", "The Guardian", "Oliver Grant", 5, False, False),
    ("Breakthrough Drug Shows Promise in Early Trials", "Health", "WHO News", "Dr. Amara Diallo", 5, True, False),
    ("Electric Vehicle Sales Top Petrol for First Time", "Economy", "Bloomberg", "Nina Alvarez", 6, False, False),
    ("Open-Source Community Ships Major Framework Release", "Technology", "TechCrunch", "Rahul Mehta", 6, False, False),
    ("Ancient City Uncovered Beneath Desert Sands", "Science", "Nature News", "Dr. Samir Haddad", 7, True, False),
    ("Championship Final Goes to Overtime Thriller", "Sports", "ESPN", "Kelly Donovan", 7, False, False),
    ("Renewable Grid Hits New Share-of-Demand Record", "Environment", "Reuters", "Ingrid Berg", 8, False, True),
    ("Global Summit Concludes With Trade Framework Deal", "World", "BBC News", "Lucy Turner", 8, True, False),
    ("AI Regulation Talks Enter Final Negotiation Phase", "Politics", "The Guardian", "Henry Walsh", 9, False, False),
    ("Food Tech Startups Reinvent Plant-Based Protein", "Business", "Forbes", "Grace Liu", 9, False, False),
    ("Mars Rover Finds New Evidence of Ancient Water", "Science", "Nature News", "Dr. Omar Farouk", 10, True, False),
    ("Major Franchise Announces Streaming Spinoff Series", "Entertainment", "Variety", "Marco Silva", 10, False, False),
    ("Smartphone Makers Double Down on On-Device AI", "Technology", "The Verge", "Chloe Martin", 11, False, False),
    ("Small Business Optimism Hits Multi-Year High", "Business", "Forbes", "Ethan Brooks", 11, False, False),
    ("Vaccination Drive Expands to Remote Regions", "Health", "WHO News", "Dr. Yuki Tanaka", 12, False, False),
    ("Marathon Record Falls in Spectacular Finish", "Sports", "ESPN", "Ava Rodriguez", 12, False, False),
    ("Coastal Cities Announce Climate Adaptation Plans", "Environment", "National Geographic", "Felix Weber", 13, True, False),
    ("Tech Giants Face New Data Privacy Mandates", "Politics", "BBC News", "Sarah Connolly", 13, False, False),
    ("Global Markets Steady as Inflation Eases", "Economy", "Reuters", "David Nguyen", 14, False, False),
    ("Indie Film Sweeps International Awards Season", "Entertainment", "Variety", "Isabella Moreau", 14, False, True),
    ("Robotics Startup Unveils Warehouse Automation Suite", "Technology", "TechCrunch", "Kenji Sato", 15, False, False),
    ("Deep Sea Expedition Maps Unexplored Trench", "Science", "Nature News", "Dr. Mia Novak", 15, True, False),
    ("Semiconductor Subsidies Spark Global Manufacturing Race", "Economy", "Bloomberg", "Oliver Lindqvist", 16, False, False),
    ("Grassroots Movements Reshape Local Elections", "Politics", "The Guardian", "Anika Patel", 16, False, False),
    ("Solar and Wind Now Cheapest Power in Most Regions", "Environment", "Reuters", "Camille Dubois", 17, True, False),
    ("Health Tech Wearables Gain Clinical Validation", "Health", "WHO News", "Dr. Noah Fischer", 17, False, False),
]

_PARAGRAPHS = {
    "Technology": [
        "Industry analysts point to a rapid shift as companies move from incremental features toward platform-level integration, with early adopters reporting significant productivity gains.",
        "The announcement follows months of speculation, and developers have already begun building on the new interfaces. Observers expect wider adoption once stability guarantees are in place.",
        "Regulators are watching closely, but insiders say the technology's potential outweighs near-term concerns. A full rollout is expected within the next two quarters.",
    ],
    "Business": [
        "Market conditions have improved markedly this quarter, with deal flow returning to levels not seen since the previous cycle. Founders report renewed appetite from institutional investors.",
        "Advisors attribute the shift to clearer exit paths and improving unit economics across the sector. Several notable transactions are said to be in late-stage negotiation.",
        "Analysts caution that momentum must be matched by disciplined execution, but the overall trajectory remains positive heading into the next reporting period.",
    ],
    "Science": [
        "The peer-reviewed findings represent a significant step forward, with independent teams already attempting to reproduce the results. The work builds on a decade of cumulative research.",
        "Researchers involved in the study emphasize that more validation is needed before real-world deployment, yet the data so far is described as 'exceptionally promising'.",
        "Funding agencies have signaled interest in expanded follow-up studies, and the findings are expected to shape the field's agenda for years to come.",
    ],
    "Health": [
        "Public health officials describe the development as a meaningful milestone, though they stress that distribution and access remain critical challenges in the months ahead.",
        "Clinical teams reported manageable side-effect profiles in early cohorts, and expanded trials are already being organized across multiple regions.",
        "Experts urge continued vigilance and routine screening, noting that prevention remains the most effective strategy alongside new treatment options.",
    ],
    "Sports": [
        "Coaches and players alike described the performance as a statement result, with post-match analysis highlighting tactical adjustments that swung the momentum.",
        "The result reshapes the standings picture and sets up a compelling stretch run. Attendance and broadcast figures continue to trend upward this season.",
        "Commentators noted that the team's preparation and depth proved decisive, and attention now turns to the next round of fixtures.",
    ],
    "Entertainment": [
        "The project has generated considerable buzz, with early reactions praising the creative direction. Executives describe it as a cornerstone of the company's content strategy.",
        "Production details remain under wraps, but sources close to the project suggest a release window is being finalized and marketing will kick off shortly.",
        "Industry observers see the move as part of a broader shift toward premium, franchise-driven programming across streaming platforms.",
    ],
    "World": [
        "Diplomatic sources described the development as a constructive step, with further rounds of talks expected in the coming weeks. Several nations have already voiced support.",
        "The agreement follows months of negotiation and is being framed as a shared commitment to stability and cooperation on the global stage.",
        "Implementation will be phased, with working groups tasked to detail the mechanisms. Analysts say the political will exists, though execution risks remain.",
    ],
    "Politics": [
        "The proposal has drawn a mixed response across the political spectrum, with supporters citing efficiency gains and critics raising concerns about oversight and equity.",
        "Lawmakers are expected to hold hearings in the coming weeks, and amendments are likely as the legislation moves through committee.",
        "Political analysts note that the issue has broad public attention, making it a defining test for the current administration.",
    ],
    "Economy": [
        "Economists interpret the data as evidence that the policy stance is having its intended effect, while cautioning that the path ahead remains data-dependent.",
        "Treasury markets responded calmly, and currency markets showed limited volatility. Forecasters have revised near-term projections modestly upward.",
        "Households and businesses alike are watching closely, with consumer confidence surveys showing cautious optimism about the outlook.",
    ],
    "Environment": [
        "Environmental groups welcomed the announcement as an important signal, while calling for accelerated timelines and stronger enforcement mechanisms.",
        "The initiative pairs public funding with private investment, and pilot projects are expected to begin within the year across several key regions.",
        "Scientists stress that cumulative progress is what matters, noting that sustained policy and technology gains will be required to meet long-term targets.",
    ],
}

_GENERIC_PARAGRAPHS = [
    "The development has been in the works for some time, according to people familiar with the matter, and marks a notable shift in how the sector approaches the challenge.",
    "Reaction has been broadly positive, though a number of open questions remain. Further details are expected to be announced in the coming weeks.",
    "Stakeholders say the timing is significant, arriving as related efforts gather momentum. Analysts will be watching closely to see how the situation evolves.",
]


def _article_body(category_name: str) -> str:
    pool = _PARAGRAPHS.get(category_name, _GENERIC_PARAGRAPHS)
    return "\n\n".join(pool)


def seed_database(db: Session | None = None) -> dict:
    """Seed the database if it is empty. Safe to call on every startup."""
    own_session = db is None
    db = db or SessionLocal()

    try:
        created = {"categories": 0, "sources": 0, "articles": 0, "users": 0}
        if db.query(Category).count() == 0:
            for name, description in CATEGORIES:
                db.add(Category(name=name, slug=unique_slug(db, Category, name), description=description))
                created["categories"] += 1
            db.flush()

        if db.query(Source).count() == 0:
            categories_by_name = {c.name: c for c in db.query(Category).all()}
            for name, url, category_name, description in SOURCES:
                db.add(
                    Source(
                        name=name,
                        slug=unique_slug(db, Source, name),
                        url=url,
                        category=categories_by_name.get(category_name),
                        description=description,
                    )
                )
                created["sources"] += 1
            db.flush()

        if db.query(Article).count() == 0:
            categories_by_slug = {c.slug: c for c in db.query(Category).all()}
            sources_by_name = {s.name: s for s in db.query(Source).all()}
            now = utcnow()
            for title, category_name, source_name, author, days_ago, featured, breaking in ARTICLE_SEEDS:
                cat = categories_by_slug.get(slugify(category_name))
                published_at = now - timedelta(days=days_ago, hours=days_ago * 3 % 20)
                db.add(
                    Article(
                        title=title,
                        slug=unique_slug(db, Article, title),
                        summary=title,
                        content=_article_body(category_name),
                        author=author,
                        source=sources_by_name.get(source_name),
                        category=cat,
                        published_at=published_at,
                        is_featured=featured,
                        is_breaking=breaking,
                        views=100 + (days_ago * 37) % 4000,
                    )
                )
                created["articles"] += 1
            db.flush()

        if db.query(User).filter(User.email == DEMO_USER["email"]).first() is None:
            db.add(
                User(
                    email=DEMO_USER["email"],
                    username=DEMO_USER["username"],
                    full_name=DEMO_USER["full_name"],
                    hashed_password=hash_password(DEMO_USER["password"]),
                    is_superuser=DEMO_USER["is_superuser"],
                )
            )
            created["users"] += 1

        db.commit()
        return created
    finally:
        if own_session:
            db.close()
