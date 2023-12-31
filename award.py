import requests #import library
import json
import re
import pandas as pd
import os
import ast
import datetime
import calendar, time
from urllib.parse import unquote
from dotenv import load_dotenv
import concurrent.futures

print(load_dotenv())
SAMSARA_API_TOKEN = os.getenv('SAMSARA_API_TOKEN')


# request = input("Enter url of data needed: " )

import csv
import json
import requests
# url = "https://api.samsara.com/fleet/reports/vehicles/fuel-energy?startDate=2022-03-31T23%3A59%3A59.394843%2B00%3A00&endDate=2022-03-31T23%3A59%3A59.394843%2B00%3A00"


OUTPUT_FILE = "output.csv"

INITAL_BONUS = 500


ZERO_DEDUCTION = 0 #key value for cost of tier 0 deduction
MID_DEDUCTION = 1 #key value for cost of tier 1 deduction
HIGH_DEDUCTION = 2 #key value for cost of tier 2 deduction

MID_COST = 25
HIGH_COST = 50

DEDUCTION = {
    ZERO_DEDUCTION: 0,
    MID_DEDUCTION: MID_COST,
    HIGH_DEDUCTION: HIGH_COST
}

SAFETY_SCORE_RANGE = [98, (96,97), 95]

IDLE_RANGES = [7.0, (7.1, 24), 24.1]

HARSH_RANGE = [0,1,2]
MPG = [7.0, (6.0,6.9), 5.9]


def calculate_idle_deduction(run_time, idle_time):
    '''
    IDLE_RANGES = [7.0, (7.1, 24), 24.1]
    '''
    idle_perct = float((idle_time/run_time) * 100)
    if idle_perct >= IDLE_RANGES[2]:
        deduct = DEDUCTION[HIGH_DEDUCTION]
    elif isinstance(IDLE_RANGES[1], tuple) and IDLE_RANGES[1][0] <= idle_perct <= IDLE_RANGES[1][1]:
        deduct =  DEDUCTION[MID_DEDUCTION]
    else:
        deduct =  DEDUCTION[ZERO_DEDUCTION]
    return idle_perct, deduct
    
def calculate_safety_deduction(safety_score):
    '''
    SAFETY_SCORE_RANGE = [98, (96,97), 95]
    '''
    if safety_score <= SAFETY_SCORE_RANGE[2]:
        return DEDUCTION[HIGH_DEDUCTION]
    elif isinstance(SAFETY_SCORE_RANGE[1], tuple) and SAFETY_SCORE_RANGE[1][0] <= safety_score <= SAFETY_SCORE_RANGE[1][1]:
        return DEDUCTION[MID_DEDUCTION]
    else:
        return DEDUCTION[ZERO_DEDUCTION]
    
def calculate_mpg_deduction(mpg):
    '''
    MPG = [7.0, (6.0,6.9), 5.9]
    '''
    if mpg <= MPG[2]:
        return DEDUCTION[HIGH_DEDUCTION]
    elif isinstance(MPG[1], tuple) and MPG[1][0] <= mpg <= MPG[1][1]:
        return DEDUCTION[MID_DEDUCTION]
    else:
        return DEDUCTION[ZERO_DEDUCTION]
    
def calculate_harsh_deduction(events) -> int:
    if(events>=HARSH_RANGE[2]):
        return DEDUCTION[HIGH_DEDUCTION]
    elif(events==HARSH_RANGE[1]):
        return DEDUCTION[MID_DEDUCTION]
    else:
        return DEDUCTION[ZERO_DEDUCTION]


def write_to_csv(data: list) -> pd.DataFrame:
    df = pd.DataFrame(data, columns=['Driver ID', 'Driver Name', 'Idle Deduct', 'Idle Percent', 'MPG Deduct', 'Efficiency', "Harsh Deduct", "Harsh Events","Safety Deduct","Safety Score", "Total Bonus"])
    df = df.sort_values(by="Total Bonus", ascending=False)
    df.to_csv(OUTPUT_FILE, index=False)
    return df

def find_driver(df: pd.DataFrame, driver_id: str, start, end):
    data = []
    try:
        df = df[df['driver'].apply(lambda x: x['id'] if isinstance(x, dict) and 'id' in x else None) == driver_id]
    except Exception as e:
        return (f"An error occurred: {e}")

    row, (safety_score_driver, harsh_event, error) = get_safety_score_and_event_count(df.iloc[0],start,end)
    if error:
        row, (safety_score_driver, harsh_event, error) = get_safety_score_and_event_count(row, start, end)
        if(error):
            print(f"Error processing row {row['driver']['name']}: {error}")
            return
    mpg_deduct = calculate_mpg_deduction(row["efficiencyMpge"])
    idle_perct, idle_deduct = calculate_idle_deduction(row["engineRunTimeDurationMs"], row["engineIdleTimeDurationMs"])
    id = row["driver"]["id"]
    name = row["driver"]["name"]
    harsh_cost = calculate_harsh_deduction(harsh_event)

    safety_deduct = calculate_safety_deduction(safety_score_driver)
    final_bonus = INITAL_BONUS - (mpg_deduct + idle_deduct + harsh_cost + safety_deduct)

    data.append([id, name, idle_deduct, idle_perct, mpg_deduct,row["efficiencyMpge"], harsh_cost, harsh_event,safety_deduct, safety_score_driver, final_bonus])
    print(data)
    return data

