import argparse
import sys
import urllib.error
import urllib.request


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Smoke check for /api/v1/assignments availability"
    )
    parser.add_argument("--base-url", required=True, help="API base URL, e.g. https://host/api/v1")
    parser.add_argument("--token", required=True, help="Bearer access token")
    parser.add_argument("--tenant-code", required=True, help="Tenant code for X-Tenant-Code header")
    args = parser.parse_args()

    url = f"{args.base_url.rstrip('/')}/assignments"
    headers = {
        "Authorization": f"Bearer {args.token}",
        "X-Tenant-Code": args.tenant_code,
    }
    request = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            status = response.status
            body = response.read(300).decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        body = exc.read(300).decode("utf-8", errors="replace")
        print(f"FAIL: {url} returned {exc.code} {body}")
        return 1
    except urllib.error.URLError as exc:
        print(f"FAIL: request error for {url}: {exc.reason}")
        return 1
    if status != 200:
        print(f"FAIL: {url} returned {status} {body}")
        return 1
    print(f"OK: {url} is reachable")
    return 0


if __name__ == "__main__":
    sys.exit(main())
