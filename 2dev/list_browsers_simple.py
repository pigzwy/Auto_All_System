
from create_window import get_browser_list
import json

def list_browsers():
    browsers = get_browser_list(page=0, pageSize=10)
    print(f"Found {len(browsers)} browsers")
    for b in browsers:
        print(f"ID: {b.get('id')} | Name: {b.get('name')} | User: {b.get('userName')}")

if __name__ == "__main__":
    list_browsers()
