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
    "TS_FILE": "/var/tmp/log_analyzer.ts",
    "ERR_THRS": 1000
}

Logger = logging.getLogger(__name__)

# Definition arguments and write config
def parse_arguments():
    try:
        p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
        p.add_argument("--config", "-c", default='./config.json', help="Please typing path to config file")
        args = p.parse_args()
        Logger.info("Arguments succefully parsed!")
    except:
        Logger.exception("Undefined error to parse arguments!")
    return args

def load_config(PATH_TO_CONFIG_FILE):
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
def open_log(f):
    try:
        if f.endswith('gz'):
            return gzip.open(f, 'rb')
        return open(f, 'rb')
    except:
        Logger.exception("Opener error!")

def collect_lines(input_file):
    parse_error, line_count = 0, 0
    with open_log(input_file) as handle:
        log_dict = {}
        for line in handle:
            line_count += 1
            result = parse_logs_line(line)
            if result is None:
                parse_error += 1
            if parse_error >= config["ERR_THRS"]:
                Logger.error("The threshold of parsing errors is exceeded! Numbers of processed lines: {}. Exit.".format(line_count))
                exit(0)
            if log_dict.get(result[0]) is None: log_dict[result[0]] = []
            log_dict[result[0]].append(float(result[1]))
    return log_dict, line_count

def select_log_file(LOG_DIR, REPORT_DIR):
    file_list_dict = {}
    last_report_date = check_report_existance(REPORT_DIR)
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

def check_report_existance(REPORT_DIR):
    try:
        report_list_dict = {}
        re_string = re.compile("(?P<filename>report-(?P<year>[0-9]{4}).(?P<month>0[1-9]|1[1,2]).(?P<day>[0-2][1-9]|3[0-1])\.html)")
        if os.path.exists(REPORT_DIR):
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
        os.path.makedirs(REPORT_DIR)
        return None
    except:
        Logger.exception("Undefined error in function {}".format(inspect.stack()[0][3]))

def parse_logs_line(line):
    line = re.split('\"', line)
    url_expr = re.compile("(GET|POST) (?P<url>.*)")
    time_rqst_expr = re.compile(" (?P<time_rqst>[0-9].*\.[0-9]{3})")
    parse_result = []
    for element in line:
        url_m = url_expr.match(element)
        time_rqst_m = time_rqst_expr.match(element)
        if url_m is not None:
            parse_result.append(url_m.group("url"))
        if time_rqst_m is not None:
            parse_result.append(time_rqst_m.group("time_rqst"))
    if len(parse_result) == 2:
        return tuple(parse_result)
    return None

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
def make_log_table(LOG_DIR, REPORT_DIR):
    input_file, last_date = select_log_file(LOG_DIR, REPORT_DIR)
    if input_file is None or last_date is None:
        Logger.info("No file for processing. Exit.")
        exit(0)
    log_dict, all_lines = collect_lines(input_file)
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
            "time_perc": round((float(sum(rqst)) / float(sum_rqst)) * 100, 3), 
            "count_perc": round((float(len(rqst)) / float(all_lines)) * 100, 3)})
    table_json = sorted(table_json, key=lambda k: k['time_sum'], reverse=True)[:config['REPORT_SIZE']]
    return table_json, last_date

def write_report(table_json, last_date):
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

def make_success_report():
    try:
        if not os.path.exists(os.path.dirname(config.get("TS_FILE"))):
            os.path.makedirs(os.path.dirname(config.get("TS_FILE")))
        with open(config.get("TS_FILE"), "a") as ts:
            ts.write(datetime.now().__format__("%Y.%m.%d %X") + "\n")
    except:
        Logger.exception("Undefined error in function {}".format(inspect.stack()[0][3]))

def main(args):
    config = load_config(args.config)
    table_json, last_date = make_log_table(config["LOG_DIR"], config["REPORT_DIR"])
    if table_json is None or last_date is None:
        Logger.info("No file for processing. Exit.")
        exit(0)
    write_report(table_json, last_date)
    Logger.info("The log file was successfully processed.")
    make_success_report()

if __name__ == "__main__":
    args = parse_arguments()
    main(args)