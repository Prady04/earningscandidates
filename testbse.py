import requests
import json
from datetime import datetime

def test_bse_api_for_17th():
    """Test the BSE API specifically for the 17th"""
    print("Testing BSE API for October 17th...")
    
    # API endpoint
    api_url = "https://api.bseindia.com/BseIndiaAPI/api/AnnSubCategoryGetData/w"

            'https://api.bseindia.com/BseIndiaAPI/api/AnnSubCategoryGetData/w'
    # Headers for BSE API
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Referer': 'https://www.bseindia.com/',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-site',
    }
    
    # Set date to October 17th, 2024 (format: YYYYMMDD)
    date_str = "20251017"
    
    # Prepare API request
    params = {
        'pageno': 1,
        'strCat': 'Result',
        'strPrevDate': date_str,
        'strScrip': '',
        'strSearch': 'P',
        'strToDate': date_str,
        'strType': 'C',
        'subcategory': 'Financial Results'
    }
    
    print(f"Testing with date: {date_str}")
    print(f"Request URL: {api_url}")
    
    try:
        response = requests.get(api_url, params=params, headers=headers)
        print(f"\nResponse status: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"\nResponse keys: {data.keys() if data else 'None'}")
                
                if data and 'Data' in data and data['Data']:
                    print(f"Found {len(data['Data'])} announcements")
                    
                    # Print first few announcements
                    for i, item in enumerate(data['Data'][:5]):
                        print(f"\n  {i+1}. Company: {item.get('FULLNAME', 'N/A')}")
                        print(f"     Code: {item.get('SCRIP_CD', 'N/A')}")
                        print(f"     Date: {item.get('NEWS_DT', 'N/A')}")
                        print(f"     Headline: {item.get('NEWSSUB', 'N/A')}")
                    
                    # Save the full response to a file for inspection
                    with open('bse_api_response_17th.json', 'w') as f:
                        json.dump(data, f, indent=2)
                    print(f"\nFull response saved to bse_api_response_17th.json")
                    
                    return data['Data']
                else:
                    print("No announcements found in the response")
                    print(f"Full response: {data}")
                    return None
            except json.JSONDecodeError as e:
                print(f"Failed to decode JSON response: {e}")
                print(f"Response content: {response.text[:1000]}...")
                return None
        else:
            print(f"API request failed with status {response.status_code}")
            print(f"Response content: {response.text[:1000]}...")
            return None
            
    except Exception as e:
        print(f"Error testing BSE API: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    announcements = test_bse_api_for_17th()