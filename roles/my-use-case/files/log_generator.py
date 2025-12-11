import os
import time
import datetime

def append_to_log_file(log_directory, log_filename="customlogsource.log.txt"):
    os.makedirs(log_directory, exist_ok=True)
    log_filepath = os.path.join(log_directory, log_filename)

    while True:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entries = [
            f"{timestamp} - INFO: This is an info log entry.",
            f"{timestamp} - WARNING: This is a warning log entry.",
            f"{timestamp} - ERROR: This is an error log entry."
        ]

        with open(log_filepath, 'a') as log_file:
            for entry in log_entries:
                log_file.write(entry + "\n")

        print(f"Appended log entries to: {log_filepath}")
        time.sleep(10)

if __name__ == "__main__":
    log_directory = os.path.expanduser("/home/dt_training/logs/")
    append_to_log_file(log_directory)