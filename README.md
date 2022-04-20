## Tracks updates on f95zone!

Needs Python3. <br>
Install the requirements with ``python -m pip install -r requirements.txt``<br>
To add games for tracking, just put them in the CSV file (you can omit the updated date, it'll be filled).

```
python.exe .\main.py -h
usage: Simple Updates Tracker for f95zone [-h] [-i [INPUT]] [-o [OUTPUT]] [-c [COOKIES]] [-t [THREADS]] [--age [AGE]] [--retries [RETRIES]] [--delay [DELAY]]

Uses a simple 'tracked.csv' file to track updates.

options:
  -h, --help            show this help message and exit
  -i [INPUT], --input [INPUT]
                        Set the input file for tracked games. Default is the 'tracked.csv' in the script starting directory.
  -o [OUTPUT], --output [OUTPUT]
                        Path to output file. Default is 'output.html' in the script starting directory.
  -c [COOKIES], --cookies [COOKIES]
                        Set the cookies file for the html session. Default is the 'cookies' in the script starting directory. If no file exists, no cookie is set.
  -t [THREADS], --threads [THREADS]
                        Number of threads to use for fetching data. Default is 5.
  --age [AGE]           Minimum age (in days) to qualify for a check. The default checks all entries older than 7 days.
  --retries [RETRIES]   Max retries. Defaults to 5.
  --delay [DELAY]       Delay between retries in seconds. Defaults to 5 seconds.
  ```
