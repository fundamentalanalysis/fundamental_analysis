#Part1
import time
import os
import re
import requests
import pandas as pd
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


# ======================================================
#                 FLATTEN NESTED TABLE
# ======================================================
def flatten_nested_table(table):
    """
    Extract **all rows including nested/subrows** EXACTLY as visible on Screener,
    preserving indentation structure by text only.
    """
    rows = []
    trs = table.find_all("tr")

    for tr in trs:
        cells = tr.find_all(["td", "th"])
        if not cells:
            continue

        # Extract the row label exactly as seen (Borrowings -, Short Term Borrowings, etc.)
        label = cells[0].get_text(" ", strip=True)

        # Extract all remaining columns
        values = [c.get_text(" ", strip=True) for c in cells[1:]]

        # Build row
        rows.append([label] + values)

    return pd.DataFrame(rows)


def login_to_screener(driver):
    """Login to Screener.in using credentials from .env file"""
    print("\n" + "="*70)
    print("LOGGING IN TO SCREENER.IN")
    print("="*70 + "\n")
    
    username = os.getenv('SCRUSER')
    password = os.getenv('SCRPASSWORD')
    
    if not username or not password:
        print("⚠️  No credentials found in .env")
        return False
    
    try:
        driver.get("https://www.screener.in/login/")
        time.sleep(2)
        
        username_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "id_username"))
        )
        username_field.clear()
        username_field.send_keys(username)
        
        password_field = driver.find_element(By.ID, "id_password")
        password_field.clear()
        password_field.send_keys(password)
        
        login_button = driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]')
        login_button.click()
        
        time.sleep(3)
        
        if "login" not in driver.current_url.lower():
            print("✓ Login successful!\n")
            return True
        else:
            print("✗ Login failed\n")
            return False
            
    except Exception as e:
        print(f"✗ Login error: {e}\n")
        return False


def clean_filename(text):
    text = re.sub(r'[<>:"/\\|?*]', '', text)
    text = re.sub(r'\s+', '_', text.strip())
    return text[:150]


def download_file(url, save_path):
    """Download files safely, detecting PDF/HTML."""
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}

        try:
            head_resp = requests.head(url, timeout=10, allow_redirects=True, headers=headers)
            content_type = head_resp.headers.get('Content-Type', '').lower()
            is_pdf = 'pdf' in content_type
        except Exception:
            content_type = ''
            is_pdf = False

        if save_path.suffix.lower() not in ['.pdf', '.html']:
            if is_pdf:
                save_path = save_path.with_suffix('.pdf')
            else:
                save_path = save_path.with_suffix('.html')

        response = requests.get(url, timeout=30, stream=True, headers=headers)
        response.raise_for_status()
        
        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        return True
    except Exception as e:
        print(f"    Download error: {e}")
        return False



#Part2
def check_paywall(soup):
    """Detect paywall text."""
    page_text = soup.get_text().lower()

    paywall_phrases = [
        'login to view',
        'sign in to access',
        'subscribe to view',
        'premium members only',
        'access denied',
        'only available to'
    ]

    for phrase in paywall_phrases:
        if phrase in page_text:
            return True, phrase

    return False, None


