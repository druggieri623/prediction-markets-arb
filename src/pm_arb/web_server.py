"""Flask web server for prediction market arbitrage detection UI"""

from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import os
from datetime import datetime

from .sql_storage import init_db, MatchedMarketPairORM
from .arbitrage_detector import ArbitrageDetector

app = Flask(__name__, template_folder="templates", static_folder="static")
CORS(app)

# Initialize database
DB_PATH = os.getenv("PM_ARB_DB", "pm_arb_demo.db")
engine, SessionLocal = init_db(f"sqlite:///{DB_PATH}")


@app.route("/")
def index():
    """Main dashboard page"""
    return render_template("dashboard.html")


@app.route("/api/pairs", methods=["GET"])
def get_pairs():
    """Get all matched market pairs"""
    session = SessionLocal()
    try:
        pairs = session.query(MatchedMarketPairORM).all()
        result = []
        for pair in pairs:
            result.append(
                {
                    "id": pair.id,
                    "source_a": pair.source_a,
                    "market_id_a": pair.market_id_a,
                    "source_b": pair.source_b,
                    "market_id_b": pair.market_id_b,
                    "similarity": (
                        round(pair.similarity, 4)
                        if pair.similarity is not None
                        else None
                    ),
                    "classifier_probability": (
                        round(pair.classifier_probability, 4)
                        if pair.classifier_probability is not None
                        else None
                    ),
                    "name_similarity": (
                        round(pair.name_similarity, 4)
                        if pair.name_similarity is not None
                        else None
                    ),
                    "category_similarity": (
                        round(pair.category_similarity, 4)
                        if pair.category_similarity is not None
                        else None
                    ),
                    "temporal_proximity": (
                        round(pair.temporal_proximity, 4)
                        if pair.temporal_proximity is not None
                        else None
                    ),
                    "is_manual_confirmed": pair.is_manual_confirmed,
                    "confirmed_by": pair.confirmed_by,
                    "notes": pair.notes,
                    "created_at": (
                        pair.created_at.isoformat() if pair.created_at else None
                    ),
                }
            )
        return jsonify({"success": True, "pairs": result, "count": len(result)})
    finally:
        session.close()


@app.route("/api/pairs/<int:pair_id>/confirm", methods=["POST"])
def confirm_pair(pair_id):
    """Confirm a matched pair"""
    session = SessionLocal()
    try:
        pair = session.query(MatchedMarketPairORM).filter_by(id=pair_id).first()
        if not pair:
            return jsonify({"success": False, "error": "Pair not found"}), 404

        data = request.get_json()
        pair.is_manual_confirmed = True
        pair.confirmed_by = data.get("confirmed_by", "user")
        session.commit()

        return jsonify({"success": True, "message": "Pair confirmed"})
    except Exception as e:
        session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        session.close()


@app.route("/api/pairs/<int:pair_id>", methods=["DELETE"])
def delete_pair(pair_id):
    """Delete a matched pair"""
    session = SessionLocal()
    try:
        pair = session.query(MatchedMarketPairORM).filter_by(id=pair_id).first()
        if not pair:
            return jsonify({"success": False, "error": "Pair not found"}), 404

        session.delete(pair)
        session.commit()

        return jsonify({"success": True, "message": "Pair deleted"})
    except Exception as e:
        session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        session.close()


@app.route("/api/arbitrage-opportunities", methods=["GET"])
def get_arbitrage_opportunities():
    """Get arbitrage opportunities from matched pairs"""
    session = SessionLocal()
    try:
        pairs = session.query(MatchedMarketPairORM).all()
        detector = ArbitrageDetector()

        # Detect opportunities
        opportunities_list = detector.detect_opportunities(session, pairs)

        opportunities = []
        for opp in opportunities_list:
            # Find the corresponding pair for confidence info
            pair = next((p for p in pairs if p.id == opp.pair_id), None)
            confidence = 0.0
            if pair and pair.classifier_probability is not None:
                confidence = pair.classifier_probability

            opportunities.append(
                {
                    "pair_id": opp.pair_id,
                    "source_a": opp.market_a.source if opp.market_a else "Unknown",
                    "market_id_a": (
                        opp.market_a.market_id if opp.market_a else "Unknown"
                    ),
                    "source_b": opp.market_b.source if opp.market_b else "Unknown",
                    "market_id_b": (
                        opp.market_b.market_id if opp.market_b else "Unknown"
                    ),
                    "potential_profit": (
                        round(opp.min_profit, 2) if opp.min_profit else 0
                    ),
                    "roi": round(opp.roi * 100, 2) if opp.roi else 0,
                    "strategy": opp.summary or "Arbitrage opportunity detected",
                    "confidence": round(confidence, 4),
                }
            )

        return jsonify(
            {
                "success": True,
                "opportunities": opportunities,
                "count": len(opportunities),
            }
        )
    except Exception as e:
        return jsonify(
            {"success": False, "error": str(e), "opportunities": [], "count": 0}
        )
    finally:
        session.close()


@app.route("/api/stats", methods=["GET"])
def get_stats():
    """Get statistics about matched pairs"""
    session = SessionLocal()
    try:
        pairs = session.query(MatchedMarketPairORM).all()
        confirmed = sum(1 for p in pairs if p.is_manual_confirmed)

        # Calculate averages, filtering out None values
        similarity_values = [p.similarity for p in pairs if p.similarity is not None]
        classifier_values = [
            p.classifier_probability
            for p in pairs
            if p.classifier_probability is not None
        ]

        stats = {
            "total_pairs": len(pairs),
            "confirmed_pairs": confirmed,
            "unconfirmed_pairs": len(pairs) - confirmed,
            "avg_similarity": (
                round(sum(similarity_values) / len(similarity_values), 4)
                if similarity_values
                else 0
            ),
            "avg_classifier_probability": (
                round(sum(classifier_values) / len(classifier_values), 4)
                if classifier_values
                else 0
            ),
            "timestamp": datetime.now().isoformat(),
        }

        return jsonify({"success": True, "stats": stats})
    finally:
        session.close()


@app.route("/api/health", methods=["GET"])
def health_check():
    """Health check endpoint"""
    return jsonify(
        {"success": True, "status": "running", "timestamp": datetime.now().isoformat()}
    )


def run_server(host="127.0.0.1", port=5000, debug=False):
    """Start the Flask development server"""
    print(f"\n🚀 Starting Prediction Market Arbitrage Web Server")
    print(f"📊 Dashboard: http://{host}:{port}")
    print(f"🗄️  Database: {DB_PATH}")
    print(f"🔌 API Base: http://{host}:{port}/api")
    print(f"\nAvailable endpoints:")
    print(f"  GET  /api/pairs                    - List all matched pairs")
    print(f"  GET  /api/arbitrage-opportunities - List arbitrage opportunities")
    print(f"  GET  /api/stats                    - Get statistics")
    print(f"  POST /api/pairs/<id>/confirm       - Confirm a pair")
    print(f"  DEL  /api/pairs/<id>               - Delete a pair")
    print(f"  GET  /api/health                   - Health check\n")

    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    run_server(debug=True)
