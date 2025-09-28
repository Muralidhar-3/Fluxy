# test_nse_api_clean.py
import requests

NSE_API_URL = "https://www.nseindia.com/api/corporate-announcements?index=equities"

def test_fetch_nse():
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.nseindia.com/",
    })

    response = session.get(NSE_API_URL, timeout=10)
    print("Status Code:", response.status_code)

    if response.status_code == 200:
        data = response.json()

        if isinstance(data, list):
            print(f"Total Announcements Fetched: {len(data)}")

            for row in data[:5]:  # first 5
                company = row.get("symbol")
                name = row.get("sm_name")
                subject = row.get("desc")
                date = row.get("an_dt") or row.get("sort_date")
                link = row.get("attchmntFile")
                details = row.get("attchmntText")

                print(f"""
📢 {company} - {name}
📝 {subject}
📅 {date}
🔗 {link}
ℹ️ {details}
""")

if __name__ == "__main__":
    test_fetch_nse()