# ======================================================
#         EXPAND ALL ACCORDIONS / NESTED ROWS
# ======================================================
def expand_all_accordions(driver):
    print("\n==============================")
    print(" EXPANDING NESTED TABLE ROWS ")
    print("==============================\n")

    time.sleep(1)

    # Scroll to trigger lazy loading
    try:
        scroll_height = driver.execute_script("return document.body.scrollHeight") or 0
    except Exception:
        scroll_height = 2000

    print("→ Scrolling page to load lazy content...")
    step = max(400, scroll_height // 12)
    y = 0
    while y <= scroll_height:
        driver.execute_script("window.scrollTo(0, arguments[0]);", y)
        time.sleep(0.3)
        y += step

    time.sleep(1)

    # -------------------------------------------------
    # Expand P&L Nested Rows
    # -------------------------------------------------
    print("→ Expanding P&L nested rows…")

    js_pl = r"""
    let clicks = 0;
    const tables = Array.from(document.querySelectorAll('table'));
    const plTables = tables.filter(tbl => {
        const r = tbl.querySelector('tr');
        if (!r) return false;
        const t = (r.cells[0]?.textContent || '').toLowerCase();
        return t.includes('sales') || t.includes('revenue');
    });

    plTables.forEach(tbl => {
        Array.from(tbl.querySelectorAll('tr')).forEach(row => {
            const firstCell = row.cells[0];
            if (!firstCell) return;
            if ((firstCell.textContent || '').trim().endsWith('+')) {
                try { firstCell.click(); } catch(e){}
                const btn = row.querySelector('button, span, i');
                if (btn) { try { btn.click(); } catch(e){} }
                clicks++;
            }
        });
    });

    return clicks;
    """

    try:
        pl_clicks = driver.execute_script(js_pl)
        print(f"   → P&L nested rows clicked: {pl_clicks}")
    except Exception as e:
        print("   ✗ P&L expand error:", e)

    time.sleep(1)

    # -------------------------------------------------
    # Expand Quarterly Nested Rows
    # -------------------------------------------------
    print("→ Expanding Quarterly nested rows…")

    js_quarterly = r"""
    let clicks = 0;
    const parents = document.querySelectorAll('tr.parent');
    parents.forEach(row => {
        const btn = row.querySelector('button, span, i');
        if (btn) { try { btn.click(); clicks++; } catch(e){} }
    });
    return clicks;
    """

    try:
        q_clicks = driver.execute_script(js_quarterly)
        print(f"   → Quarterly nested rows clicked: {q_clicks}")
    except Exception as e:
        print("   ✗ Quarterly expand error:", e)

    time.sleep(1)

    # -------------------------------------------------
    # Expand ALL generic + buttons
    # -------------------------------------------------
    print("→ Expanding all generic '+' expanders…")

    selectors = [
        "button.button-plain",
        "span.icon-plus",
        "i.icon-plus",
        "[class*='plus']",
        "[class*='expand']",
        ".toggle",
        "button[aria-expanded='false']",
        "a[onclick*='expand']",
    ]

    total_clicked = 0

    for selector in selectors:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
        except:
            continue

        for elem in elements:
            try:
                if not elem.is_displayed():
                    continue

                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", elem)
                time.sleep(0.2)

                try:
                    elem.click()
                except:
                    try:
                        driver.execute_script("arguments[0].click();", elem)
                    except:
                        continue

                total_clicked += 1
            except:
                continue

    print(f"   → Generic expand clicks: {total_clicked}")

    # -------------------------------------------------
    # Force ALL rows to be visible via CSS override
    # -------------------------------------------------
    print("→ Forcing all rows visible…")

    js_force = r"""
    document.querySelectorAll('tr').forEach(r => {
        r.style.display = 'table-row';
        r.style.visibility = 'visible';
    });
    """

    try:
        driver.execute_script(js_force)
    except:
        pass

    print("\n✓ All tables expanded\n")


# ======================================================
#                SECTION HEADING EXTRACTOR
# ======================================================
def extract_section_heading(element):
    for _ in range(10):
        prev = element.find_previous(['h2', 'h3', 'h4', 'h5'])
        if prev:
            text = prev.get_text(strip=True)
            if text and len(text) < 50:
                return text
        element = element.parent
        if not element:
            break
    return None


# ======================================================
#              CLICK SHOW MORE BUTTONS
# ======================================================
def click_show_more_buttons(driver):
    print("  Clicking 'show more' buttons…")
    clicks = 0

    for _ in range(5):
        try:
            buttons = driver.find_elements(
                By.XPATH,
                "//*[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), 'show more')]"
            )

            if not buttons:
                break

            for b in buttons:
                if b.is_displayed():
                    try:
                        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", b)
                        time.sleep(0.4)
                        b.click()
                        clicks += 1
                        time.sleep(0.8)
                    except:
                        pass
        except:
            break

    print(f"  → Show more clicked: {clicks}")
    return clicks


# ======================================================
#         DOCUMENTS / ANNOUNCEMENTS EXTRACTOR
# ======================================================
def extract_documents_links(soup, base_url):
    docs = []
    heading = None

    for tag in soup.find_all(['h2', 'h3']):
        if 'documents' in tag.get_text(strip=True).lower():
            heading = tag
            break

    if not heading:
        print("  [Docs] No Documents section found")
        return docs

    container = heading
    for _ in range(10):
        container = container.parent
        if not container or container.name == "body":
            break
        links = container.find_all('a', href=True)
        if len(links) > len(docs):
            best = container

    container = best if 'best' in locals() else None
    if not container:
        print("  [Docs] Could not detect documents container")
        return docs

    for a in container.find_all('a', href=True):
        text = a.get_text(strip=True)
        if text and text.lower() not in ['all', 'show more', 'show all']:
            docs.append({
                'category': 'documents',
                'text': text,
                'href': a['href'],
                'url': urljoin(base_url, a['href'])
            })

    print(f"  [Docs] Links collected: {len(docs)}")
    return docs


# ======================================================
#        TEXT CONTENT (ABOUT, PROS, CONS)
# ======================================================
def extract_text_content(soup, company_folder: Path):
    sections = []

    about_texts = []
    for label in soup.find_all(string=lambda t: isinstance(t, str) and 'about' in t.lower()):
        parent = label.parent
        sib = parent.find_next_sibling()
        count = 0

        while sib and count < 10:
            count += 1
            if sib.name == 'p':
                txt = sib.get_text(" ", strip=True)
                if len(txt) > 25:
                    about_texts.append(txt)
            sib = sib.find_next_sibling()

        if about_texts:
            break

    if about_texts:
        sections.append(("About", "\n\n".join(about_texts)))

    def get_list(keyword):
        items = []
        for p in soup.find_all('p'):
            if keyword in p.get_text(strip=True).lower():
                ul = p.find_next_sibling('ul')
                if ul:
                    for li in ul.find_all('li'):
                        items.append(li.get_text(" ", strip=True))
                break
        return items

    pros = get_list('pros')
    if pros:
        sections.append(("Pros", "\n".join(f"- {p}" for p in pros)))

    cons = get_list('cons')
    if cons:
        sections.append(("Cons", "\n".join(f"- {c}" for c in cons)))

    if not sections:
        return

    markdown = ["# Text Content", ""]
    for title, content in sections:
        markdown.append(f"## {title}")
        markdown.append("")
        markdown.append(content)
        markdown.append("")

    (company_folder / "text_content.md").write_text("\n".join(markdown), encoding="utf-8")
    print("✓ Saved text content")


#Part3
# ======================================================
#                KEY METRICS EXTRACTOR
# ======================================================
def extract_key_metrics(soup, company_folder: Path):
    """Extract key metrics (Market Cap, P/E, ROE, etc.) into CSV."""
    metrics = []

    for ul in soup.find_all('ul'):
        lis = ul.find_all('li')
        if not lis:
            continue

        labels = [li.get_text(" ", strip=True).lower() for li in lis]

        # Detect the Key Metrics block
        if any('market cap' in lbl for lbl in labels) and any('current price' in lbl for lbl in labels):
            for li in lis:
                spans = [s.get_text(" ", strip=True) for s in li.find_all('span')]

                if len(spans) >= 2:
                    name, value = spans[0], spans[1]

                else:
                    txt = li.get_text(" ", strip=True)
                    if ':' in txt:
                        name, value = txt.split(':', 1)
                        name, value = name.strip(), value.strip()
                    else:
                        continue

                metrics.append({'metric': name, 'value': value})
            break

    if metrics:
        df = pd.DataFrame(metrics).drop_duplicates()
        df.to_csv(company_folder / "key_metrics.csv", index=False)
        print("✓ Saved key metrics")


# ======================================================
#         QUARTERLY RAW PDF LINK EXTRACTOR
# ======================================================
def extract_quarterly_result_pdfs(soup, base_url):
    """Extract quarterly result PDF links from Raw PDF row."""
    results = []

    for table in soup.find_all('table'):
        rows = table.find_all('tr')

        for row in rows:
            cells = row.find_all(['td', 'th'])
            if not cells:
                continue

            if 'raw pdf' in cells[0].get_text(strip=True).lower():

                # Identify quarter headers
                headers = table.find_all('tr')[0].find_all(['th', 'td'])

                for idx, cell in enumerate(cells[1:], start=1):
                    a = cell.find('a', href=True)
                    if not a:
                        continue

                    quarter = headers[idx].get_text(strip=True) if idx < len(headers) else "Quarter"

                    results.append({
                        'category': 'quarterly_results',
                        'text': f"Quarterly Result PDF - {quarter}",
                        'url': urljoin(base_url, a['href']),
                        'quarter': quarter,
                        'force_pdf': True
                    })

    print(f"  [Quarterly PDFs] Found: {len(results)}")
    return results


# ======================================================
#                      MAIN SCRAPER
# ======================================================
def scrape_screener_company(symbol):
    """Scrape company data from Screener.in (Enhanced Version A)."""

    url = f"https://www.screener.in/company/{symbol}/consolidated/"
    company_folder = Path(symbol)
    company_folder.mkdir(exist_ok=True)

    folders = {
        'tables': company_folder / 'financial_tables',
        'annual': company_folder / 'annual_reports',
        'concalls': company_folder / 'concalls',
        'announcements': company_folder / 'announcements',
        'credit_ratings': company_folder / 'credit_ratings',
        'quarterly_results': company_folder / 'quarterly_result_pdfs',
        'other': company_folder / 'other_documents'
    }

    for folder in folders.values():
        folder.mkdir(exist_ok=True)

    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    
    driver = webdriver.Chrome(options=chrome_options)

    try:
        # --------------------------------------
        # LOGIN TO SCREENER
        # --------------------------------------
        login_success = login_to_screener(driver)

        print("\n" + "="*70)
        print(f"SCRAPING: {symbol}")
        print("="*70 + "\n")

        driver.get(url)

        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "table"))
        )
        print("✓ Page loaded\n")

        # Initial scroll to trigger content load
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(1)

        # --------------------------------------
        # EXPAND ALL TABLES
        # --------------------------------------
        expand_all_accordions(driver)
        click_show_more_buttons(driver)

        # Scroll entire page to ensure all elements load
        print("Scrolling entire page to capture all content…")
        height = driver.execute_script("return document.body.scrollHeight")
        y = 0
        step = height // 10 if height else 500

        while y < height:
            driver.execute_script(f"window.scrollTo(0, {y});")
            time.sleep(1)
            y += step

        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(3)

        # Scroll to Documents section
        print("Scrolling to Documents section…")
        driver.execute_script("""
            const docs = [...document.querySelectorAll('h2')]
                .find(h => h.textContent.includes('Documents'));
            if (docs) docs.scrollIntoView({behavior: 'smooth', block:'center'});
        """)
        time.sleep(2)

        # Extract concall notes (modal pop-up)
        extract_concall_notes(driver, company_folder)

        # Freeze the final rendered page
        soup = BeautifulSoup(driver.page_source, 'html.parser')

        # --------------------------------------
        # PAYWALL CHECK
        # --------------------------------------
        paywall_detected = False
        is_pw, msg = check_paywall(soup)

        if is_pw:
            print(f"\n⚠️ PAYWALL DETECTED: {msg}")
            print("⚠️ Proceeding with visible content only.\n")
            paywall_detected = True

        # Company name
        cname = soup.find('h1')
        company_name = cname.text.strip() if cname else symbol
        print(f"Company: {company_name}\n")

        # Save full HTML snapshot
        (company_folder / "full_page.html").write_text(driver.page_source, encoding="utf-8")
        print("✓ Saved: full_page.html\n")

        # Extract textual and key metrics
        extract_text_content(soup, company_folder)
        extract_key_metrics(soup, company_folder)

        # --------------------------------------
        #        EXTRACT ALL FINANCIAL TABLES
        # --------------------------------------
        print("Extracting financial tables…")
        print("-" * 70)

        all_tables = soup.find_all("table")
        tables_saved = {}


