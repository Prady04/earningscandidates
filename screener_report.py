import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
import time
from pathlib import Path
from dotenv import load_dotenv
import os
import json
import re

class ScreenerReport:
    def __init__(self, email, password):
        """Initialize with Screener.in credentials"""
        self.email = email
        self.password = password
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        self.base_url = "https://www.screener.in"
        # Updated with the correct query from the previous step
        self.screen_url = "https://www.screener.in/screen/raw/?sort=qoq+profits&order=&source_id=186346&query=QoQ+Profits+%3E+30+AND%0D%0AQoQ+Sales+%3E+30+AND%0D%0AMarket+Capitalization+%3E+300+AND%0D%0AIs+not+SME+AND%0D%0AReturn+on+capital+employed+%3E+15+AND%0D%0ADebt+to+equity+%3C+1+AND%0D%0APledged+percentage+%3C+15&latest=on"
        self.bse_api_base = "https://api.bseindia.com/BseIndiaAPI/api/AnnSubCategoryGetData/w"
        
        # Headers for BSE API
        self.bse_headers = {
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
        
    def login(self):
        """Login to Screener.in"""
        print("Logging in to Screener.in...")
        
        try:
            # Get login page to extract CSRF token and set initial cookies
            login_page = self.session.get(f"{self.base_url}/login/")
            soup = BeautifulSoup(login_page.content, 'html.parser')
            
            # Get CSRF token from the form
            csrf_input = soup.find('input', {'name': 'csrfmiddlewaretoken'})
            if csrf_input and csrf_input.has_attr('value'):
                csrf_token = csrf_input['value']
            else:
                # Fallback: try to get from cookies
                csrf_token = self.session.cookies.get('csrftoken')
            
            if not csrf_token:
                print("✗ Could not find CSRF token")
                return False
            
            # Prepare login data
            login_data = {
                'username': self.email,
                'password': self.password,
                'csrfmiddlewaretoken': csrf_token
            }
            
            # Set headers for login POST request
            headers = {
                'Referer': f"{self.base_url}/login/",
                'Origin': self.base_url,
            }
            
            # Perform login
            response = self.session.post(
                f"{self.base_url}/login/",
                data=login_data,
                headers=headers,
                allow_redirects=True
            )
            
            # Check if login was successful
            if 'login' not in response.url or 'sessionid' in self.session.cookies:
                print("✓ Login successful!")
                return True
            else:
                print("✗ Login failed - still on login page")
                return False
                
        except Exception as e:
            print(f"✗ Login error: {e}")
            return False
    
    def get_bse_announcements(self, from_date=None, to_date=None):
        """
        Get financial results announcements from BSE API for a date range
        This is now STEP 1 - we get announcements FIRST
        """
        if to_date is None:
            to_date = datetime.now().strftime("%Y%m%d")
        
        if from_date is None:
            # Default: last 7 days
            from_date = (datetime.now() - timedelta(days=7)).strftime("%Y%m%d")
        
        print(f"\n=== STEP 1: Fetching BSE Earnings Announcements ===")
        print(f"Date range: {from_date} to {to_date}")
        
        announcements = []
        
        # Prepare API request
        params = {
            'pageno': 1,
            'strCat': 'Result',
            'strPrevDate': from_date,
            'strScrip': '',
            'strSearch': 'P',
            'strToDate': to_date,
            'strType': 'C',
            'subcategory': 'Financial Results'
        }
        
        try:
            print("  Making initial API request...")
            response = requests.get(self.bse_api_base, params=params, headers=self.bse_headers, timeout=10)
            print(f"  Response status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                
                if data and 'Table' in data and data['Table']:
                    table_data = data['Table']
                    print(f"  Found {len(table_data)} announcements on page 1")
                    
                    for item in table_data:
                        company_name = item.get('SLONGNAME', '')
                        company_code = item.get('SCRIP_CD', '')
                        announcement_date = item.get('NEWS_DT', '')
                        headline = item.get('HEADLINE', '')
                        
                        announcements.append({
                            'name': company_name,
                            'code': company_code,
                            'date': announcement_date,
                            'headline': headline
                        })
                    
                    # Check for pagination
                    if data and 'Table1' in data and data['Table1']:
                        pagination_info = data['Table1'][0] if data['Table1'] else {}
                        total_pages = int(pagination_info.get('ROWCNT', 1))
                        
                        # SAFETY: Limit to max 5 pages to prevent infinite loops
                        max_pages = min(total_pages, 5)
                        
                        if max_pages > 1:
                            print(f"  Fetching {max_pages-1} additional pages (total pages available: {total_pages})...")
                            for page in range(2, max_pages + 1):
                                print(f"    Fetching page {page}/{max_pages}...")
                                params['pageno'] = page
                                try:
                                    response = requests.get(self.bse_api_base, params=params, headers=self.bse_headers, timeout=10)
                                    if response.status_code == 200:
                                        page_data = response.json()
                                        if page_data and 'Table' in page_data and page_data['Table']:
                                            page_items = len(page_data['Table'])
                                            print(f"      Got {page_items} announcements")
                                            for item in page_data['Table']:
                                                announcements.append({
                                                    'name': item.get('SLONGNAME', ''),
                                                    'code': item.get('SCRIP_CD', ''),
                                                    'date': item.get('NEWS_DT', ''),
                                                    'headline': item.get('HEADLINE', '')
                                                })
                                    else:
                                        print(f"      Failed with status {response.status_code}")
                                except Exception as page_error:
                                    print(f"      Error on page {page}: {page_error}")
                                time.sleep(0.5)
                else:
                    print(f"  No announcements found in date range")
            else:
                print(f"  API request failed with status {response.status_code}")
            
        except requests.exceptions.Timeout:
            print(f"  ERROR: Request timed out after 10 seconds")
        except Exception as e:
            print(f"  Error fetching announcements: {e}")
            import traceback
            traceback.print_exc()
        
        print(f"✓ Total announcements fetched: {len(announcements)}")
        
        # Save for debugging
        try:
            with open('bse_announcements.json', 'w') as f:
                json.dump(announcements, f, indent=2)
            print("  Saved to bse_announcements.json")
        except Exception as e:
            print(f"  Warning: Could not save announcements file: {e}")
        
        return announcements
    
    def scrape_screen_data(self):
        """
        Scrape the screen results using authenticated session
        This is now STEP 2 - we get screening results to use as a lookup
        """
        print("\n=== STEP 2: Fetching Screener.in Results ===")
        
        try:
            print("  Making request to screener.in...")
            response = self.session.get(self.screen_url, headers={'Referer': self.base_url}, timeout=15)
            print(f"  Response received: {response.status_code}")
            
            if 'login' in response.url:
                print("✗ Session expired or not authenticated")
                return None
            
            print("  Parsing HTML...")
            soup = BeautifulSoup(response.content, 'html.parser')
            
            table = soup.find('table', {'class': 'data-table'})
            if not table:
                print("✗ Could not find results table")
                return None
            
            print("  Found data table, extracting headers...")
            # Extract headers
            headers = []
            header_row = table.find('tr')
            if header_row:
                for th in header_row.find_all('th'):
                    for span in th.find_all('span'):
                        span.decompose()
                    headers.append(th.text.strip())
            
            if not headers:
                print("✗ Could not extract table headers")
                return None
            
            print(f"  Headers: {headers}")
            
            # Extract data rows
            print("  Extracting data rows...")
            data = []
            rows = table.find_all('tr')
            
            for i, row in enumerate(rows):
                if row.find('th'):
                    continue
                
                row_data = {}
                cells = row.find_all('td')
                
                for j, cell in enumerate(cells):
                    if j < len(headers):
                        link = cell.find('a')
                        if link and j == 1:  # Company name column
                            href = link.get('href', '')
                            if href and not href.startswith('http'):
                                row_data['company_url'] = self.base_url + href
                            else:
                                row_data['company_url'] = href
                        row_data[headers[j]] = cell.text.strip()
                
                if row_data:
                    data.append(row_data)
                
                # Print progress every 10 rows
                if (i + 1) % 10 == 0:
                    print(f"    Processed {len(data)} companies so far...")
            
            print(f"✓ Scraped {len(data)} companies passing criteria")
            
            if len(data) == 0:
                print("  Warning: No data rows found")
                return None
            
            # Save to CSV for debugging
            df = pd.DataFrame(data)
            try:
                df.to_csv('screener_data.csv', index=False)
                print("  Saved to screener_data.csv")
            except Exception as e:
                print(f"  Warning: Could not save CSV: {e}")
                
            return df
            
        except requests.exceptions.Timeout:
            print("✗ ERROR: Request to screener.in timed out after 15 seconds")
            return None
        except Exception as e:
            print(f"✗ Error scraping data: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def normalize_company_name(self, name):
        """Normalize company name for better matching"""
        # Remove common suffixes and prefixes
        name = re.sub(r'\b(LTD|LIMITED|PVT|PRIVATE|THE|INDIA|INDUSTRIES|CORPORATION)\b', '', name, flags=re.IGNORECASE)
        # Remove special characters and extra spaces
        name = re.sub(r'[^\w\s]', '', name)
        name = re.sub(r'\s+', ' ', name).strip()
        return name.upper()
    
    def match_announcements_with_screen(self, announcements, screener_df):
        """
        STEP 3: Match BSE announcements with companies passing screener criteria
        This is the correct order: announcements first, then check if they pass criteria
        """
        print("\n=== STEP 3: Matching Announcements with Screener Criteria ===")
        
        if screener_df is None or len(screener_df) == 0:
            print("✗ No screener data available for matching")
            return []
        
        # Create lookup dictionary from screener results
        screener_lookup = {}
        print("\n📋 Building screener lookup table...")
        for idx, row in screener_df.iterrows():
            company_name = row.get('Name', '')
            normalized_name = self.normalize_company_name(company_name)
            screener_lookup[normalized_name] = row.to_dict()
            
            # Only print first 5 for brevity
            if idx < 5:
                print(f"  [{idx+1}] '{company_name}' → '{normalized_name}'")
        
        if len(screener_df) > 5:
            print(f"  ... and {len(screener_df) - 5} more companies")
        
        print(f"\n  Created lookup table with {len(screener_lookup)} companies")
        
        # Match announcements with screener results
        matched_stocks = []
        unmatched_announcements = []
        
        print(f"\n📋 Matching {len(announcements)} announcements...")
        print("  (Showing first 10 for brevity)")
        
        for i, announcement in enumerate(announcements):
            company_name = announcement['name']
            normalized_name = self.normalize_company_name(company_name)
            
            # Only show detailed output for first 10
            verbose = i < 10
            
            print(f"\n  [{i+1}] '{company_name}'")
            print(f"      Normalized: '{normalized_name}'")
            print(f"      Date: {announcement['date']}")
            
            # Try direct match
            match_found = False
            matched_data = None
            match_type = None
            
            if normalized_name in screener_lookup:
                match_found = True
                matched_data = screener_lookup[normalized_name]
                match_type = "DIRECT"
                if verbose:
                    print(f"      ✓ DIRECT MATCH!")
            else:
                # Try partial match
                for screener_name, screener_data in screener_lookup.items():
                    if normalized_name in screener_name or screener_name in normalized_name:
                        match_found = True
                        matched_data = screener_data
                        match_type = "PARTIAL"
                        if verbose:
                            print(f"      ✓ PARTIAL MATCH: '{screener_data.get('Name', '')}'")
                        break
                
                if not match_found:
                    if verbose:
                        print(f"      ✗ NO MATCH")
                    unmatched_announcements.append({
                        'announcement': company_name,
                        'normalized': normalized_name,
                        'date': announcement['date']
                    })
            
            if match_found and matched_data:
                normalized_name = self.normalize_company_name(company_name)
                # Combine announcement data with screener data
                combined = {
                    'Announcement Date': announcement['date'],
                    'Company Name': normalized_name,
                    'BSE Code': announcement['code'],
                    'Headline': announcement['headline'],
                    'Match Type': match_type,
                    **matched_data  # Add all screener metrics
                }

                matched_stocks.append(combined)
                if verbose:
                    print(f"      → Added to matches (total: {len(matched_stocks)})")
            
            # Progress indicator for remaining items
            if i == 10 and len(announcements) > 10:
                print(f"\n  ... processing remaining {len(announcements) - 10} announcements silently ...")
        
        print(f"\n✓ Matching complete:")
        print(f"  - {len(matched_stocks)} matches found")
        print(f"  - {len(unmatched_announcements)} unmatched")
        
        return matched_stocks
    
    def generate_html_report(self, matched_stocks, announcements,from_date=None, to_date=None):
        """Generate HTML report organized by announcement date"""
        report_date = datetime.now().strftime("%B %d, %Y")
        
        print("\n=== STEP 4: Generating HTML Report ===")
        print(f"📋 DEBUG: Received {len(matched_stocks)} matched stocks")
        
        # Convert to DataFrame for easier manipulation
        if len(matched_stocks) == 0:
            df = pd.DataFrame()
            date_groups = {}
        else:
            df = pd.DataFrame(matched_stocks)
            print(f"  DataFrame shape: {df.shape}")
            print(f"  Columns: {df.columns.tolist()}")
            
            # Sort by announcement date (most recent first)
            # BSE date format is 'dd-MMM-YYYY', e.g., '03-Jan-2024'
            #df['Announcement Date'] = pd.to_datetime(df['Announcement Date'], format='%d-%b-%Y', errors='coerce').dt.strftime('%Y-%m-%d')
            #df = df.sort_values('Announcement Date', ascending=False)
            print(f"\n  Sorted by date (most recent first)")
            
            # Group by announcement date
            #date_groups = df.groupby('Announcement Date')
            #print(f"\n  Found {len(date_groups)} unique dates:")
        
        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Earnings + Screener Report - {report_date}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f4f7f6; padding: 20px; }}
        .container {{ max-width: 1600px; margin: 0 auto; background: white; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); overflow: hidden; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; }}
        .header h1 {{ font-size: 2.2em; margin-bottom: 10px; }}
        .header .meta {{ opacity: 0.9; font-size: 1em; line-height: 1.6; }}
        .summary {{ padding: 30px; background: #f8f9fa; border-bottom: 3px solid #667eea; }}
        .summary-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; }}
        .summary-card {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .summary-card h3 {{ font-size: 0.9em; color: #6c757d; margin-bottom: 8px; }}
        .summary-card .value {{ font-size: 2em; color: #667eea; font-weight: bold; }}
        .criteria {{ background: #f8f9fa; padding: 20px; margin: 20px 30px; border-radius: 8px; border-left: 4px solid #667eea; }}
        .criteria h3 {{ margin-bottom: 12px; color: #495057; }}
        .criteria ul {{ list-style: none; padding-left: 0; }}
        .criteria li {{ padding: 5px 0; color: #6c757d; }}
        .criteria li:before {{ content: "✓ "; color: #28a745; font-weight: bold; margin-right: 8px; }}
        .date-section {{ padding: 30px; border-bottom: 1px solid #e0e0e0; }}
        .date-section:last-child {{ border-bottom: none; }}
        .date-header {{ display: flex; align-items: center; margin-bottom: 20px; padding-bottom: 10px; border-bottom: 2px solid #667eea; }}
        .date-header h2 {{ font-size: 1.6em; color: #2d3748; flex: 1; }}
        .badge {{ background: #667eea; color: white; padding: 6px 12px; border-radius: 20px; font-weight: 600; font-size: 0.9em; }}
        .table-wrapper {{ overflow-x: auto; border-radius: 8px; border: 1px solid #e0e0e0; }}
        table {{ width: 100%; border-collapse: collapse; background: white; font-size: 0.9em; }}
        thead {{ background: #f8f9fa; position: sticky; top: 0; }}
        th {{ padding: 12px; text-align: left; font-weight: 600; color: #495057; white-space: nowrap; border-bottom: 2px solid #dee2e6; }}
        td {{ padding: 12px; border-bottom: 1px solid #f0f0f0; }}
        tbody tr:hover {{ background: #f8f9fa; }}
        tbody tr:last-child td {{ border-bottom: none; }}
        .positive {{ color: #28a745; font-weight: 600; }}
        .negative {{ color: #dc3545; font-weight: 600; }}
        .company-name {{ color: #667eea; font-weight: 600; text-decoration: none; }}
        .company-name:hover {{ text-decoration: underline; }}
        .empty-state {{ text-align: center; padding: 60px 20px; color: #999; }}
        .empty-state h3 {{ font-size: 1.5em; margin-bottom: 10px; }}
        .headline {{ font-size: 0.85em; color: #6c757d; font-style: italic; max-width: 300px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Earnings + Screener Report</h1>
            <div class="meta">
                <div>Generated on: {report_date}</div>
                <div>Shows companies that: (1) Announced earnings, AND (2) Pass screening criteria</div>
            </div>
        </div>
        
        <div class="summary">
            <div class="summary-grid">
                <div class="summary-card">
                    <h3>Total Matches</h3>
                    <div class="value">{len(matched_stocks)}</div>
                </div>
            </div>
        </div>
        
        <div class="criteria">
            <h3>🎯 Screening Criteria Applied:</h3>
            <ul>
                <li>QoQ Profits > 30%</li>
                <li>QoQ Sales > 30%</li>
                <li>Market Capitalization > 300 Cr</li>
                <li>Is not SME</li>
                <li>Return on capital employed > 15%</li>
                <li>Debt to Equity < 1</li>
                <li>Pledged percentage < 15%</li>
            </ul>
        </div>
"""
        
        if len(matched_stocks) == 0:
            html += """
        <div class="empty-state">
            <h3>No Matches Found</h3>
            <p>No companies announced earnings in the date range that also pass the screening criteria.</p>
        </div>
"""
        else:
            # Add a section for each date
           
            html += f"""
        <div class="date-section">
          
            {self._generate_table(matched_stocks)}
        </div>
       
""" 
        html_content = '<div class="date-section">\n'
        for announcement in announcements:
            html_content += f"{announcement['name']}, {announcement['date']}<br>\n"
        html_content += '</div>'
        html+=html_content 
        html += """
            </div>
</body>
</html>
"""
        
        print(f"\n  ✓ HTML generation complete")
        print(f"  Total HTML length: {len(html)} characters")
        
        return html
    
    def _generate_table(self, df):
        listofstocks = []
        """Generate HTML table from dataframe"""
        print(f"\n      _generate_table called with {len(df)} rows")
        
        if len(df) == 0:
            return '<div class="empty-state">No data available.</div>'
        
        # Select columns to display (customize as needed)
        display_cols = ['Name', 'BSE Code', 'Headline', 'Match Type']
        
        # Add screener columns if available
        screener_cols = [col for col in df.columns if col not in ['Announcement Date', 'Name', 'BSE Code', 'Headline', 'company_url', 'Name', 'Match Type']]
        display_cols.extend(screener_cols)
        
        # Filter to only existing columns
        display_cols = [col for col in display_cols if col in df.columns]
        
        print(f"      Display columns: {display_cols}")
        print(f"      DataFrame columns: {df.columns.tolist()}")
        
        html = '<div class="table-wrapper"><table><thead><tr>'
        for col in display_cols:
            html += f'<th>{col}</th>'
        html += '</tr></thead><tbody>'
        
        row_count = 0
        for idx, row in df.iterrows():
            html += '<tr>'
            for col in display_cols:
                val = row.get(col, '')
                
                if col == 'Name':
                    company_url =row.get('company_url','#')
                    import re


                
                    # Extract stock name from URL
                    # URL format: https://www.screener.in/company/BEL/consolidated/
                    stock_name = val  # Default to original value
                    
                    if company_url != '#':
                        # Method 1: Using regex to extract the stock symbol
                        match = re.search(r'/company/([^/]+)/', company_url)
                        if match:
                            stock_name = match.group(1)
    
                    html += f'<td><a href="{company_url}" class="company-name" target="_blank">{stock_name}</a></td>'
                    listofstocks.append(stock_name)
                   
                elif col == 'Headline':
                    html += f'<td class="headline">{val}</td>'
                elif col == 'Match Type':
                    html += f'<td><span style="font-size: 0.8em; background: #e7f3ff; padding: 4px 8px; border-radius: 4px;">{val}</span></td>'
                else:
                    try:
                        num_val = float(str(val).replace(',', '').replace('%', '').replace('Cr', '').replace('₹', ''))
                        css_class = 'positive' if num_val > 0 else 'negative' if num_val < 0 else ''
                        html += f'<td class="{css_class}">{val}</td>'
                    except:
                        html += f'<td>{val}</td>'
            html += '</tr>'
            row_count += 1
        
        html += '</tbody></table></div>'
        result = ', '.join(listofstocks)
        print(result)
        print(f"      Generated table with {row_count} rows")
        return html
    
    def generate_report(self, from_date=None, to_date=None, output_file='earnings_screener_report.html'):
        """
        Main method to generate the report with correct flow:
        1. Get BSE announcements first
        2. Get screener results
        3. Match and filter
        """
        print("\n" + "="*60)
        print("EARNINGS + SCREENER REPORT GENERATOR")
        print("="*60)
        
        # STEP 1: Get BSE announcements (PRIMARY DATA SOURCE)
        announcements = self.get_bse_announcements(from_date, to_date)
        
        if not announcements:
            print("\n✗ No announcements found. Cannot generate report.")
            return False
        for announcement in announcements:
            print(announcement['name'],announcement['date'])
        # STEP 2: Login and get screener data (FILTER/LOOKUP)
        if not self.login():
            print("\n✗ Failed to login. Cannot generate report.")
            return False
        
        screener_df = self.scrape_screen_data()
        
        if screener_df is None or len(screener_df) == 0:
            print("\n✗ No screener data available. Cannot generate report.")
            return False
        
        # Save for debugging
        screener_df.to_csv('screener_data.csv', index=False)
        screener_df.to_html('result.html')
        
        # STEP 3: Match announcements with screener results
        matched_stocks = screener_df #self.match_announcements_with_screen(announcements, screener_df)
        
        # STEP 4: Generate HTML report
        print("\n=== STEP 4: Generating HTML Report ===")
        # CORRECTED: Passing matched_stocks instead of screener_df
        html = self.generate_html_report(matched_stocks, announcements, from_date, to_date)
        
        output_path = Path(output_file)
        output_path.write_text(html, encoding='utf-8')
        
        print(f"\n✓ Report generated: {output_path.absolute()}")
        print("\n" + "="*60)
        print("SUMMARY")
        print("="*60)
        print(f"Total announcements fetched: {len(announcements)}")
        print(f"Companies passing screener: {len(screener_df)}")
        print(f"Final matches (earnings + criteria): {len(matched_stocks)}")
        print("="*60)
        
        return True


# Usage
if __name__ == "__main__":
    load_dotenv()
    
    # Configuration
    EMAIL = os.getenv('SCR_USER')
    PASSWORD = os.getenv('SCR_PASS')
    
    if not EMAIL or not PASSWORD:
        print("✗ Please set SCR_USER and SCR_PASS environment variables")
        exit(1)
    
    # Date range for announcements (last 7 days by default)
    to_date = datetime.now().strftime("%Y%m%d")
    from_date = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
    
    print(f"Searching for earnings announcements from {from_date} to {to_date}")
    
    # Generate report with correct flow
    reporter = ScreenerReport(EMAIL, PASSWORD)
    reporter.generate_report(from_date=from_date, to_date=to_date)