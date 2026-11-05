"""
database/models.py - Async SQLite database models using aiosqlite
"""
import aiosqlite
import logging
import os
from config import settings

logger = logging.getLogger(__name__)

DB_PATH = os.path.abspath(settings.DB_PATH)


from contextlib import asynccontextmanager

@asynccontextmanager
async def get_db():
    """Async context manager for SQLite database connection."""
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    try:
        yield db
    finally:
        await db.close()


async def init_db() -> None:
    """Initialize all database tables."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    logger.info(f"Initializing database at {DB_PATH}")

    async with aiosqlite.connect(DB_PATH) as db:
        # --- users table ---
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                name            TEXT,
                email           TEXT UNIQUE,
                phone           TEXT,
                location        TEXT,
                linkedin_url    TEXT,
                github_url      TEXT,
                target_roles    TEXT DEFAULT '[]',
                experience_level TEXT,
                geographies     TEXT DEFAULT '[]',
                resume_path     TEXT,
                resume_text     TEXT,
                skills          TEXT DEFAULT '[]',
                projects        TEXT DEFAULT '[]',
                created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Migration: ensure github_url and projects columns exist if table was already created
        cursor = await db.execute("PRAGMA table_info(users)")
        existing_cols = [row[1] for row in await cursor.fetchall()]
        if "github_url" not in existing_cols:
            await db.execute("ALTER TABLE users ADD COLUMN github_url TEXT")
        if "projects" not in existing_cols:
            await db.execute("ALTER TABLE users ADD COLUMN projects TEXT DEFAULT '[]'")

        # --- jobs table ---
        await db.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id              TEXT PRIMARY KEY,
                title           TEXT NOT NULL,
                company         TEXT NOT NULL,
                location        TEXT,
                platform        TEXT CHECK(platform IN ('linkedin','internshala','naukri','indeed','wellfound','other')),
                url             TEXT,
                description     TEXT,
                salary_range    TEXT,
                job_type        TEXT CHECK(job_type IN ('full-time','internship','contract','part-time','other')),
                match_score     REAL DEFAULT 0.0,
                status          TEXT DEFAULT 'pending' CHECK(status IN ('pending','approved','rejected','applied')),
                scraped_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                raw_data        TEXT DEFAULT '{}'
            )
        """)

        # --- applications table ---
        await db.execute("""
            CREATE TABLE IF NOT EXISTS applications (
                id                   TEXT PRIMARY KEY,
                job_id               TEXT NOT NULL REFERENCES jobs(id),
                user_id              INTEGER REFERENCES users(id),
                status               TEXT DEFAULT 'applied'
                                     CHECK(status IN ('applied','in_review','interview','rejected','offer')),
                cover_letter_text    TEXT,
                tailored_resume_path TEXT,
                applied_at           TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_updated         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                notes                TEXT
            )
        """)

        # --- emails table (inbox & outbox) ---
        await db.execute("""
            CREATE TABLE IF NOT EXISTS emails (
                id              TEXT PRIMARY KEY,
                application_id  TEXT REFERENCES applications(id),
                direction       TEXT CHECK(direction IN ('outbound', 'inbound')),
                sender          TEXT NOT NULL,
                recipient       TEXT NOT NULL,
                subject         TEXT NOT NULL,
                body            TEXT NOT NULL,
                status          TEXT DEFAULT 'delivered',
                created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # --- agent_messages table ---
        await db.execute("""
            CREATE TABLE IF NOT EXISTS agent_messages (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id  TEXT NOT NULL,
                role        TEXT CHECK(role IN ('user','assistant')),
                agent_name  TEXT,
                content     TEXT,
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # --- Seed / Enrich profile with verified GitHub data ---
        import json as _json
        projects_seed = [
            {
                "title": "VehicleIQ - Real-time Vehicle Health & Failure Prevention System",
                "tech_stack": ["Python", "TensorFlow", "LSTM", "Scikit-learn", "FastAPI", "Next.js 14", "OBD-II Telemetry"],
                "description": "Real-time vehicle health prediction & failure prevention system using OBD-II telemetry streams, Scikit-learn, TensorFlow LSTM models, FastAPI, and Next.js 14 dashboard with plain-language diagnostic alerts and DIY repair solutions.",
                "github_url": "https://github.com/Jyotiraditya1006/VehicleIQ"
            },
            {
                "title": "Customer Churn Detection System",
                "tech_stack": ["Python", "Machine Learning", "Scikit-Learn", "Pandas", "Classification", "Feature Importance"],
                "description": "End-to-end customer attrition prediction model identifying high-risk churn indicators to improve customer retention.",
                "github_url": "https://github.com/Jyotiraditya1006/Customer-Churn-Personal"
            },
            {
                "title": "Deep Learning LSTM Stock & Time-Series Predictor",
                "tech_stack": ["Python", "Deep Learning", "TensorFlow", "Keras", "LSTM", "Time-Series Forecasting"],
                "description": "Predictive time-series forecasting model utilizing Recurrent Neural Networks (LSTM) to capture temporal dependencies in financial market data.",
                "github_url": "https://github.com/Jyotiraditya1006/LSTM-Stock-Prediction-using-deep-learning"
            },
            {
                "title": "RecruitIQ - AI Recruitment & Candidate Evaluation Platform",
                "tech_stack": ["TypeScript", "Next.js", "AI Matching", "Vercel"],
                "description": "Full-stack AI recruitment platform matching candidates to relevant job profiles with live production deployment at recruit-iq-nu.vercel.app.",
                "github_url": "https://github.com/Jyotiraditya1006/RecruitIQ"
            },
            {
                "title": "Weather-HMM-Predictor - Hidden Markov Model Forecasting",
                "tech_stack": ["Python", "Hidden Markov Models (HMM)", "Statistical Modeling", "Sequence Prediction"],
                "description": "Stochastic sequence modeling system utilizing Hidden Markov Models to predict multi-state weather transitions.",
                "github_url": "https://github.com/Jyotiraditya1006/Weather-HMM-Predictor"
            }
        ]
        skills_seed = [
            "Python", "Machine Learning", "Deep Learning", "Artificial Intelligence",
            "TensorFlow", "PyTorch", "Scikit-Learn", "LSTM / RNNs",
            "Natural Language Processing (NLP)", "Computer Vision",
            "FastAPI", "Next.js 14", "TypeScript", "SQL",
            "Pandas", "NumPy", "Time-Series Forecasting",
            "Statistical Modeling (HMM)", "Data Engineering", "Git / GitHub"
        ]
        target_roles_seed = [
            "Data Science Intern", "Machine Learning Engineer Intern", "AI Research Intern",
            "Junior Data Scientist", "Junior ML Engineer", "Data Analyst Intern"
        ]
        geographies_seed = ["Pune", "Mumbai", "Bangalore", "Hyderabad", "Delhi NCR", "Remote / Global"]

        u_check = await db.execute("SELECT id FROM users ORDER BY id LIMIT 1")
        u_row = await u_check.fetchone()
        if u_row:
            await db.execute("""
                UPDATE users SET
                    name = 'Jyotiraditya Patil',
                    email = 'jyotiradityapatil106@gmail.com',
                    phone = '+91 7020676261',
                    location = 'Pune / Mumbai (Open to all locations & Remote)',
                    linkedin_url = 'https://www.linkedin.com/in/jyotiraditya-patil-73b394274/',
                    github_url = 'https://github.com/Jyotiraditya1006',
                    experience_level = 'Fresher / Student (B.Tech CSE - AI & ML)',
                    skills = ?,
                    projects = ?,
                    target_roles = ?,
                    geographies = ?
                WHERE id = ?
            """, (
                _json.dumps(skills_seed),
                _json.dumps(projects_seed),
                _json.dumps(target_roles_seed),
                _json.dumps(geographies_seed),
                u_row[0]
            ))
        else:
            await db.execute("""
                INSERT INTO users
                    (name, email, phone, location, linkedin_url, github_url, experience_level,
                     skills, projects, target_roles, geographies)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)
            """, (
                'Jyotiraditya Patil',
                'jyotiradityapatil106@gmail.com',
                '+91 7020676261',
                'Pune / Mumbai (Open to all locations & Remote)',
                'https://www.linkedin.com/in/jyotiraditya-patil-73b394274/',
                'https://github.com/Jyotiraditya1006',
                'Fresher / Student (B.Tech CSE - AI & ML)',
                _json.dumps(skills_seed),
                _json.dumps(projects_seed),
                _json.dumps(target_roles_seed),
                _json.dumps(geographies_seed),
            ))

        await db.commit()
        logger.info("Database initialization and user profile calibration complete.")