#part4

# ==========================================================================
#                         *** PART 4: FINANCIAL TABLE EXTRACTION ***
#              (Nested rows preserved + Row/Column Flip + FY fix + cleanup)
# ==========================================================================
        for idx, table in enumerate(all_tables):
            try:
                # -------------------------------------------------
                # 1️⃣ GET SECTION HEADING
                # -------------------------------------------------
                section = extract_section_heading(table)

                # -------------------------------------------------
                # 2️⃣ EXTRACT NESTED TABLE (FULLY EXPANDED HTML)
                # -------------------------------------------------
                df = flatten_nested_table(table)

                if df.shape[0] < 1 or df.shape[1] < 2:
                    continue

                # -------------------------------------------------
                # 3️⃣ FIX EMPTY COLUMN HEADERS
                # -------------------------------------------------
                df.columns = [
                    col if str(col).strip() else f"Column_{i}"
                    for i, col in enumerate(df.columns)
                ]

                # -------------------------------------------------
                # 4️⃣ FLIP TABLE (ROWS ↔ COLUMNS)
                # -------------------------------------------------
                try:
                    first_col = df.columns[0]
                    df = df.set_index(first_col).T
                    df.reset_index(inplace=True)
                    df.rename(columns={"index": first_col}, inplace=True)
                    print("    → Table flipped (rows <-> columns)")
                except Exception as e:
                    print(f"    → Flip failed: {e}")

                # -------------------------------------------------
                # 4.1️⃣ REMOVE INDEX-LIKE FIRST COLUMN
                # -------------------------------------------------
                first_column = df.columns[0]
                if df[first_column].astype(str).str.match(r'^\d+$').all():
                    df.drop(columns=[first_column], inplace=True)

                # Rename FY column
                fy_col = df.columns[0]
                df.rename(columns={fy_col: "Financial_Year"}, inplace=True)

                # -------------------------------------------------
                # 4.2️⃣ FIX FINANCIAL YEAR FORMAT (Mar 2014 → Mar_2014)
                # -------------------------------------------------
                def convert_fy(val):
                    val = str(val).strip()

                    # Pattern: "Mar 2014", "Sep 2025"
                    match = re.match(r"([A-Za-z]{3})\s+(\d{4})$", val)
                    if match:
                        prefix = match.group(1)
                        year = match.group(2)
                        return f"{prefix}_{year}"

                    return val

                df["Financial_Year"] = df["Financial_Year"].apply(convert_fy)

                # -------------------------------------------------
                # 4.3️⃣ CLEAN COLUMN NAMES
                # -------------------------------------------------
                def clean_col(col):
                    col = str(col).strip()

                    replacements = {
                        "Equity Cap": "Equity_Capital",
                        "Borrowings -": "Borrowings",
                        "Other Liabilities +": "Other_Liabilities",
                        "Other Liabilities": "Other_Liabilities",
                        "Fixed Assets +": "Fixed_Assets",
                        "Other Assets +": "Other_Assets",
                        "Short term Borrowings": "Short_term_Borrowings",
                        "Long term Borrowings": "Long_term_Borrowings",
                    }

                    for old, new in replacements.items():
                        if old.lower() in col.lower():
                            return new

                    col = col.replace(" -", "")
                    col = col.replace("-", "_")
                    col = col.replace(" ", "_")
                    col = col.replace("/", "_")
                    col = re.sub(r"[^A-Za-z0-9_]", "", col)
                    col = re.sub(r"_+", "_", col)
                    return col.strip("_")

                df.columns = [clean_col(c) for c in df.columns]

                # -------------------------------------------------
                # 4.4️⃣ REMOVE COMMAS FROM NUMERIC VALUES (Positive + Negative)
                # -------------------------------------------------
                def remove_commas(val):
                    if isinstance(val, str):
                        # Handles: 123,456 | -123,456 | 123 | -123
                        if re.match(r"^-?[0-9,]+$", val):
                            return int(val.replace(",", ""))
                    return val

                df = df.applymap(remove_commas)

                # -------------------------------------------------
                # 4.4.1️⃣ FORCE CONVERT ALL NUMERIC-LIKE VALUES TO INTEGER
                # -------------------------------------------------
                for col in df.columns:
                    if col not in ["Financial_Year", "Company_Ticker"]:
                        df[col] = pd.to_numeric(df[col], errors="ignore")

                # -------------------------------------------------
                # 4.5️⃣ REPLACE NULL VALUES WITH ZERO (Commented as per requirement)
                # -------------------------------------------------
                # NOTE: Replacing NULL values with 0 for consistency
                # df = df.fillna(0)

                # -------------------------------------------------
                # 5️⃣ DETECT TABLE NAME
                # -------------------------------------------------
                if section:
                    base_name = clean_filename(section)
                else:
                    first_col_text = " ".join(df[df.columns[1]].astype(str)).lower()

                    if "sales" in first_col_text or "revenue" in first_col_text:
                        base_name = "Profit_Loss"
                    elif "equity" in first_col_text or "assets" in first_col_text:
                        base_name = "Balance_Sheet"
                    elif "cash" in first_col_text:
                        base_name = "Cash_Flow"
                    elif "debtor" in first_col_text or "roe" in first_col_text:
                        base_name = "Ratios"
                    else:
                        base_name = f"Table_{idx}"

                name = base_name
                counter = 1
                while name in tables_saved:
                    name = f"{base_name}_{counter}"
                    counter += 1

                # -------------------------------------------------
                # 5.1️⃣ ADD COMPANY TICKER COLUMN
                # -------------------------------------------------
                df["Company_Ticker"] = symbol

                # -------------------------------------------------
                # 6️⃣ SAVE FINAL CLEANED CSV
                # -------------------------------------------------
                filepath = folders["tables"] / f"{name}.csv"
                df.to_csv(filepath, index=False)
                tables_saved[name] = df.shape

                print(f"  ✓ Saved {name:40} ({df.shape[0]} rows × {df.shape[1]} cols)")

            except Exception as e:
                print(f"  ✗ Error extracting table {idx}: {e}")

        print("\n" + "="*70)
        print(f"Tables extracted: {len(tables_saved)}")
        print("="*70 + "\n")




