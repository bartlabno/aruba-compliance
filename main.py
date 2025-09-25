import argparse
import json
import sys
import re
import difflib
import os
import fnmatch
from aruba_central_api import ArubaCentralAPI

__version__ = "0.1-alpha"

# ANSI color codes for pretty printing
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    ENDC = '\033[0m'

def apply_exemptions(config_list, exemption_rules):
    """
    Parses a list of config lines and removes items based on exemption rules.
    - If a block header pattern has a value of "*", the entire block is removed.
    - If a block header pattern has a list of line patterns, only those lines
      within the block are removed. Supports wildcards.
    """
    if not isinstance(config_list, list) or not isinstance(exemption_rules, dict):
        return config_list

    filtered_config = []
    in_fully_exempt_block = False
    current_line_exemptions = []

    for line in config_list:
        # If we are inside a block that should be fully ignored
        if in_fully_exempt_block:
            if line.strip() == "!":
                in_fully_exempt_block = False
            continue  # Skip this line

        # Check if the current line is a block header (no leading whitespace)
        is_header = not line.startswith(' ')
        if is_header:
            # We've started a new block, so reset the line-level exemptions
            current_line_exemptions = []
            # Check if this new block matches any exemption rule
            for block_pattern, rules in exemption_rules.items():
                if fnmatch.fnmatch(line, block_pattern):
                    if rules == "*":
                        # This block should be fully exempted.
                        in_fully_exempt_block = True
                    elif isinstance(rules, list):
                        # This block has specific line exemptions.
                        current_line_exemptions = rules
                    break  # Found the matching rule for this block, no need to check others
            
            if in_fully_exempt_block:
                continue # Skip the header line of the fully exempt block

        # Now, check if the current line should be exempted based on line-level rules
        is_line_exempt = False
        if current_line_exemptions:
            for line_pattern in current_line_exemptions:
                if fnmatch.fnmatch(line.strip(), line_pattern):
                    is_line_exempt = True
                    break
        
        if is_line_exempt:
            continue # Skip this specific line

        # If the line has survived all checks, add it to the final config
        filtered_config.append(line)

    return filtered_config

def compare_configs(config_a, config_b, simplified=False, from_file='template.json', to_file='live_config.json'):
    """
    Compares two configurations and prints the differences with colors.
    Returns True if different, False otherwise.
    """
    if config_a == config_b:
        print(f"{Colors.GREEN}✅ Configurations match.{Colors.ENDC}")
        return False

    print(f"{Colors.RED}❌ Configurations do not match.{Colors.ENDC}")
    
    config_a_str = json.dumps(config_a, indent=2, sort_keys=True).splitlines()
    config_b_str = json.dumps(config_b, indent=2, sort_keys=True).splitlines()
    diff = list(difflib.unified_diff(config_a_str, config_b_str, fromfile=from_file, tofile=to_file, lineterm=''))
    
    additions = sum(1 for line in diff if line.startswith('+') and not line.startswith('+++'))
    removals = sum(1 for line in diff if line.startswith('-') and not line.startswith('---'))

    if not simplified:
        print(f"{Colors.CYAN}List of detailed differences:{Colors.ENDC}")
        for line in diff:
            if line.startswith('+'):
                print(f"{Colors.GREEN}{line}{Colors.ENDC}")
            elif line.startswith('-'):
                print(f"{Colors.RED}{line}{Colors.ENDC}")
            elif line.startswith('@@'):
                print(f"{Colors.CYAN}{line}{Colors.ENDC}")
            else:
                print(line)
    
    print("\n" + "="*40)
    print(f"{Colors.BOLD}Summary of differences:{Colors.ENDC}")
    print(f"  Lines added:    {Colors.GREEN}{additions}{Colors.ENDC}")
    print(f"  Lines removed:  {Colors.RED}{removals}{Colors.ENDC}")
    print("="*40)

    return True

