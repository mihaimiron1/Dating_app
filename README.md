# Dating App

A Flask web app that recommends dating matches using a content-based recommender (location + shared interests) with a small collaborative boost from other users' likes.

Users register, build a profile, and swipe through recommended profiles one at a time. A like from both sides creates a match, and matches appear on the Friends page. The UI is in Romanian.

## Features

- **Registration and login.** Passwords are stored as salted scrypt hashes (`werkzeug.security`), never in plain text.
- **Profile creation.** Users upload a photo and enter age, height, interests, location and match preferences (gender, age range).
- **Recommendations.** Each user gets a ranked feed of profiles they haven't seen yet, filtered by their preferences.
- **Like / dislike.** Each swipe is saved to an interaction matrix, so profiles a user has already rated don't come back.
- **Matches.** Mutual likes are listed on the Friends page.
- **Profile page.** Users can view and edit their own details.

## How recommendations work

The logic lives in [`backend/main.py`](backend/main.py):

1. **Filter.** Keep only candidates whose gender and age fit the current user's preferences, and drop anyone the user has already liked or disliked.
2. **Build feature vectors.**
   - *Location.* The city is geocoded to latitude/longitude with the OpenCage API, then turned into a 3D unit vector (x, y, z) on a sphere, so nearby cities end up with similar vectors.
   - *Interests.* Interests are one-hot encoded with `MultiLabelBinarizer`.
3. **Score.** The features are standardized (`StandardScaler`) and compared with cosine similarity.
4. **Collaborative boost.** Profiles that a similar user has liked get a small score bonus (+0.07).
5. **Record the swipe.** A like is stored as `1` and a dislike as `0.5` in `interact.csv`. When two users have both stored `1` for each other, they are a match.

## Tech stack

- **Backend:** Python, Flask
- **Data and ML:** pandas, NumPy, scikit-learn
- **Geocoding:** OpenCage Geocoding API
- **Frontend:** Jinja2 templates, HTML, CSS, vanilla JavaScript
- **Storage:** CSV and JSON files (no database)

## Project structure

```
├── app.py                  # Flask routes (auth, profile, recommendations, swipes)
├── backend/main.py         # Data loading, similarity and recommendation logic
├── APA_PR/
│   ├── dating_data.csv     # Raw user profiles
│   ├── procesed_data.csv   # Processed features (one-hot interests, location vectors)
│   └── interact.csv        # User × user interaction matrix (likes/dislikes)
├── login_users.json        # Accounts (email, name, password hash)
├── templates/              # Jinja2 pages
├── static/                 # CSS and images
└── test.ipynb              # Exploration notebook used while building the data pipeline
```

## Getting started

### Prerequisites

- Python 3.11+
- An [OpenCage](https://opencagedata.com/) API key. The free tier is enough, and you only need it to **register new users**; logging in and browsing with the demo accounts works without it.

### Installation

```sh
git clone https://github.com/mihaimiron1/Dating_app
cd Dating_app
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Configuration

Both settings are read from environment variables:

| Variable           | Required                 | Purpose                                                        |
|--------------------|--------------------------|----------------------------------------------------------------|
| `SECRET_KEY`       | Recommended              | Flask session key. If unset, a random one is generated at startup, so sessions reset on every restart. |
| `OPENCAGE_API_KEY` | For registering new users | Geocodes the city entered on the profile form.                 |

```sh
export SECRET_KEY="change-me"
export OPENCAGE_API_KEY="your-key"
# PowerShell: $env:SECRET_KEY="change-me"; $env:OPENCAGE_API_KEY="your-key"
```

### Run

```sh
python app.py
```

Then open http://127.0.0.1:5000.

### Demo account

The repo ships with 70 synthetic users. To log in as one of them:

- **Email:** `john.doe25@gmail.com`
- **Password:** `A1b2C3d4`

## Limitations and next steps

- Data is stored in CSV/JSON files, which is fine for a demo but not safe for concurrent writes. The next step would be SQLite or PostgreSQL with an ORM.
- Similarity is recomputed on every request. It could be cached, or updated incrementally when a profile changes.
- There are no automated tests yet.