#Part5
# ======================================================
#                 DOWNLOAD DOCUMENTS
# ======================================================
        print("Downloading documents…")
        print("-" * 70)

        download_stats = {
            'annual': 0,
            'concalls': 0,
            'announcements': 0,
            'credit_ratings': 0,
            'quarterly_results': 0,
            'other': 0
        }

        # Extract links from Documents section
        doc_links = extract_documents_links(soup, url)
        print(f"  Found {len(doc_links)} document links")

        # Extract concalls
        concall_links = extract_concalls_comprehensive(driver, soup, url)
        print(f"  Found {len(concall_links)} concall links")

        # Extract quarterly PDFs
        quarterly_pdfs = extract_quarterly_result_pdfs(soup, url)
        print(f"  Found {len(quarterly_pdfs)} quarterly result PDFs")

        # Combine all
        all_doc_links = doc_links + concall_links + quarterly_pdfs

        # ------------------------------------------------------
        #    DOWNLOAD EACH DOCUMENT
        # ------------------------------------------------------
        for item in all_doc_links:
            category = item['category']
            text = item['text'] or ''
            full_url = item['url']
            force_pdf = item.get('force_pdf', False)

            # Clean filename
            filename = clean_filename(text)

            # FIX STARTS HERE  ***********************************************
            if category not in folders:
                folder_key = 'other'
            else:
                folder_key = category

            if category not in download_stats:
                category = 'other'
            # FIX ENDS HERE  *************************************************

            # Determine correct extension
            ext_src = os.path.splitext(urlparse(full_url).path)[1].lower()

            if force_pdf:
                ext = ".pdf"
            else:
                if ext_src in ['.pdf']:
                    ext = ".pdf"
                elif ext_src in ['.htm', '.html']:
                    ext = ".html"
                else:
                    ext = ".html"

            filename = filename + ext
            save_path = folders[folder_key] / filename

            if save_path.exists():
                continue

            print(f"  Downloading [{category}]: {filename}")
            print(f"     URL: {full_url}")

            ok = download_file(full_url, save_path)
            if ok:
                download_stats[category] += 1
            else:
                print("     ✗ Failed")


        # ------------------------------------------------------
        #               DOCUMENTS SUMMARY
        # ------------------------------------------------------
        print("\n" + "="*70)
        print("Documents downloaded:")
        print(f"  Annual Reports:           {download_stats['annual']}")
        print(f"  Concalls:                 {download_stats['concalls']}")
        print(f"  Announcements:            {download_stats['announcements']}")
        print(f"  Credit Ratings:           {download_stats['credit_ratings']}")
        print(f"  Quarterly Result PDFs:    {download_stats['quarterly_results']}")
        print(f"  Other:                    {download_stats['other']}")
        print("="*70 + "\n")

        # ------------------------------------------------------
        #                       SUMMARY CSV
        # ------------------------------------------------------
        summary = {
            'Company Name': company_name,
            'Symbol': symbol,
            'URL': url,
            'Scraped On': time.strftime('%Y-%m-%d %H:%M:%S'),
            'Login Successful': 'Yes' if login_success else 'No',
            'Paywall Detected': 'Yes' if paywall_detected else 'No',
            'Financial Tables Extracted': len(tables_saved),
            'Annual Reports': download_stats['annual'],
            'Concalls': download_stats['concalls'],
            'Announcements': download_stats['announcements'],
            'Credit Ratings': download_stats['credit_ratings'],
            'Quarterly Result PDFs': download_stats['quarterly_results'],
            'Other Documents': download_stats['other']
        }

        pd.DataFrame([summary]).to_csv(company_folder / "summary.csv", index=False)
        print("✓ Saved summary.csv")

        # ------------------------------------------------------
        #              TABLE INDEX (Rows & Columns)
        # ------------------------------------------------------
        pd.DataFrame([
            {'Table': name, 'Rows': shape[0], 'Columns': shape[1]}
            for name, shape in tables_saved.items()
        ]).to_csv(folders['tables'] / "_table_index.csv", index=False)

        print("✓ Saved table index (_table_index.csv)\n")

        print("="*70)
        print(f"SCRAPING COMPLETE: Output folder → {company_folder}/")
        print("="*70 + "\n")

        return company_folder, tables_saved, download_stats


    finally:
        print("Closing browser in 3 seconds…")
        time.sleep(3)
        driver.quit()


