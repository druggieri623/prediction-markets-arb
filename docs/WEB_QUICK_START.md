# Web Interface Quick Start

Get the web dashboard running in 30 seconds.

## Prerequisites

- Python 3.8+
- Virtual environment activated
- Dependencies installed (`pip install -r requirements.txt`)

## Start the Server

```bash
python scripts/run_web_server.py
```

You should see:

```
🚀 Starting Prediction Market Arbitrage Web Server
📊 Dashboard: http://127.0.0.1:5000
🗄️  Database: pm_arb_demo.db
🔌 API Base: http://127.0.0.1:5000/api

Available endpoints:
  GET  /api/pairs                    - List all matched pairs
  GET  /api/arbitrage-opportunities - List arbitrage opportunities
  GET  /api/stats                    - Get statistics
  POST /api/pairs/<id>/confirm       - Confirm a pair
  DEL  /api/pairs/<id>               - Delete a pair
  GET  /api/health                   - Health check
```

## Open Dashboard

Click the link or paste in your browser:

```
http://127.0.0.1:5000
```

## What You'll See

### 📊 Matched Pairs Tab

- All matched market pairs from your database
- Similarity and classifier scores
- Ability to confirm or delete pairs
- Search and filter options

### 💰 Arbitrage Opportunities Tab

- Potential risk-free profit opportunities
- Expected ROI for each opportunity
- Strategy details

### 📈 Analytics Tab

- Total pairs count
- Confirmation statistics
- Average similarity scores
- Last update timestamp

## Common Tasks

### View a Specific Pair

1. Click the "👁️ View" button on any pair card
2. See detailed metrics and notes in the modal

### Confirm a Match

1. Click "✓ Confirm" on an unconfirmed pair
2. Pair will be marked as manually verified

### Search for Pairs

1. Use the search box in the Matched Pairs tab
2. Type platform name or market ID
3. Results filter in real-time

### Check Statistics

1. Go to Analytics tab
2. View aggregated statistics about all pairs
3. See average similarity and classifier scores

## Custom Configuration

### Different Port

```bash
python scripts/run_web_server.py --port 8080
```

Then visit: http://127.0.0.1:8080

### Different Database

```bash
python scripts/run_web_server.py --db /path/to/custom.db
```

### Debug Mode (Auto-reload)

```bash
python scripts/run_web_server.py --debug
```

### Network Access

```bash
python scripts/run_web_server.py --host 0.0.0.0 --port 5000
```

Then visit: http://{your-computer-ip}:5000

## API Access

All data is available via REST API:

```bash
# List all pairs
curl http://127.0.0.1:5000/api/pairs

# Get opportunities
curl http://127.0.0.1:5000/api/arbitrage-opportunities

# Get stats
curl http://127.0.0.1:5000/api/stats
```

See [WEB_INTERFACE.md](WEB_INTERFACE.md) for complete API documentation.

## Keyboard Shortcuts

- **Tab key** - Switch between dashboard tabs
- **Enter key** - Confirm dialogs
- **Escape key** - Close modals

## Troubleshooting

### Port Already in Use

```bash
python scripts/run_web_server.py --port 5001
```

### Database Not Found

Ensure the database file exists or run:

```bash
python scripts/match_markets.py --db pm_arb_demo.db
```

### Check Server Status

```bash
curl http://127.0.0.1:5000/api/health
```

## Next Steps

1. **Load Data**: Run market matching to populate pairs

   ```bash
   python scripts/match_markets.py --db pm_arb_demo.db
   ```

2. **Train Classifier**: Improve match accuracy

   ```bash
   python scripts/train_classifier.py --db pm_arb_demo.db
   ```

3. **Find Arbitrage**: Identify profit opportunities

   ```bash
   python scripts/find_arbitrage.py --db pm_arb_demo.db
   ```

4. **Monitor Dashboard**: Watch opportunities in real-time

## More Information

- Full documentation: [WEB_INTERFACE.md](WEB_INTERFACE.md)
- API reference: [WEB_INTERFACE.md#rest-api](WEB_INTERFACE.md#rest-api)
- Examples: [WEB_INTERFACE.md#usage-examples](WEB_INTERFACE.md#usage-examples)
