import os
import json
import random
import string
import datetime
import requests
import argparse
from datetime import datetime
from urllib.parse import urlparse
import colorama
from colorama import Fore, Style

TMP_FOLDER = "./tmp"
REQUESTS_FOLDER = "./requests"
USER_AGENTS_FILE = "./utils/user-agents"
AUTH_FILE = os.path.join(REQUESTS_FOLDER, "auth")
HEADERS = {}

# Characters to use for testing
CHARS = [
    "",
    "'",
    "\"",
    "<",
    ">",
    ";",
    "=",
    "&",
    "(",
    ")",
    "+",
    "-",
    "*",
    "/",
    "\\",
    "%0A",
    "%0D",
    "%3C",
    "%3E",
    "%22",
    "%27",
    "%3B",
    "%2B",
    "%2D",
    "%2F",
    "%5C",
    "%25",
]

# initialize colorama
colorama.init()

def load_user_agents():
    with open(USER_AGENTS_FILE, "r") as f:
        user_agents = f.read().splitlines()
    return user_agents

def send_file_request(request_file, headers_list=None, verify=True):
    with open(request_file) as f:
        request_lines = f.readlines()

    # Get request method, URL and version from first line
    method, url, version = request_lines[0].strip().split()

    # Get request headers from the remaining lines
    headers = {}

    # Find host and set
    host = None
    for line in request_lines[1:]:
        if line.strip() == "":
            break
        header_name, header_value = line.strip().split(": ", 1)
        headers[header_name] = header_value
        if header_name.lower() == "host":
            host = header_value

    if host is not None:
        url = url.replace(f"{host}/", "")
        url = f"{headers.get('Scheme', 'https://')}{host}{url}"

    # Set random user agent
    headers["User-Agent"] = random.choice(USER_AGENTS)

    # Add extra headers to headers dictionary
    if headers_list is not None:
        for h in headers_list:
            headers.update(h)

    # Get request body
    body = "".join(request_lines).split("\r\n\r\n", 1)[1] if "\r\n\r\n" in "".join(request_lines) else ""

    # Get the response
    response = requests.request(method, url, headers=headers, data=body, verify=verify)

    status_code = response.status_code
    if status_code == 200:
        status_color = Fore.GREEN
    else:
        status_color = Fore.RED

    print(f"  {Style.BRIGHT}{method}{Style.RESET_ALL} - {status_color}{status_code}{Style.RESET_ALL} - {Style.BRIGHT}{url}{Style.RESET_ALL}\n\n")

    return response

def send_url_request(url, method, headers=None, data=None, verify=True):
    # Send the request
    response = requests.request(method, url, headers=headers, data=data, verify=verify)

    return response


def test_params(params, method, url, headers, save_results=False):
    results = []
    for param in params.keys():
        for char in CHARS:
            if params[param] is None:
                # Parameter has no value, so add the character as a value
                test_params = {param: char}
            else:
                # Parameter has a value, so add the character to the value
                test_params = {param: f"{params[param]}{char}"}

            # Inject the character into the URL
            test_url = url.replace(f"{param}={params[param]}", f"{param}={test_params[param]}")

            # Send the request with the modified URL
            response = send_url_request(test_url, method, headers, False)

            # Add the response text to the results list
            results.append({
                "params": str(test_params),
                "test": test_url,
                "result": response.text if len(response.text) <= 500 else "Response too long to be saved."
            })

            status_code = response.status_code
            if status_code == 200:
                status_color = Fore.GREEN
            elif status_code > 399 and status_code < 500:
                status_color = Fore.CYAN
            elif status_code > 499 and status_code < 600:
                status_color = Fore.RED
            else:
                status_color = Fore.WHITE

            print(f"  {status_color}{method} - {response.status_code} - {test_url}{Style.RESET_ALL}")
        
    # Save the results to a file if save_results flag is True
    if save_results:
        # Create a unique filename using the current date and time, domain name, and a random string of 5 characters
        now = datetime.now().strftime("%Y%m%d%H%M%S")
        domain_name = url.split('/')[2]
        random_string = ''.join(random.choices(string.ascii_lowercase, k=5))
        filename = f"{now}_{domain_name}_{random_string}.json"
        filepath = os.path.join(TMP_FOLDER, filename)
        
        # Save the results to a file
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=4)

    return results

def main():
    try:
        # Parse command line arguments
        parser = argparse.ArgumentParser(description="Execute requests from file(s)")
        parser.add_argument("-o", "--output", metavar="output_file", type=str, help="write output to file")
        parser.add_argument("-s", "--save", action="store_true", help="save test results to file")
        parser.add_argument("-v", "--verbose", action="store_true", help="show response body")
        args = parser.parse_args()

        # Load user agents
        print("➜ Loading user agents...")
        global USER_AGENTS
        USER_AGENTS = load_user_agents()

        # Authenticate and get session token
        print("➜ Finding Auth Token...")
        token = None
        if os.path.exists(AUTH_FILE):
            response = send_file_request(AUTH_FILE)
            token = response.json()["token"]["access_token"]

        # Get list of request files
        print("➜ Loading request files...")
        request_files = [f for f in os.listdir(REQUESTS_FOLDER) if os.path.isfile(os.path.join(REQUESTS_FOLDER, f)) and f != "auth"]

        # Execute requests and print output
        print("➜ Loading each file...")
        output = []
        for filename in request_files:
            filepath = os.path.join(REQUESTS_FOLDER, filename)
            
            print(f"➜ Requesting {filepath}...")
            with open(filepath) as f:
                request_lines = f.readlines()

            # Get request method, URL and version from first line
            method, url, version = request_lines[0].strip().split()

            # Get request headers from the remaining lines
            headers = {}
            
            # Find host and set
            host = None
            for line in request_lines[1:]:
                if line.strip() == "":
                    break
                header_name, header_value = line.strip().split(": ", 1)
                headers[header_name] = header_value
                if header_name.lower() == "host":
                    host = header_value

            if host is not None:
                url = url.replace(f"{host}/", "")
                url = f"{headers.get('Scheme', 'https://')}{host}{url}"

            # Get request parameters from the URL
            parsed_url = urlparse(url)
            params = {}
            for key, value in [p.split("=") for p in parsed_url.query.split("&")]:
                params[key] = value if value else None
            
            if token is not None:
                headers["Authorization"] = f"Bearer {token}"

            # Test parameters
            print("➜ Testing parameters...")
            results = test_params(params, method, url, headers, args.save)
            
            if args.verbose:
                # Show Results
                status_color = Fore.YELLOW
                print(f"  {status_color}{method} \n {results}{Style.RESET_ALL}\n\n\n")
            
        # Write output to file if specified
        if args.output:
            with open(args.output, "w") as f:
                f.write("\n".join(output))

        status_color = Fore.GREEN
        if args.save:
            print(f"\n➜ {status_color} Script executed successfully! Results saved in {os.path.abspath(TMP_FOLDER)}{Style.RESET_ALL}")
        else:
            print(f"\n➜ {status_color} Script executed successfully! {Style.RESET_ALL}")

    except KeyboardInterrupt:
        print(f"\n➜ stopped by user")

if __name__ == "__main__":
    try:
        # Create temporary directory if it doesn't exist
        if not os.path.exists(TMP_FOLDER):
            os.makedirs(TMP_FOLDER)

        main()
    except Exception as e:
        print("An error occurred:", str(e))
        