#Part6
# ======================================================
#              EXTRACT CONCALL NOTES (MODAL)
# ======================================================
def extract_concall_notes(driver, company_folder: Path):
    """
    Extract all Concall Notes from the right-side modal (offcanvas dialog)
    that pops up when clicking the 'Notes' button.
    """

    notes_folder = company_folder / "concall_notes"
    notes_folder.mkdir(exist_ok=True)

    wait = WebDriverWait(driver, 10)

    print("\n[Concalls] Extracting Notes from modal/off-canvas…")

    # ----------------------------------------------
    # Helper to close any open modal
    # ----------------------------------------------
    def close_modal():
        try:
            dialogs = driver.find_elements(By.CSS_SELECTOR, "dialog.modal.modal-right[open]")
            if not dialogs:
                return

            dlg = dialogs[0]

            try:
                # Try clicking the close button
                close_btn = dlg.find_element(
                    By.XPATH,
                    ".//button[.//i[contains(@class,'icon-cancel') or contains(@class,'icon-cancel-thin')]]"
                )
                close_btn.click()
            except:
                # If fail, try ESC key
                try:
                    driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
                except:
                    pass

            # Wait for modal to disappear
            try:
                wait.until(EC.invisibility_of_element_located(
                    (By.CSS_SELECTOR, "dialog.modal.modal-right[open]")
                ))
            except:
                pass

        except Exception:
            pass

    # Always close any modal before starting
    close_modal()

    # ----------------------------------------------
    # Locate all NOTES buttons
    # ----------------------------------------------
    try:
        notes_buttons = driver.find_elements(
            By.XPATH,
            "//button[contains(@class,'concall-link') and normalize-space()='Notes']"
        )
    except Exception as e:
        print(f"  [Concalls] ERROR locating Notes buttons: {e}")
        return

    print(f"  [Concalls] Found {len(notes_buttons)} Notes buttons")

    if not notes_buttons:
        return

    # ----------------------------------------------
    # Process each NOTES button
    # ----------------------------------------------
    for idx in range(len(notes_buttons)):
        try:
            # Reload buttons (DOM may change)
            notes_buttons = driver.find_elements(
                By.XPATH,
                "//button[contains(@class,'concall-link') and normalize-space()='Notes']"
            )

            if idx >= len(notes_buttons):
                break

            btn = notes_buttons[idx]

            # ----------------------------------------------
            # Determine title for the markdown file
            # ----------------------------------------------
            title = None

            try:
                title = btn.get_attribute("data-title")
            except:
                pass

            if not title:
                try:
                    parent = btn.find_element(By.XPATH, "./ancestor::*[self::li or self::div][1]")
                    title = parent.text.splitlines()[0].strip()
                except:
                    title = f"Concall_{idx+1}"

            print(f"    → Clicking Notes button #{idx+1}: {title}")

            # Ensure no modal is open
            close_modal()

            # Scroll button into view
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
            time.sleep(0.5)

            # Click the button
            try:
                btn.click()
            except:
                driver.execute_script("arguments[0].click();", btn)

            # Wait for modal
            try:
                dialog = wait.until(
                    EC.visibility_of_element_located(
                        (By.CSS_SELECTOR, "dialog.modal.modal-right[open]")
                    )
                )
            except Exception:
                print(f"    ✗ Modal did NOT open for {title}")
                continue

            # ----------------------------------------------
            # Extract text from modal
            # ----------------------------------------------
            try:
                body = dialog.find_element(By.CSS_SELECTOR, "div.modal-body")
            except:
                body = dialog

            try:
                article = body.find_element(By.CSS_SELECTOR, "article.sub, article")
                text = article.text.strip()
            except:
                text = (body.text or "").strip()

            if not text:
                print(f"    ✗ No text found for {title}")
            else:
                safe_name = clean_filename(f"{title}_concall_notes")
                out_path = notes_folder / f"{safe_name}.md"
                out_path.write_text(text, encoding="utf-8")
                print(f"    ✓ Saved notes: {out_path.name}")

            # ----------------------------------------------
            # Close modal
            # ----------------------------------------------
            close_modal()

            time.sleep(0.3)

        except Exception as e:
            print(f"    ✗ Error processing Notes #{idx+1}: {e}")
            close_modal()


