import pandas as pd

url = "https://data.gov.tw/en/datasets/81180"

# Better: download the CSV from the page and save it as:
# taiwan_patent_raw.csv

df = pd.read_csv("taiwan_patent_raw.csv", encoding="big5")

print(df.columns)
print(df.head())
print(df.tail())