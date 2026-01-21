import re
import aiohttp

# Regex Pattern
card_pattern = re.compile(
    r'(\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{3,4}\b)[|:/\s]?\b(\d{1,2})[|:/\s]?(\d{2,4})\b[|:/\s]?(\d{3,4})?',
    re.IGNORECASE
)

# --- FLAG ENGINE (MASTER LIST) ---
def get_flag_from_name(country_name):
    """နိုင်ငံနာမည် သို့မဟုတ် Code ပေးလိုက်ရင် အလံပြန်ပေးမည့် Function"""
    if not country_name: return "🏳️"
    
    text = country_name.upper().strip()
    
    # Code (2 letter) ဖြစ်နေရင် တန်းတွက်မယ် (US, TH, MM)
    if len(text) == 2:
        return "".join([chr(0x1F1E6 + ord(c) - ord('A')) for c in text])

    # Name ဖြစ်နေရင် Code အရင်ရှာမယ်
    name_to_code = {
        "AFGHANISTAN": "AF", "ALBANIA": "AL", "ALGERIA": "DZ", "ANDORRA": "AD", "ANGOLA": "AO",
        "ARGENTINA": "AR", "ARMENIA": "AM", "AUSTRALIA": "AU", "AUSTRIA": "AT", "AZERBAIJAN": "AZ",
        "BAHAMAS": "BS", "BAHRAIN": "BH", "BANGLADESH": "BD", "BARBADOS": "BB", "BELARUS": "BY",
        "BELGIUM": "BE", "BELIZE": "BZ", "BENIN": "BJ", "BHUTAN": "BT", "BOLIVIA": "BO",
        "BOSNIA": "BA", "BOTSWANA": "BW", "BRAZIL": "BR", "BRUNEI": "BN", "BULGARIA": "BG",
        "BURKINA FASO": "BF", "BURUNDI": "BI", "CAMBODIA": "KH", "CAMEROON": "CM", "CANADA": "CA",
        "CAPE VERDE": "CV", "CHAD": "TD", "CHILE": "CL", "CHINA": "CN", "COLOMBIA": "CO",
        "COMOROS": "KM", "CONGO": "CG", "COSTA RICA": "CR", "CROATIA": "HR", "CUBA": "CU",
        "CYPRUS": "CY", "CZECH REPUBLIC": "CZ", "CZECHIA": "CZ", "DENMARK": "DK", "DJIBOUTI": "DJ",
        "DOMINICA": "DM", "DOMINICAN REPUBLIC": "DO", "ECUADOR": "EC", "EGYPT": "EG", "EL SALVADOR": "SV",
        "ESTONIA": "EE", "ETHIOPIA": "ET", "FIJI": "FJ", "FINLAND": "FI", "FRANCE": "FR",
        "GABON": "GA", "GAMBIA": "GM", "GEORGIA": "GE", "GERMANY": "DE", "GHANA": "GH",
        "GREECE": "GR", "GRENADA": "GD", "GUATEMALA": "GT", "GUINEA": "GN", "GUYANA": "GY",
        "HAITI": "HT", "HONDURAS": "HN", "HONG KONG": "HK", "HUNGARY": "HU", "ICELAND": "IS",
        "INDIA": "IN", "INDONESIA": "ID", "IRAN": "IR", "IRAQ": "IQ", "IRELAND": "IE",
        "ISRAEL": "IL", "ITALY": "IT", "JAMAICA": "JM", "JAPAN": "JP", "JORDAN": "JO",
        "KAZAKHSTAN": "KZ", "KENYA": "KE", "KIRIBATI": "KI", "KOREA": "KR", "SOUTH KOREA": "KR",
        "NORTH KOREA": "KP", "KUWAIT": "KW", "KYRGYZSTAN": "KG", "LAOS": "LA", "LATVIA": "LV",
        "LEBANON": "LB", "LESOTHO": "LS", "LIBERIA": "LR", "LIBYA": "LY", "LIECHTENSTEIN": "LI",
        "LITHUANIA": "LT", "LUXEMBOURG": "LU", "MACAU": "MO", "MACEDONIA": "MK", "MADAGASCAR": "MG",
        "MALAWI": "MW", "MALAYSIA": "MY", "MALDIVES": "MV", "MALI": "ML", "MALTA": "MT",
        "MARSHALL ISLANDS": "MH", "MAURITANIA": "MR", "MAURITIUS": "MU", "MEXICO": "MX", "MICRONESIA": "FM",
        "MOLDOVA": "MD", "MONACO": "MC", "MONGOLIA": "MN", "MONTENEGRO": "ME", "MOROCCO": "MA",
        "MOZAMBIQUE": "MZ", "MYANMAR": "MM", "BURMA": "MM", "NAMIBIA": "NA", "NAURU": "NR",
        "NEPAL": "NP", "NETHERLANDS": "NL", "NEW ZEALAND": "NZ", "NICARAGUA": "NI", "NIGER": "NE",
        "NIGERIA": "NG", "NORWAY": "NO", "OMAN": "OM", "PAKISTAN": "PK", "PALAU": "PW",
        "PANAMA": "PA", "PAPUA NEW GUINEA": "PG", "PARAGUAY": "PY", "PERU": "PE", "PHILIPPINES": "PH",
        "POLAND": "PL", "PORTUGAL": "PT", "QATAR": "QA", "ROMANIA": "RO", "RUSSIA": "RU",
        "RWANDA": "RW", "SAMOA": "WS", "SAN MARINO": "SM", "SAUDI ARABIA": "SA", "SENEGAL": "SN",
        "SERBIA": "RS", "SEYCHELLES": "SC", "SIERRA LEONE": "SL", "SINGAPORE": "SG", "SLOVAKIA": "SK",
        "SLOVENIA": "SI", "SOLOMON ISLANDS": "SB", "SOMALIA": "SO", "SOUTH AFRICA": "ZA", "SPAIN": "ES",
        "SRI LANKA": "LK", "SUDAN": "SD", "SURINAME": "SR", "SWAZILAND": "SZ", "SWEDEN": "SE",
        "SWITZERLAND": "CH", "SYRIA": "SY", "TAIWAN": "TW", "TAJIKISTAN": "TJ", "TANZANIA": "TZ",
        "THAILAND": "TH", "TIMOR-LESTE": "TL", "TOGO": "TG", "TONGA": "TO", "TRINIDAD AND TOBAGO": "TT",
        "TUNISIA": "TN", "TURKEY": "TR", "TURKIYE": "TR", "TÜRKIYE": "TR", "TURKMENISTAN": "TM",
        "TUVALU": "TV", "UGANDA": "UG", "UKRAINE": "UA", "UAE": "AE", "UNITED ARAB EMIRATES": "AE",
        "UNITED KINGDOM": "GB", "UK": "GB", "GREAT BRITAIN": "GB",
        "UNITED STATES": "US", "USA": "US", "AMERICA": "US",
        "URUGUAY": "UY", "UZBEKISTAN": "UZ", "VANUATU": "VU", "VATICAN": "VA", "VENEZUELA": "VE",
        "VIETNAM": "VN", "VIET NAM": "VN", "YEMEN": "YE", "ZAMBIA": "ZM", "ZIMBABWE": "ZW"
    }
    
    code = name_to_code.get(text)
    if code:
        # Generate Flag from Code
        return "".join([chr(0x1F1E6 + ord(c) - ord('A')) for c in code])
    
    return "🏳️"

