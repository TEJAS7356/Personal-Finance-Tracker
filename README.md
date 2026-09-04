# Personal Finance Tracker

A multi-page Streamlit app for tracking personal income and expenses, with budgets, monthly analytics, savings goals, and an AI financial advisor — backed by a local SQLite database.

## Features

- **Transaction Management** — add, search, filter by date, delete, and export transactions to CSV.
- **Financial Dashboard** — income/expense summary, category breakdown charts, and smart spending insights with a plain-language recommendation.
- **Budget Tracking** — set a monthly spending limit per category and see live progress bars with on-track / near-limit / over-budget badges.
- **Monthly Analytics** — income vs. expenses trend chart over time, month-over-month percentage comparison, and a monthly breakdown table.
- **Savings Goals** — create savings goals with a target amount and date, and track progress with a visual bar.
- **AI Financial Advisor** — chat with Google's Gemini (free tier) about your own summarized financial data (spending by category, budgets, goals) for personalized, grounded suggestions.
- **Expense Prediction** — explainable next-month and category-level forecasts using the user's monthly expense history and linear regression when enough history exists.
- **Expense Anomaly Detection** — robust per-category median/MAD checks that identify unusually high expenses without mixing accounts.
- **AI Expense Categorization** — fast local merchant/description keyword suggestions that never remove the existing manual category choice or require an API call.
- **Financial Health Score** — deterministic 0–100 score based on savings rate, expense ratio, budget adherence, goal progress, and month consistency.
- **What-If Simulator** — interactive surplus and savings-goal projections for extra monthly saving or reducing a selected expense category.

## Multi-user accounts

The app now supports independent accounts with Register, Log In, and Log out controls. Each account receives a unique user ID, and transactions, budgets, savings goals, dashboard calculations, analytics, and AI Advisor summaries are filtered to that authenticated user. Ownership checks are also applied to every update and delete operation.

Users must choose a username and a password of at least eight characters. Newly registered accounts always start with empty financial data. If an existing single-user `finance_tracker.db` is present, the first startup migrates its old rows under an inaccessible legacy owner instead of exposing them to a new account.

### Gmail password recovery setup

Registration requires an email address so that the Forgot Password flow can deliver a one-time verification code. Password recovery uses Gmail SMTP with a Gmail **App Password**, not a normal Gmail password. Add these values to Streamlit Secrets in `.streamlit/secrets.toml` or provide them as environment variables:

```toml
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = "587"
SMTP_USERNAME = "your-gmail-address@gmail.com"
SMTP_APP_PASSWORD = "your-16-character-gmail-app-password"
SMTP_FROM_EMAIL = "your-gmail-address@gmail.com"
```

`SMTP_HOST` and `SMTP_PORT` default to Gmail's `smtp.gmail.com` and `587`; `SMTP_USERNAME`, `SMTP_APP_PASSWORD`, and optionally `SMTP_FROM_EMAIL` are the important account settings. Enable two-step verification on the Gmail account before creating the App Password. Never commit `.streamlit/secrets.toml` or expose these values in the UI.

## Project structure

```
personal-financial-tracker/
├── app.py                          # Home page: quick add + at-a-glance summary
├── database.py                     # SQLite setup and CRUD for transactions, budgets, goals
├── utils.py                        # Shared CSS, category lists, formatting helpers, color palette
├── finance_ml.py                   # User-scoped prediction, anomaly, categorization, scoring, and simulation logic
├── .streamlit/
│   └── secrets.toml                # Local-only file holding GEMINI_API_KEY (not committed)
├── pages/
│   ├── 1_Transaction_Management.py
│   ├── 2_Financial_Dashboard.py
│   ├── 3_Budget_Tracking.py
│   ├── 4_Monthly_Analytics.py
│   ├── 5_Savings_Goals.py
│   └── 6_AI_Financial_Advisor.py
├── requirements.txt
└── README.md
```

Streamlit automatically builds the sidebar navigation from the `pages/` folder — no extra routing code needed.

## Requirements

- Python 3.9+
- streamlit
- pandas
- plotly
- google-genai (only needed for the AI Financial Advisor page)
- scikit-learn (used by the expense prediction model)

## Setup

1. Clone or download this project, keeping the folder structure above intact.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Set your Gemini API key for the AI Financial Advisor page. Create a `.streamlit/secrets.toml` file in the project root:
   ```toml
   GEMINI_API_KEY = "your-key-here"
   ```
   Get a free key (no credit card required) at https://aistudio.google.com/app/apikey. `.streamlit/secrets.toml` holds a personal API key, so keep it out of version control (add it to `.gitignore`). Without a key, every other page still works — only the advisor page is disabled.
4. Run the app:
   ```bash
   streamlit run app.py
   ```
5. Open the URL Streamlit prints (usually `http://localhost:8501`).

A file named `finance_tracker.db` will be created automatically the first time you run the app. It's not included in the repo since it holds your personal data.

## Usage

1. **Home** — quickly add a transaction or check your total income/expenses/balance.
2. **Transaction Management** — the full transaction log with date/search filters, per-row delete, and CSV export.
3. **Financial Dashboard** — charts and insights based on all your data.
4. **Budget Tracking** — set a ₹ limit per expense category and see how this month's spending compares.
5. **Monthly Analytics** — spot trends across months and see how this month compares to the last.
6. **Savings Goals** — set a target (e.g. "Emergency Fund — ₹50,000 by Dec 2026") and update your progress as you save.
7. **AI Financial Advisor** — ask things like "Where can I cut back?" and get a suggestion grounded in your actual numbers. Click "Data being sent to the advisor" to see exactly what's shared.

## Notes

- All amounts are in ₹ (Indian Rupees). To use a different currency, update `format_currency()` in `utils.py`.
- Data is stored locally in SQLite. Authentication state is held in each browser's Streamlit session; use a shared, persistent database location when deploying the app for multiple users.
- The AI Financial Advisor sends a **summary** (totals by category, budgets, goals), not your raw transaction list, to the Gemini API. Google's free tier may use prompts to improve their models — see [Gemini API terms](https://ai.google.dev/gemini-api/terms) for details.
- `utils.py` defines two color-related values: `FINANCE_COLORS` (a dict of semantic colors, e.g. `FINANCE_COLORS["income"]`) and `FINANCE_COLOR_SEQUENCE` (the same colors as a flat list). Plotly's `color_discrete_sequence` argument requires a list, so chart code should use `FINANCE_COLOR_SEQUENCE`, not `FINANCE_COLORS`, when setting chart palettes.

## Troubleshooting

- **`ValueError` from `px.pie` / `px.bar` about `color_discrete_sequence`** — this argument needs a list of color strings, not a dict. Make sure chart code imports and uses `FINANCE_COLOR_SEQUENCE` from `utils.py` rather than `FINANCE_COLORS`.
- **AI Financial Advisor page says it can't reach the advisor** — check that `.streamlit/secrets.toml` exists in the project root (not inside `pages/`) and contains a valid `GEMINI_API_KEY`.

## Possible future additions

- Recurring transactions (e.g. rent, salary auto-added monthly)
- Custom, user-defined categories
- Multi-currency support
- Bank statement import (CSV/PDF parsing)