#Part7
# ======================================================
#      EXTRACT CONCALL LINKS (but NOT modal notes)
# ======================================================
def extract_concalls_comprehensive(driver, soup, base_url):
    """
    Extract Concall links (audio/text) from the Documents section.
    Notes are handled separately by extract_concall_notes().
    """
    concalls = []

    print("  [Concalls] Extracting concall links...")

    # Find concall container
    ccontainer = None
    for div in soup.find_all("div", class_=lambda c: c and "documents" in c and "concalls" in c):
        h3 = div.find("h3")
        if h3 and "concall" in h3.get_text(strip=True).lower():
            ccontainer = div
            break

    if not ccontainer:
        print("  [Concalls] No concall container found")
        return concalls

    ul = ccontainer.find("ul", class_="list-links")
    if not ul:
        print("  [Concalls] No <ul> inside concall container")
        return concalls

    for li in ul.find_all("li"):
        # Quarter label
        quarter_div = li.find("div")
        quarter_text = quarter_div.get_text(strip=True) if quarter_div else None

        # Links inside the LI
        for el in li.find_all("a", href=True):
            link_text = el.get_text(strip=True)
            href = el["href"]

            if not link_text or not href:
                continue

            concalls.append({
                "category": "concalls",
                "text": link_text if not quarter_text else f"{quarter_text}_{link_text}",
                "url": urljoin(base_url, href),
                "quarter": quarter_text,
                "type": link_text.lower()
            })

    print(f"  [Concalls] Total concall links collected: {len(concalls)}")
    return concalls


# ======================================================
#                    MAIN ENTRY POINT
# ======================================================
if __name__ == "__main__":
    symbol = input("Enter company symbol (e.g., TCS): ").strip().upper()

    if not symbol:
        symbol = "TCS"

    try:
        folder, table_info, docs = scrape_screener_company(symbol)
        print(f"\n✅ SUCCESS! All data saved at: {folder}/")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