async def get_bin_details(session, card_number):
    bin_number = card_number[:6]
    try:
        async with session.get(f'https://bins.antipublic.cc/bins/{bin_number}', timeout=5) as response:
            if response.status == 200:
                data = await response.json()
                if 'bin' in data:
                    country_name = data.get('country_name', 'Unknown')
                    country_code = data.get('country_code', '')
                    
                    # Flag Calculation Logic:
                    # 1. Try API Code
                    # 2. Try API Name
                    # 3. Default to White Flag
                    flag = "🏳️"
                    if country_code and len(country_code) == 2:
                        flag = "".join([chr(0x1F1E6 + ord(c) - ord('A')) for c in country_code.upper()])
                    elif country_name != 'Unknown':
                        flag = get_flag_from_name(country_name)

                    return {
                        "country": country_name,
                        "country_flag": flag, 
                        "bank": data.get('bank', 'Unknown'),
                        "type": data.get('type', 'Unknown'),
                        "level": data.get('level', 'Unknown'),
                        "brand": data.get('brand', 'Unknown')
                    }
    except:
        pass
    return {
        "country": "Unknown", "country_flag": "🏳️", "bank": "Unknown", 
        "type": "Unknown", "level": "Unknown", "brand": "Unknown"
    }

def parse_expiry_year(year_str):
    if len(year_str) == 2:
        return int("20" + year_str)
    return int(year_str)
