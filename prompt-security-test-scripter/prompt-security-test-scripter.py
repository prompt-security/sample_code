from typing import Optional
from fastparquet import ParquetFile
import time
import pandas as pd

import httpx
import json
import asyncio
import openai
import sys
import csv

def main():
    filename = None
    outputfile = None
    appid = None
    if '-f' in sys.argv:
        try:
            filename = sys.argv[sys.argv.index('-f') + 1]
        except:
            pass

    if '-o' in sys.argv:
        try:
            outputfile = sys.argv[sys.argv.index('-o') + 1]
        except:
            pass

    if '-a' in sys.argv:
        try:
            appid = sys.argv[sys.argv.index('-a') + 1]
        except:
            pass
            
    if not filename or not outputfile:
        print("Usage: python scriptname.py -f <inputfile> -o <outputfile>")
        sys.exit(1)

    print(f"Input Filename: {filename}")
    print(f"Output Filename: {outputfile}")

    true_positive = 0
    true_negative = 0
    false_positive = 0
    false_negative = 0

    if not filename.lower().endswith('.csv') and not filename.lower().endswith('.parquet'):
        print("Error: input file must be a CSV or parquet.")
        sys.exit(1)

    with open(outputfile, 'w') as output_file:
        csvwriter = csv.writer(output_file, delimiter=",", quotechar='"', quoting=csv.QUOTE_MINIMAL)
        csvwriter.writerow(['Expected Result','Expected Result (text)','Action','User Prompt','Modified Prompt','Violations','Sensitive Data Object'])
        if filename.lower().endswith('.csv'):
            with open(filename, "r", newline='') as infile:
                reader = csv.reader(infile)
                for row in reader:
                    user_prompt = row[0]
                    system_prompt = ""
                    expected_result = row[1]
                    expected_result_text = ""
                    if(expected_result != 1 and expected_result != 0):
                        expected_result_text = expected_result
                    elif(expected_result == 1):
                        expected_result_text = "fail"
                    else:
                        expected_result_text = "pass"
                    # Scan user prompt with Prompt Security
                    true_positive, true_negative, false_positive, false_negative = process_prompt_results(appid, csvwriter, user_prompt, system_prompt, expected_result, expected_result_text, true_positive, true_negative, false_negative, false_positive)
                    time.sleep(0.1)
        elif filename.lower().endswith('.parquet'):
            try:
                # Read the Parquet file into a DataFrame
                df = pd.read_parquet(filename)
            except Exception as e:
                print(f"Error reading the Parquet file: {e}")
                sys.exit(1)

            df = df.sample(50)
            with open("sampleprompts", "wb") as f:
                f.write(df.to_csv(index=False).encode())
            #df = df.iloc[300:400]
            # Iterate over each row in the DataFrame and print it
            for index, row in df.iterrows():
                user_prompt = row['prompt']
                system_prompt = ""
                expected_result = row['label']
                expected_result_text = ""
                if(expected_result != 1 and expected_result != 0):
                    expected_result_text = expected_result
                elif(expected_result == 1):
                    expected_result_text = "fail"
                else:
                    expected_result_text = "pass"
                # Scan user prompt with Prompt Security
                true_positive, true_negative, false_positive, false_negative = process_prompt_results(appid, csvwriter, user_prompt, system_prompt, expected_result, expected_result_text, true_positive, true_negative, false_negative, false_positive)


    print("Final Results:")
    print("True Positive: " + str(true_positive))
    print("True Negative: " + str(true_negative))
    print("False Positive: " + str(false_positive))
    print("False Negative: " + str(false_negative))

    output_file.close()

def process_prompt_results(appid, csvwriter, user_prompt, system_prompt, expected_result, expected_result_text, true_positive, true_negative, false_negative, false_positive):
    ps_ret = ps_protect_api_async(appid, user_prompt, system_prompt, None, 'user@domain.com')
    print("user_prompt= " + user_prompt + "; action = " + ps_ret["result"]["prompt"]["action"] )
    sensitive_data = ""
    modified_text = ""
    if "Sensitive Data" in ps_ret["result"]["prompt"]["findings"]:
        sensitive_data = ps_ret["result"]["prompt"]["findings"]["Sensitive Data"]
    if "modified_text" in ps_ret["result"]["prompt"]:
        modified_text = ps_ret["result"]["prompt"]["modified_text"]
    csvwriter.writerow([expected_result,expected_result_text,ps_ret['result']['prompt']['action'],user_prompt,modified_text,json.dumps(ps_ret['result']['prompt']['violations']),json.dumps(sensitive_data)])
    if ps_ret["result"]["prompt"]["action"] == "log":
        if expected_result_text == "pass":
            true_negative += 1
        else:
            false_negative += 1
    else:
        if expected_result_text == "pass":
            false_positive += 1
        else:
            true_positive += 1
    return true_positive,true_negative,false_positive,false_negative

def ps_protect_api_async(appid: str, prompt: str, system_prompt: Optional[str] = None, response: Optional[str] = None, user: Optional[str] = None):
    headers = {
        'APP-ID': appid,
        'Content-Type': 'application/json'
    }
    payload = {
        'prompt': prompt,
        'system_prompt': system_prompt,
        'response': response,
        'user': user
    }
    with httpx.Client() as client:
        ret = client.post('https://useast.prompt.security/api/protect', headers=headers, json=payload)
        return ret.json()




if __name__ == "__main__":
    main()
