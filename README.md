# unlockED

unlockED is a premium SaaS, AI-powered College Counseling Platform driven by the **unlockED Agent Engine** under the hood. It is designed to assist counsellors in managing portfolios, tracking student academic risks, identifying scholarship opportunities, and executing complex counseling commands.

---

## 🛠️ Technology Stack

### Backend & AI Engine
- **Framework**: [Flask](https://flask.palletsprojects.com/) (Python)
- **AI Core**: [Groq Cloud API](https://console.groq.com/) for Agentic counselor co-pilot commands and text ingestion.
- **Machine Learning & Data Processing**: 
  - [scikit-learn](https://scikit-learn.org/) & [joblib](https://joblib.readthedocs.io/) for pre-trained risk prediction models.
  - [pandas](https://pandas.pydata.org/) & [numpy](https://numpy.org/) for cohort analytics and data manipulation.
- **Utilities**: `rich` (CLI formatting), `python-dotenv` (environment variable configuration).

### Frontend
- **Interface**: Vanilla HTML5, CSS3 (Custom design system built with custom variables, smooth transitions, and premium SaaS UI/UX).
- **Text Editor**: [Quill.js](https://quilljs.com/) for rich email drafting.
- **Typography**: [Google Fonts (Inter)](https://fonts.google.com/specimen/Inter) for clean, readable layouts.

---

## 🚀 Key Features

1. **Counselor Co-Pilot (AI Command Center)**
   - Execute natural language commands (e.g., *"draft warning emails"*, *"recommend pathways for STU_001"*).
   - Generates quick insights, analysis, or draft templates dynamically.
2. **AI Priority Queue**
   - Ranks students by predictive risk score so counselors know who needs attention today.
3. **Student Profile & Database**
   - Manage all student academic records, GPA trends, activity logs, and timelines.
   - Auto-classify portfolio achievements/activities into Tier 1, 2, or 3 based on descriptive criteria.
4. **Opportunity Radar & Scholarship Search**
   - Scan for college opportunities and filter scholarships tailored to student profiles.
5. **Ingestion Agent**
   - Bulk import student data via Excel or CSV formats directly into the dashboard.

---

## 📦 Project Structure

```bash
├── static/                  # Frontend files (HTML, CSS, JS assets)
│   ├── style.css            # Custom premium CSS design system
│   ├── index.html           # Main dashboard
│   ├── app.js               # Dashboard interactive logic
│   └── student.html         # Detailed student view
├── prism_agent/             # Core PRISM Agent logic
│   ├── agent.py             # Main Orchestration Agent
│   ├── reasoner.py          # Deduction & risk analysis engine
│   ├── planner.py           # Goal-oriented planning system
│   ├── knowledge_graph.py   # Student & college relationship database
│   └── opportunity_radar.py # Scholarship matching engine
├── models/                  # Pre-trained ML classifiers
├── server.py                # Flask Web Server
├── requirements.txt         # Python dependencies
└── README.md                # Documentation
```

---

## ⚙️ Setup and Installation

### 1. Prerequisites
- Python 3.10 or higher.
- A Groq API Key

### 2. Installation
Clone the repository and navigate to the project directory:

```bash
git clone <repository-url>
cd agent
```

Create a virtual environment and activate it:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows, use `.venv\Scripts\activate`
```

Install the dependencies:
```bash
pip install -r requirements.txt
```

### 3. Configuration
Create a `.env` file in the root directory and add your Groq API key:

### 4. Running the Application
Start the Flask development server:
```bash
python server.py
```
Open your browser and navigate to `http://127.0.0.1:5000` to access the unlockED dashboard.
