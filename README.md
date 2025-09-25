# Aruba Configuration Comparison Script

This script compares the running configuration of Aruba devices against a master template and reports any differences. It's designed to be used in CI/CD pipelines for automated configuration validation.

---
## Installation

To get started, you'll need to install the necessary Python libraries. You can do this easily using the provided `requirements.txt` file.

Run the following command in your terminal:

    pip install -r requirements.txt

---
## Usage

Here are a few tips for running the script from your command line:

* **Standard Comparison**: To run a standard comparison with detailed output, simply execute the main script.

        python main.py

* **Simplified Output**: If you only need a summary of the differences without the detailed line-by-line comparison, use the `--simplified` argument.

        python main.py --simplified

* **Getting Help**: To see all available command-line options and instructions, use the `--help` argument.

        python main.py --help

---
## How it Works

The script fetches the device configuration from Aruba Central using the API and compares it line by line against a provided template file. It uses a `diff` like approach to highlight additions and deletions.

---
## Exit Codes

The script uses the following exit codes for automation:

* **0**: Success, no differences found.
* **1**: General error (e.g., template not found).
* **2**: Authentication/Authorization Error.
* **3**: Differences found.

---
## Security

For production environments, it is strongly recommended to use a secrets manager (like AWS Secrets Manager) to store your `client_id` and `client_secret`.