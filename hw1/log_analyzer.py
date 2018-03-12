#!/usr/bin/env python
# -*- coding: utf-8 -*-


# log_format ui_short '$remote_addr $remote_user $http_x_real_ip [$time_local] "$request" '
#                     '$status $body_bytes_sent "$http_referer" '
#                     '"$http_user_agent" "$http_x_forwarded_for" "$http_X_REQUEST_ID" "$http_X_RB_USER" '
#                     '$request_time';

import re, argparse, logging, os, gzip, itertools, json, inspect
from datetime import date, datetime
from string import Template

config = {
    "REPORT_SIZE": 1000,
    "REPORT_DIR": "./reports",
    "LOG_DIR": "./log",
}

Logger = logging.getLogger(__name__)

# Definition arguments and write config
def ParseArguments():
    try:
        p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
        p.add_argument("--config", "-c", default='./config.json', help="Please typing path to config file")
        args = p.parse_args()
        Logger.info("Arguments succefully parsed!")
    except:
        Logger.exception("Undefined error to parse arguments!")
    return args

def LoadConfig(PATH_TO_CONFIG_FILE):
    try:
        with open(PATH_TO_CONFIG_FILE, 'rb') as js:
            loaded_config = json.load(js)
            config.update(loaded_config)
        if config.get("SCRIPT_LOG") is None:
            config["SCRIPT_LOG"] = None
        logging.basicConfig(filename=config["SCRIPT_LOG"], level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s',datefmt='%Y.%m.%d %H:%M:%S')
        Logger.info("Config file is successfully updated!")
        return config
    except:
        Logger.exception("Doesn't correct config file!")

# Open&Collect, Parsing functions
def openLog(f):
    try:
        if f[-2:] == 'gz':
            return gzip.open(f, 'rb')
        return open(f, 'rb')
    except:
        Logger.exception("Opener error!")

def CollectLines(input_file):
    all_lines = float(sum(1 for line in openLog(input_file)))
    parse_error_threshold = 0.5
    parse_error, line_count = 0.0, 0.0
    with openLog(input_file) as handle:
        log_dict = {}
        for line in handle:
            line_count += 1.0
            url, rqst = ParseLog(line)
            if url == 1 and rqst == 1:
                parse_error += 1.0
            if parse_error / all_lines >= parse_error_threshold:
                processed_lines = line_count / all_lines
                Logger.error("The relative threshold of parsing errors is exceeded! Percent of processed lines: {}. Exit.".format(processed_lines))
                exit(0)
            if log_dict.get(url) is None: log_dict[url] = []
            log_dict[url].append(float(rqst))
    return log_dict, all_lines

def parseLogFilesList(LOG_DIR, REPORT_DIR):
    file_list_dict = {}
    last_report_date = CheckReportExistance(REPORT_DIR)
    re_string = re.compile("(?P<file>nginx-access-ui\.log-(?P<year>[0-9]{4})(?P<month>0[1-9]|1[1,2])(?P<day>[0-2][1-9]|3[0-1])(\.gz|))")
    for f in os.listdir(LOG_DIR):
        m = re_string.match(f)
        if m is not None:
            file_list_dict[m.group("file")] = date(int(m.group("year")), int(m.group("month")), int(m.group("day")))
    if len(file_list_dict) == 0:
        Logger.info("No logs for work. Exit.")
        exit(0)
    else:
        last_date = max([v for k, v in file_list_dict.items()])
        if last_report_date == last_date:
            Logger.info("Log is already prepaired. Exit.")
            exit(0)
        else:
            input_file = [k for k, v in file_list_dict.items() if v == last_date][0]
            input_file = os.path.join(LOG_DIR, input_file)
            Logger.info("The file '{}' for processing was successfully found.".format(input_file))
            return input_file, last_date

def CheckReportExistance(REPORT_DIR):
    try:
        report_list_dict = {}
        re_string = re.compile("(?P<filename>report-(?P<year>[0-9]{4}).(?P<month>0[1-9]|1[1,2]).(?P<day>[0-2][1-9]|3[0-1])\.html)")
        for l in os.listdir(REPORT_DIR):
            m = re_string.match(l)
            if m is not None:
                report_list_dict[m.group("filename")] = date(int(m.group("year")), int(m.group("month")), int(m.group("day")))
        if len(report_list_dict) == 0:
            last_report_date = None
            Logger.info("I didn't find the latest report.")
        else:
            last_report_date = max([v for k, v in report_list_dict.items()])
            Logger.info("Report found. The date of the report is {}.".format(last_report_date))
        return last_report_date
    except:
        Logger.exception("Undefined error in function {}".format(inspect.stack()[0][3]))

def ParseLog(line):
    try:
        line = re.split('\"', line[:-2])
        url, rqst = line[1].split(" ")[1], line[12][1:]
    except:
        url, rqst = 1, 1
    return url, rqst

# Statistics functions
def median(numbers):
    try:
        numbers = sorted(numbers)
        center = len(numbers) / 2
        if len(numbers) % 2 == 0:
            return sum(numbers[center - 1:center + 1]) / 2.0
        else:
            return numbers[center]
    except:
        Logger.exception("Undefined error in function {}".format(inspect.stack()[0][3]))

def mean(numbers):
    try:
        return float(sum(numbers)) / max(len(numbers), 1)
    except:
        Logger.exception("Undefined error in function {}".format(inspect.stack()[0][3]))

# Report generators
def MakeTableJson(LOG_DIR, REPORT_DIR):
    input_file, last_date = parseLogFilesList(LOG_DIR, REPORT_DIR)
    if input_file is None or last_date is None:
        Logger.info("No file for processing. Exit.")
        exit(0)
    log_dict, all_lines = CollectLines(input_file)
    sum_rqst = sum(list(itertools.chain(*[v for k, v in log_dict.items()])))
    table_json = []
    for url, rqst in log_dict.items():
        table_json.append({
            "count": len(rqst), 
            "time_avg": round(mean(rqst), 3), 
            "time_max": round(max(rqst), 3), 
            "time_sum": round(sum(rqst), 3), 
            "url": url, 
            "time_med": round(median(rqst), 3), 
            "time_perc": round((float(sum(rqst)) / sum_rqst) * 100, 3), 
            "count_perc": round((float(len(rqst)) / all_lines) * 100, 3)})
    table_json = sorted(table_json, key=lambda k: k['time_sum'], reverse=True)[:config['REPORT_SIZE']]
    return table_json, last_date

def WriteReport(table_json, last_date):
    try:
        if os.path.exists('report.html') and os.path.isfile('report.html'):
            with open('report.html', 'rb') as handle:
                template_file_in_string = Template(handle.read()).safe_substitute(table_json = table_json)
                time_stamp = last_date.__format__('%Y.%m.%d')
                report_file_name = os.path.join(config["REPORT_DIR"],"report-{}.html".format(time_stamp))
                with open(report_file_name, 'wb') as out_file:
                    out_file.write(template_file_in_string)
        else:
            Logger.error("Template file is absent!")
            exit(0)
    except:
        Logger.exception("Input/Output error")

def SuccessReport():
    path_to_ts = "/var/tmp/log_analyzer.ts"
    if config.get("TS_FILE") is not None:
        if not os.path.exists(os.path.dirname(config.get("TS_FILE"))): os.path.makedirs(os.path.dirname(config.get("TS_FILE")))
        path_to_ts = config["TS_FILE"]
    with open(path_to_ts, "a") as ts:
        ts.write(datetime.now().__format__("%Y.%m.%d %X") + "\n")

def main(args):
    config = LoadConfig(args.config)
    table_json, last_date = MakeTableJson(config["LOG_DIR"], config["REPORT_DIR"])
    if table_json is None or last_date is None:
        Logger.info("No file for processing. Exit.")
        exit(0)
    WriteReport(table_json, last_date)
    Logger.info("The log file was successfully processed.")
    SuccessReport()

if __name__ == "__main__":
    args = ParseArguments()
    main(args)