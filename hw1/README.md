Log Analyzer v. 0.0.1
=====================

This script is analysing ngnix log file and then make the report. 
-----------------------------------------------------------------

### Default arguments:

* *"REPORT_SIZE": 1000*
    The number of lines who write to report with maximum time execution

* *"REPORT_DIR": "./reports"*
    Folder with final reports

* *"LOG_DIR": "./log"*
    Folder with log files

### Options:
The program can specify where the configuration file in **[json format](https://en.wikipedia.org/wiki/JSON)** is located to override certain parameters. If there is no such option, the program looks for the configuration file in the working folder.
    *'--config', '-c' - './config.json'*

### Содержимое файла config.json:

```javascript
{
    "REPORT_SIZE": 1000,
    "REPORT_DIR": "./reports",
    "LOG_DIR": "./log",
    "TS_FILE": "log_analyzer.ts",
    "SCRIPT_LOG": "log_analyzer.log"
}
```

#### There are additional options:
* *"TS_FILE": "log_analyzer.ts"*
    Path to *timestamp* file
* *"SCRIPT_LOG": "log_analyzer.log"*
    Path to working *log file*

How to run
----------
*python log_analyzer.py*

**OR**

*python log_analyzer.py --config <your_config_file_name.json>*

**SIMPLER**

*python log_analyzer.py -c <your_config_file_name.json>*