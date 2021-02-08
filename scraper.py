import requests
from datetime import datetime, timedelta

#--- Customize here
email = 'EMAIL'
password = 'PASSWORD'
# Directory path that you want to store invoice files
directory_path = 'path/to/your/directory'
#---

LOGIN_API = 'https://restaurant-hub.deliveroo.net/api/session'
payload = {'email': email, 'password': password}
headers = {'User-Agent' : 'Mozilla/5.0'}
invoices_api_url = 'https://restaurant-hub.deliveroo.net/api/invoices'

session = requests.Session()

def login(email, password) -> dict:
    """
    Sends a POST request to Deliveroo login API
    """
    try: 
        post = session.post(LOGIN_API, data = payload, headers = headers)
        if (post.status_code == 401):
            raise SystemExit('Invalid email or password')
        post.raise_for_status()
    except requests.exceptions.RequestException as error:
        # Quit the program
        raise SystemExit(error)

    post = post.json()
    company_name = post["restaurant_companies"][0]["name"]
    company_id = post["restaurant_companies"][0]["id"]
    print(f'Welcome back, {company_name}')
    print(f'organization id: {company_id}')

    access_token = post['access_token']
    headers['Authorization'] = 'Bearer ' + access_token
    # Create a token cookie
    token_cookie = {'token': access_token}

    return {
        'org_id': company_id,
        'token_cookie': token_cookie
    }

def get_all_invoices(params, token_cookie) -> list:
    """
    GET Request
    """
    response = session.get(invoices_api_url, headers = headers, params = params, cookies = token_cookie )
    if response.status_code == 200:
        print('Successful get all invoices')

    invoices_list = response.json()

    # Remove invoices which total == 0
    invoices_list = list( filter(isNotZero, invoices_list) )

    return invoices_list

def convertToDate(stringDate) -> datetime:
    return datetime.strptime(stringDate, '%Y-%m-%d')

def fileExists(path) -> bool:
    """
    Check if the file or directory at `path` can
    be accessed by the program using `mode` open flags.
    """
    try:
        file = open(path)
        file.close()
    except IOError:
        return False
    return True

def download_pdf(filter_invoices, token_cookie):

    print('Downloading statement PDFs..')
    # Download statement pdf according to the date
    for invoice in filter_invoices:
        #--- Create date prefix of the filename
        end_date_plus_1_day = convertToDate(invoice['end_date']) + timedelta(days=1)
        # Remove the time '00:00:00' of the date
        end_date_plus_1_day = end_date_plus_1_day.date()
        datePrefix: str = str(end_date_plus_1_day)
        #---
        file_path = f'{directory_path}{datePrefix}-deliveroo.pdf'

        if not fileExists(file_path):
            # Statement_pdf = relevé de compte
            if 'statement_pdf' in invoice['download_links']:
                pdf_download_link = invoice['download_links']['statement_pdf']
            else:
                pdf_download_link = invoice['download_links']['invoice_pdf']
            
            invoice_pdf = session.get(pdf_download_link, headers = headers, cookies = token_cookie)
            with open(file_path, 'wb') as file:
                file.write(invoice_pdf.content)
        else:
            print(f"{file_path} already exists")

    print('Downloading finished')

def isThisYear(invoice, year):
    # 4 first characters of the date
    invoice_year = int(invoice['end_date'][0:4])
    return invoice_year == year

def isThisMonth(invoice, month):
    # the month first characters of the date
    invoice_month = int(invoice['end_date'][5:7])
    return invoice_month == month

# Check if a invoice's total is NOT zero
def isNotZero(invoice):
    return invoice['total']['fractional'] != 0

def main():

    currentUser: dict = login(email, password)
    # Extract token cookie from login()'s returned dict
    org_id: str = currentUser['org_id']
    # Extract organization id from login()'s returned dict
    token_cookie: str = currentUser['token_cookie']
    api_payload = {'org_id': org_id}

    today = datetime.today()
    year = int(input(f'Enter a year between 2000 and {today.year} '))
    while ( year < 2000 or year > today.year ):
        year = int(input(f'Enter a year between 2000 and {today.year} '))

    response = input('Do you want a particular month invoice? y/n ')
    while ( response != 'y' and response != 'n'):
        response = input('Do you want a particular month invoice? y/n ')

    if (response == 'y'):

        while True:
            try:
                month = int(input("Which month do you want to get? "))
                break
            except ValueError:
                print("Please enter a valid month")


        while ( month < 1 or month > 12 ):
            month = int(input('Enter a month between 1 and 12 '))

        # Get all invoices of this year
        all_invoices = get_all_invoices(api_payload, token_cookie)
        # Get invoices of this year
        filter_invoices = list( filter(lambda invoice: isThisYear(invoice, year), all_invoices) )
        # Filter the month of the date 
        filter_invoices = list(filter(lambda invoice: isThisMonth(invoice, month), filter_invoices))

        if filter_invoices:
            download_pdf(filter_invoices, token_cookie)
        else:
            print('Pdf invoices not found')

    else:
        #--- Get all invoices of this year
        all_invoices = get_all_invoices(api_payload, token_cookie)
        filter_invoices = list( filter(lambda invoice: isThisYear(invoice, year), all_invoices) )
        #---    

        if not filter_invoices:
            print('Pdf invoices not found')

        download_pdf(filter_invoices, token_cookie)

main()

session.close()