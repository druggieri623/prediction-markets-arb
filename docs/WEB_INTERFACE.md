# Web Interface Guide

## Overview

The Prediction Market Arbitrage Detector includes a modern web-based dashboard for browsing, analyzing, and managing matched market pairs across prediction platforms.

## Getting Started

### Starting the Server

```bash
# Basic usage (localhost:5000)
python scripts/run_web_server.py

# Custom host and port
python scripts/run_web_server.py --host 0.0.0.0 --port 8080

# With debug mode (auto-reload on code changes)
python scripts/run_web_server.py --debug

# With custom database
python scripts/run_web_server.py --db /path/to/custom.db
```

### Accessing the Dashboard

Open your web browser and navigate to:

- **Local machine**: http://127.0.0.1:5000
- **Network access**: http://{your-machine-ip}:5000

## Dashboard Features

### 1. Matched Pairs Tab 📊

Browse all matched market pairs in your database.

**Features:**

- View similarity metrics for each pair
- Search by source platform or market ID
- Filter to show only confirmed pairs
- Confirm or delete pairs with one click
- View detailed pair information in modal

**Metrics Displayed:**

- **Similarity**: Overall match confidence (0-100%)
- **Classifier**: ML model confidence (0-100%)
- **Name Similarity**: Text similarity of market names
- **Category Similarity**: Category alignment score
- **Temporal Proximity**: How recent the data is

**Actions:**

- 👁️ **View** - See detailed pair information
- ✓ **Confirm** - Mark as manually verified match
- 🗑️ **Delete** - Remove pair from database

### 2. Arbitrage Opportunities Tab 💰

Identify potential risk-free profit opportunities across matched pairs.

**Displayed Information:**

- **Market Pair**: Which platforms are involved
- **Potential Profit**: Dollar amount of risk-free profit
- **ROI**: Return on investment percentage
- **Confidence**: How confident the match is
- **Strategy**: Specific arbitrage strategy explanation

### 3. Analytics Tab 📈

View aggregated statistics about your matched pairs.

**Statistics Tracked:**

- Total matched pairs in database
- Number of manually confirmed pairs
- Average overall similarity score
- Average classifier probability
- Last update timestamp

## REST API

The web server exposes a complete REST API for programmatic access.

### Base URL

```
http://127.0.0.1:5000/api
```

### Endpoints

#### Get All Matched Pairs

```bash
GET /api/pairs
```

**Response:**

```json
{
  "success": true,
  "pairs": [
    {
      "id": 1,
      "source_a": "kalshi",
      "market_id_a": "market_123",
      "source_b": "polymarket",
      "market_id_b": "market_456",
      "similarity": 0.95,
      "classifier_probability": 0.92,
      "name_similarity": 0.9,
      "category_similarity": 0.95,
      "temporal_proximity": 1.0,
      "is_manual_confirmed": false,
      "confirmed_by": null,
      "notes": "High-confidence match",
      "created_at": "2025-12-05T10:30:00"
    }
  ],
  "count": 1
}
```

#### Get Arbitrage Opportunities

```bash
GET /api/arbitrage-opportunities
```

**Response:**

```json
{
  "success": true,
  "opportunities": [
    {
      "pair_id": 1,
      "source_a": "kalshi",
      "market_id_a": "market_123",
      "source_b": "polymarket",
      "market_id_b": "market_456",
      "potential_profit": 0.15,
      "roi": 0.176,
      "strategy": "Buy YES from A, NO from B",
      "confidence": 0.92
    }
  ],
  "count": 1
}
```

#### Get Statistics

```bash
GET /api/stats
```

**Response:**

```json
{
  "success": true,
  "stats": {
    "total_pairs": 10,
    "confirmed_pairs": 7,
    "unconfirmed_pairs": 3,
    "avg_similarity": 0.856,
    "avg_classifier_probability": 0.823,
    "timestamp": "2025-12-05T10:30:00"
  }
}
```

#### Confirm a Pair

```bash
POST /api/pairs/{id}/confirm
Content-Type: application/json

{
  "confirmed_by": "user@example.com"
}
```

**Response:**

```json
{
  "success": true,
  "message": "Pair confirmed"
}
```

