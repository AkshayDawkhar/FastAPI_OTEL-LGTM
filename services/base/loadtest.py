import time

import requests

def load_test():
    base_url = "http://localhost"
    for _ in range(2000):
        resp = requests.get(base_url)
    print("Load test completed.")
load_test()


