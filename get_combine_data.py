## https://www.pro-football-reference.com/draft/2010-combine.htm

import requests
import pandas as pd
import time
import random
import os

YEAR_RANGE = range(2000, 2021)
TARGET_DIR = "combine_data/"

NUMERIC_COLS = ['Wt', '40yd', 'Vertical', 'Bench', 'Broad Jump', '3Cone', 'Shuttle']

COMBINE_METRICS = ['40yd', 'Vertical', 'Bench', 'Broad Jump', '3Cone', 'Shuttle']

EXTRACT_DRAFTED = r"(?P<tm>.+) / (?P<rnd>\d+).+ / (?P<pick>\d+).+ / (?P<yr>.+)"

DROP_COLS = ['College'] # this is a link to college stats.

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
            df = pd.read_html(target_file)[0]

        df['CombineYear'] = year
        dataframes.append(df)
    return dataframes

def process_data(dataframes):
    all_data = pd.concat(dataframes, ignore_index=True)


    ## these are header rows, not actual players.
    all_data = all_data.drop(all_data[all_data.Wt == "Wt"].index, axis=0)

    all_data[NUMERIC_COLS] = all_data[NUMERIC_COLS].astype(float)

    all_data = all_data.drop(DROP_COLS, axis=1)

    extracted = all_data["Drafted (tm/rnd/yr)"].str.extract(EXTRACT_DRAFTED)

    ## I think there are some years where teams lose their picks, so the draft number may not be right
    ## not all drafted players go to the combine, so it would be non-trivial to figure out the real number.
    ## using floats here because there are NaN values for players not drafted.

    extracted['DraftNumber'] = extracted.pick.astype(float) + (32 * (extracted.rnd.astype(float) - 1))

    ## TODO? Height?

    return all_data.join(extracted)


if __name__ == '__main__':
    dataframes = get_data()

    processed_data = process_data(dataframes)


    


