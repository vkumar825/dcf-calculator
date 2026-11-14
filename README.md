# dcf-calculator

DCF Calculator is an automated Discounted Cash Flow valuation tool built with Python and Streamlit.

It fetches historical financial statement data from SEC EDGAR 10-K filings (2009+) using [edgartools](https://github.com/dgunning/edgartools), models WACC and unlevered free cash flows, and estimates a company's intrinsic value and implied share price.

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://vkumar-dcf.streamlit.app/)

## Prerequisites

- Python `>=3.13`
- [uv](https://docs.astral.sh/uv/) package manager

## Getting Started

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd dcf-calculator
   ```

2. **Install dependencies:**
   ```bash
   uv sync
   ```

3. **Configure SEC EDGAR identity:**
   SEC EDGAR requires a user-agent header for requests. Create a `.env` file in the project root:
   ```env
   EDGAR_IDENTITY="Your Name yourname@example.com"
   ```

4. **Launch the application:**
   ```bash
   uv run streamlit run src/dcf_calculator/app.py
   ```

## Running Tests

Run the unit test suite using `pytest` via `uv`:

```bash
uv run pytest
```

## Acknowledgements

Portions of this project were developed in conjunction with Google Gemini (via Antigravity CLI) for code assistance and debugging. All code, logic, and design were reviewed and supervised by me.
