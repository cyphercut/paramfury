import os
import random
import requests
import argparse
from urllib.parse import urlparse

REQUESTS_FOLDER = "./requests"
USER_AGENTS_FILE = "./utils/user-agents"
AUTH_FILE = os.path.join(REQUESTS_FOLDER, "auth")
HEADERS = {}

def load_user_agents():
    with open(USER_AGENTS_FILE, "r") as f:
        user_agents = f.read().splitlines()
    return user_agents

def send_request(request_file, headers_list=None, verify=True):
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

    print(f"  {method}")
    print(f"  {url}")
    print(f"  Status: \033[1m{response.status_code}\033[0m\n\n")

    return response

def main():
    try:
        # Parse command line arguments
        parser = argparse.ArgumentParser(description="Execute requests from file(s)")
        parser.add_argument("-o", "--output", metavar="output_file", type=str, help="write output to file")
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
            response = send_request(AUTH_FILE)
            token = response.json()["token"]["access_token"]

        # Get list of request files
        print("➜ Loading request files...")
        request_files = [f for f in os.listdir(REQUESTS_FOLDER) if os.path.isfile(os.path.join(REQUESTS_FOLDER, f)) and f != "auth"]

        # Execute requests and print output
        print("➜ Loading each file...")
        output = []
        for filename in request_files:
            filepath = os.path.join(REQUESTS_FOLDER, filename)
            headers_list = []
            if token is not None:
                headers_list.append({"Authorization": f"Bearer {token}"})
            
            print(f"➜ Requesting {filepath}...")
            response = send_request(filepath, headers_list)

            output.append(f"File: {filename}")
            output.append(f"Status: \033[1m{response.status_code}\033[0m")
            if args.verbose:
                output.append(f"Body: \033[1m{response.text}\033[0m\n")
                print(f"Body: \033[1m{response.text}\033[0m\n")
            
        # Write output to file if specified
        if args.output:
            with open(args.output, "w") as f:
                f.write("\n".join(output))
    except KeyboardInterrupt:
        print(f"\n➜ stopped by user")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("An error occurred:", str(e))

