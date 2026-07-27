import sys
sys.path.insert(0, ".")
from services.cftc_service import get_latest_cftc_report

print("Fetching CFTC data via Socrata API...")
try:
    r = get_latest_cftc_report(force_refresh=True)
    print(f"report_date: {r['report_date']}")
    print(f"TFF items: {len(r['tff_items'])}")
    print(f"Disagg items: {len(r['disagg_items'])}")
    print(f"Findings: {len(r['analysis']['findings'])}")
    print(f"Source: {r['source']}")
    print("SUCCESS!")
except Exception as e:
    print(f"FAIL: {e}")