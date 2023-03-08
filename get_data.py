## https://www.pro-football-reference.com/draft/2010-combine.htm

import requests
import pandas as pd
import time
import random
import os

YEAR_RANGE = range(2000, 2011)
TARGET_DIR = "combine_data/"

def get_data():
    dataframes = []
    
    for year in YEAR_RANGE:

        target_file = f"{TARGET_DIR}{year}-combine.htm"
        if not os.path.exists(target_file):

            url = f"https://www.pro-football-reference.com/draft/{year}-combine.htm"
            r = requests.get(url)

            with open(target_file, "w") as f:
                f.write(str(r.content))
            df = pd.read_html(r.content)[0]
            time.sleep(6 * random.random()) # don't crawl too hard
        else:
            df = pd.read_html(target_file)

        df['Year'] = year
        dataframes.append(df)
    return dataframes

def process_data(dataframes):
    concatenated = pd.concat(dataframes)


if __name__ == '__main__':
    dataframes = get_data()

    processed_data = process_data(dataframes)


    


