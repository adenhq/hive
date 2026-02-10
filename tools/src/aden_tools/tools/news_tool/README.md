# News Tool

Search news articles and headlines with optional sentiment analysis.

## Description

Provides structured news results from multiple providers with automatic fallback:
- **NewsData.io** (primary)
- **Finlight.me** (optional; required for sentiment)

## Tools

### `news_search`
Search news articles with filters.

Arguments:
- `query` (str, required)
- `from_date` (str, optional, YYYY-MM-DD)
- `to_date` (str, optional, YYYY-MM-DD)
- `language` (str, optional, default `en`)
- `limit` (int, optional, default `10`)
- `sources` (str, optional)
- `category` (str, optional)
- `country` (str, optional)

### `news_headlines`
Get top headlines by category and country.

Arguments:
- `category` (str, required)
- `country` (str, required)
- `limit` (int, optional, default `10`)

### `news_by_company`
Get news mentioning a company.

Arguments:
- `company_name` (str, required)
- `days_back` (int, optional, default `7`)
- `limit` (int, optional, default `10`)
- `language` (str, optional, default `en`)

### `news_sentiment`
Get news with sentiment analysis (Finlight provider only).

Arguments:
- `query` (str, required)
- `from_date` (str, optional, YYYY-MM-DD)
- `to_date` (str, optional, YYYY-MM-DD)

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `NEWSDATA_API_KEY` | Yes | API key for [NewsData.io](https://newsdata.io/) |
| `FINLIGHT_API_KEY` | Optional | API key for [Finlight.me](https://finlight.me/) |

## Example Usage

```python
news_search(query="Series B funding", from_date="2026-02-01", to_date="2026-02-10")
news_headlines(category="business", country="us")
news_by_company(company_name="Acme Corp", days_back=7)
news_sentiment(query="Acme Corp")
```



