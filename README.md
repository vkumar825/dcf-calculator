# dcf-calculator

DCF Calculator is an automated DCF valuation tool written in Python.

The program fetches financial statement data from SEC EDGAR 10-K filings and applies a Discounted Cash Flow (DCF) model to estimate a company's intrinsic value.

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

## Running Tests

Run the unit test suite using `pytest` via `uv`:

```bash
uv run pytest
```
