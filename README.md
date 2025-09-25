# Aruba Configuration Comparison Script

This script compares the running configuration of Aruba devices against a master template and reports any differences. It's designed to be used in CI/CD pipelines for automated configuration validation.

---
## Setup and Configuration

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/bartlabno/aruba-compliance.git
    cd aruba-compliance
    ```

2.  **Set up Python Environment:**
    ```bash
    cd scripts
    pip install -r requirements.txt
    cd ..
    ```

3.  **Configure Aruba Central API Credentials:**
    * Rename `example.env` to `.env`.
    * Populate `.env` with your Aruba Central API `ARUBA_BASE_URL`, `ARUBA_CLIENT_ID`, `ARUBA_CLIENT_SECRET`, and optionally `ARUBA_GROUP_NAME`.

4.  **Create Golden Templates:**
    * Place your desired "golden" configuration files (in JSON format, mirroring the Aruba Central API output structure) into the `templates/` directory. For example, `templates/Gateway-A.json`.

5.  **Define Exemption Rules (Optional):**
    * Create or update `exemptions.json` at the root of the project.
    * The `exemptions.json` should be a JSON object where keys are configuration block patterns (supporting wildcards like `*`) and values are either:
        * `"*"`: To exempt the entire block.
        * `["line pattern 1*", "line pattern 2*"]`: To exempt specific lines within that block (also supports wildcards).

    **Example `exemptions.json`:**
    ```json
    {
      "ip access-list session global_acl*": [
        "   permit ip any any any log",
        "   permit tcp any any any dst-port 443"
      ],
      "interface gigabitethernet 0/0/0": [
        "   ip address 10.0.0.1 255.255.255.0",
        "   description Link to ISP"
      ],
      "username admin*": "*"
    }
    ```

## Usage

The `main.py` script can be run directly for individual comparisons or snapshotting.

```bash
python3 scripts/main.py --help
```

## Common main.py Arguments:
`--template TEMPLATE_FILE`: Path to the master template JSON file for comparison (default: template.json).

`--group-name GROUP_NAME`: Name of the Aruba Central group to check. Overrides ARUBA_GROUP_NAME from .env.

`--mac-address MAC_ADDRESS`: MAC address of a specific device to check for local overrides. (e.g., 00:1A:2B:3C:4D:5E).

`--previous-config PREV_CONFIG_FILE`: Path to a previously saved config file to compare against. Overrides --template.

`--save-config SAVE_FILE`: Path to save the fetched live configuration to a file (e.g., config_snapshots/my_group.json).

`--exemptions EXEMPTIONS_FILE`: Path to a JSON file containing exemption rules (e.g., exemptions.json).

`--simplified`: Show a simplified output, only indicating if there is a difference.

`--no-color`: Disable colorized output in the terminal.

---
## Examples
- Compare group "MyBranch" against `Gateway-A.json` template:
```Bash
python3 scripts/main.py --group-name "MyBranch" --template templates/Gateway-A.json
````

- Compare a specific device (MAC address) against its Data-Center.json template:
```Bash
python3 scripts/main.py --group-name "DataCenter" --mac-address "00:1A:2B:3C:4D:5E" --template templates/Data-Center.json
```

- Save the live configuration of group "MyBranch" to a snapshot file:
```Bash
python3 scripts/main.py --group-name "MyBranch" --save-config config_snapshots/MyBranch.json
```
- Compare group "MyBranch" against its previous snapshot with exemptions and simplified output:

```Bash
python3 scripts/main.py --group-name "MyBranch" --previous-config config_snapshots/MyBranch.json --exemptions exemptions.json --simplified
```

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

---
## Contributing
Feel free to open issues or pull requests to improve this automation.