#### Delete a Pair

```bash
DELETE /api/pairs/{id}
```

**Response:**

```json
{
  "success": true,
  "message": "Pair deleted"
}
```

#### Health Check

```bash
GET /api/health
```

**Response:**

```json
{
  "success": true,
  "status": "running",
  "timestamp": "2025-12-05T10:30:00"
}
```

## Usage Examples

### Python Example

```python
import requests

api_base = "http://127.0.0.1:5000/api"

# Get all pairs
response = requests.get(f"{api_base}/pairs")
pairs = response.json()['pairs']
print(f"Found {len(pairs)} matched pairs")

# Confirm a pair
pair_id = pairs[0]['id']
requests.post(f"{api_base}/pairs/{pair_id}/confirm", json={"confirmed_by": "script"})

# Get arbitrage opportunities
opps = requests.get(f"{api_base}/arbitrage-opportunities").json()['opportunities']
for opp in opps:
    print(f"Potential profit: ${opp['potential_profit']}")
```

### JavaScript Example

```javascript
const API_BASE = "http://127.0.0.1:5000/api";

// Get all pairs
const pairs = await fetch(`${API_BASE}/pairs`)
  .then((r) => r.json())
  .then((d) => d.pairs);

// Confirm a pair
await fetch(`${API_BASE}/pairs/1/confirm`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ confirmed_by: "user" }),
});

// Get stats
const stats = await fetch(`${API_BASE}/stats`)
  .then((r) => r.json())
  .then((d) => d.stats);
```

### cURL Examples

```bash
# Get all pairs
curl http://127.0.0.1:5000/api/pairs

# Get arbitrage opportunities
curl http://127.0.0.1:5000/api/arbitrage-opportunities

# Get statistics
curl http://127.0.0.1:5000/api/stats

# Confirm a pair
curl -X POST http://127.0.0.1:5000/api/pairs/1/confirm \
  -H "Content-Type: application/json" \
  -d '{"confirmed_by": "user"}'

# Delete a pair
curl -X DELETE http://127.0.0.1:5000/api/pairs/1
```

## Advanced Configuration

### Environment Variables

```bash
# Set custom database path
export PM_ARB_DB=/path/to/custom.db

# Start server with custom DB
python scripts/run_web_server.py
```

### CORS Configuration

The API has CORS enabled by default. To restrict CORS:

Edit `src/pm_arb/web_server.py`:

```python
# Replace:
CORS(app)

# With:
CORS(app, origins=["http://localhost:3000"])
```

### Production Deployment

For production, use a WSGI server like Gunicorn:

```bash
pip install gunicorn

# Run with Gunicorn
gunicorn --bind 0.0.0.0:5000 --workers 4 src.pm_arb.web_server:app
```

## Troubleshooting

### Server Won't Start

- Check if port 5000 is already in use
- Use `--port` flag to specify a different port
- Ensure database file exists or is accessible

### Data Not Loading

- Verify the database file path is correct
- Check that the database has data in the `matched_market_pairs` table
- Ensure database file permissions are correct

### CORS Issues

- Check that API_BASE in app.js matches your server URL
- Verify CORS is enabled in web_server.py

### API Errors

- Check browser console for error messages
- Use `/api/health` endpoint to verify server is running
- Review Flask server logs for detailed error messages

## Performance Tips

1. **Database Optimization**

   - Create indexes on frequently queried columns
   - Archive old pairs to separate database

2. **Large Datasets**

   - Implement pagination in API endpoints
   - Cache statistics that don't change frequently
   - Use query filtering for initial loads

3. **Network Performance**
   - Run server on same network as clients
   - Consider caching layer (Redis) for statistics
   - Enable gzip compression in production

## Contributing

To add new features to the web interface:

1. **Backend**: Modify `src/pm_arb/web_server.py`

   - Add new API endpoints
   - Implement business logic

2. **Frontend**: Modify `src/pm_arb/static/`

   - `app.js` - JavaScript logic
   - `style.css` - Styling
   - `dashboard.html` - HTML structure

3. **Templates**: Modify `src/pm_arb/templates/`
   - Update dashboard.html for new UI elements

## License

This web interface is part of the prediction-markets-arb project.