def parse_df(df: pd.DataFrame, quarter: int, driver_id = None):
    data = []
    start, end = get_in_unix_epoch(quarter)
    # print(df['driver'].head())
    if(driver_id != None and driver_id != 'none'):
        return find_driver(df, driver_id, start, end)
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_to_row = {executor.submit(get_safety_score_and_event_count, row, start, end): row for _, row in df.iterrows()}
        for future in concurrent.futures.as_completed(future_to_row):
            row, (safety_score_driver, harsh_event, error) = future.result()
            if error:
                row, (safety_score_driver, harsh_event, error) = get_safety_score_and_event_count(row, start, end)
                if(error):
                    print(f"Error processing row {row['driver']['name']}: {error}")
                    continue
            mpg_deduct = calculate_mpg_deduction(row["efficiencyMpge"])
            idle_perct, idle_deduct = calculate_idle_deduction(row["engineRunTimeDurationMs"], row["engineIdleTimeDurationMs"])
            id = row["driver"]["id"]
            name = row["driver"]["name"]
            harsh_cost = calculate_harsh_deduction(harsh_event)

            safety_deduct = calculate_safety_deduction(safety_score_driver)
            final_bonus = INITAL_BONUS - (mpg_deduct + idle_deduct + harsh_cost + safety_deduct)

            data.append([id, name, idle_deduct, idle_perct, mpg_deduct,row["efficiencyMpge"], harsh_cost, harsh_event,safety_deduct, safety_score_driver, final_bonus])
        return data





def fuel_and_energy_call(quarter: int):
    url = f"https://api.samsara.com/fleet/reports/drivers/fuel-energy?startDate={QUARTERLY[quarter][0]}&endDate={QUARTERLY[quarter][1]}&driverIds="

    headers = {
        "accept": "application/json",
        "authorization": f"Bearer {SAMSARA_API_TOKEN}"
    }

    try:
        response = requests.get(url, headers=headers)
        # Extract the JSON data from the response
        json_data = response.json()
        # Extract the driver reports from the JSON data
        driver_reports = json_data['data']['driverReports']
        df = pd.DataFrame(driver_reports)
    except Exception as e:
        return (f"An error occurred: {e}")
    return df


# This function will get safety score and event count for a driver in a certain period
def get_safety_score_and_event_count(row, start_time: int, end_time: int):
    driver_id = row["driver"]["id"]
    max_retries = 5  # You can adjust this number as needed
    retries = 0

    while retries < max_retries:
        try:
            url = f"https://api.samsara.com/v1/fleet/drivers/{driver_id}/safety/score?startMs={start_time}&endMs={end_time}"
            headers = {
                "accept": "application/json",
                "authorization": f"Bearer {SAMSARA_API_TOKEN}"
            }
            response = requests.get(url, headers=headers)

            if response.status_code == 429:
                retry_after = response.headers.get('Retry-After')  # Retrieve the value of Retry-After header
                time.sleep(0.5)  # Delay the execution of the next request
                retries += 1
                continue  # Go to next iteration of loop, re-running the request

            # If response is successful, parse json and return
            json_data = response.json()
            return row, (json_data["safetyScore"], json_data["totalHarshEventCount"], None)

        except Exception as e:
            return row, (None, None, f"An error occurred: {e}")
    
    # If the loop completes without a successful request, return an error
    return row, (None, None, f"An error occurred: Maximum retries reached")




def get_in_unix_epoch(quarter: int):
    start, end = QUARTERLY[quarter][0], QUARTERLY[quarter][1]
    decoded_start = unquote(start)
    decoded_end = unquote(end)
    date_start = decoded_start.split("T")[0]
    date_end = decoded_end.split("T")[0]
    date_start_final = f'{date_start} 01:01:00'
    date_end_final = f'{date_end} 23:00:00'

    unix_epoch_start = (calendar.timegm(time.strptime(date_start_final, '%Y-%m-%d %H:%M:%S'))) * 1000
    unix_epoch_end = (calendar.timegm(time.strptime(date_end_final, '%Y-%m-%d %H:%M:%S'))) * 1000

    print(unix_epoch_end, unix_epoch_start)
    return unix_epoch_start, unix_epoch_end






def update_year(year):
    global CURRENT_YEAR, QUARTERLY
    CURRENT_YEAR = year
    QUARTERLY = {
        1: (f"{CURRENT_YEAR}-01-01T23%3A59%3A59.394843%2B00%3A00", f"{CURRENT_YEAR}-03-31T23%3A59%3A59.394843%2B00%3A00"), 
        2: (f"{CURRENT_YEAR}-04-01T23%3A59%3A59.394843%2B00%3A00", f"{CURRENT_YEAR}-06-30T23%3A59%3A59.394843%2B00%3A00"),
        3: (f"{CURRENT_YEAR}-07-01T23%3A59%3A59.394843%2B00%3A00", f"{CURRENT_YEAR}-09-30T23%3A59%3A59.394843%2B00%3A00"), 
        4: (f"{CURRENT_YEAR}-10-01T23%3A59%3A59.394843%2B00%3A00", f"{CURRENT_YEAR}-12-31T23%3A59%3A59.394843%2B00%3A00")
    }







def main(quarter: int, year: int, driver_id = None):
    if(year>2020):
        update_year(year)
    else:
        return pd.DataFrame
    # try:
    df_fuel = fuel_and_energy_call(int(quarter))
    data = parse_df(df_fuel, quarter, driver_id)
    final_df = write_to_csv(data)
    return final_df
    # except Exception as e:
    #     print (f"An error occurred main: {e}")

# if __name__ == "__main__":
#     main(1,2021)