def validate_mac_address(mac):
    """Custom argparse type for validating a MAC address."""
    if not re.match(r'^([0-9a-fA-F]{2}([:\-]?)){5}[0-9a-fA-F]{2}$|^[0-9a-fA-F]{12}$', mac):
        raise argparse.ArgumentTypeError(f"'{mac}' is not a valid MAC address format.")
    return mac

def main():
    """Main function to run the configuration comparison."""
    parser = argparse.ArgumentParser(
        description="Compare Aruba Central configuration against a template or a previous snapshot.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument('--version', action='version', version=f'%(prog)s {__version__}')
    parser.add_argument('--template', default='template.json', help='Path to the master template file (default: template.json)')
    parser.add_argument('--group-name', help='Name of the Aruba Central group to check. Overrides ARUBA_GROUP_NAME from .env file.')
    parser.add_argument('--previous-config', help='Path to a previously saved config file to compare against. Overrides --template.')
    parser.add_argument('--save-config', help='Path to save the fetched live configuration to a file.')
    parser.add_argument('--simplified', action='store_true', help='Show a simplified output, only indicating if there is a difference.')
    parser.add_argument('--mac-address', type=validate_mac_address, help="MAC address of a specific device to check for local overrides.")
    parser.add_argument(
        '--exemptions',
        help='Path to a JSON file containing exemption rules.'
    )
    parser.add_argument('--no-color', action='store_true', help='Disable colorized output.')

    args = parser.parse_args()

    if args.no_color:
        Colors.GREEN = ''
        Colors.RED = ''
        Colors.CYAN = ''
        Colors.BOLD = ''
        Colors.ENDC = ''

    config_to_compare = None
    from_filename = args.template

    if args.previous_config:
        from_filename = args.previous_config
        try:
            with open(args.previous_config, 'r') as f:
                config_to_compare = json.load(f)
            print(f"Loaded previous configuration from '{args.previous_config}' for comparison.")
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error loading previous config '{args.previous_config}': {e}", file=sys.stderr)
            sys.exit(1)
    else:
        if not args.save_config or args.previous_config:
            try:
                with open(args.template, 'r') as f:
                    config_to_compare = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError) as e:
                print(f"Error loading template '{args.template}': {e}", file=sys.stderr)
                sys.exit(1)

    try:
        api = ArubaCentralAPI(group_name=args.group_name)
        live_config = None
        if args.mac_address:
            live_config = api.get_device_override_config(args.mac_address)
        else:
            live_config = api.get_group_level_config()

        if live_config is None:
            print("\nError: Failed to fetch the live configuration from Aruba Central.", file=sys.stderr)
            sys.exit(1)

        # If an exemption file is provided, apply the rules
        if args.exemptions:
            try:
                with open(args.exemptions, 'r') as f:
                    exemption_rules = json.load(f)
                print(f"Applying exemption rules from '{args.exemptions}'...")
                
                if config_to_compare and 'config' in config_to_compare:
                    config_to_compare['config'] = apply_exemptions(config_to_compare['config'], exemption_rules)
                
                if 'config' in live_config:
                    live_config['config'] = apply_exemptions(live_config['config'], exemption_rules)

            except (FileNotFoundError, json.JSONDecodeError) as e:
                print(f"Error loading exemption file '{args.exemptions}': {e}", file=sys.stderr)
                sys.exit(1)

        if args.save_config:
            try:
                with open(args.save_config, 'w') as f:
                    json.dump(live_config, f, indent=2, sort_keys=True)
                print(f"Successfully saved live configuration to '{args.save_config}'")
                if not args.previous_config and not os.path.exists(args.template):
                    sys.exit(0)
            except IOError as e:
                print(f"Error writing to file '{args.save_config}': {e}", file=sys.stderr)
        
        if config_to_compare is None:
            print("No template or previous config to compare against. Exiting.")
            sys.exit(0)

        if compare_configs(config_to_compare, live_config, args.simplified, from_file=from_filename):
            sys.exit(3)
        else:
            sys.exit(0)

    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()

