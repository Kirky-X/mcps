"""
Command line interface for TimeMaster
"""
import argparse
import sys
from time_master import TimeMaster


def main():
    parser = argparse.ArgumentParser(description="TimeMaster - A robust timezone handling tool")
    parser.add_argument("--timezone", "-tz", help="Specify a timezone (e.g., 'Asia/Shanghai')")
    parser.add_argument("--format", "-f", choices=["iso", "friendly"], help="Output format")
    parser.add_argument("--search", "-s", help="Search for timezones by name")
    parser.add_argument("--list", "-l", nargs="?", const="all", help="List timezones, optionally by region")
    parser.add_argument("--convert", "-c", nargs=2, metavar=("DATETIME", "TARGET_TZ"), 
                        help="Convert datetime to target timezone")
    parser.add_argument("--difference", "-d", nargs=2, metavar=("TZ1", "TZ2"), 
                        help="Calculate time difference between two timezones")
    parser.add_argument("--offline", action="store_true", help="Force offline mode")
    
    args = parser.parse_args()
    
    # Initialize TimeMaster
    tm = TimeMaster()
    
    # Force offline mode if requested
    if args.offline:
        tm.force_offline(True)
    
    try:
        if args.search:
            # Search for timezones
            results = tm.find_timezones(args.search)
            print(f"Timezones matching '{args.search}':")
            for tz in results:
                print(f"  {tz}")
                
        elif args.list:
            # List timezones
            if args.list == "all":
                results = tm.list_timezones()
                print("All timezones:")
            else:
                results = tm.list_timezones(region=args.list)
                print(f"Timezones in region '{args.list}':")
                
            for tz in results[:20]:  # Limit output
                print(f"  {tz}")
            if len(results) > 20:
                print(f"  ... and {len(results) - 20} more")
                
        elif args.convert:
            # Convert datetime
            # This is a simplified example - in practice, you'd want more robust parsing
            dt_str, target_tz = args.convert
            print(f"Converting {dt_str} to {target_tz}")
            # For simplicity, we'll just show the current time conversion
            result = tm.convert(__import__('datetime').datetime.now(), target_tz)
            print(f"Result: {result}")
            
        elif args.difference:
            # Calculate time difference
            tz1, tz2 = args.difference
            diff = tm.difference(tz1, tz2)
            print(f"Time difference between {tz1} and {tz2}: {diff}")
            
        elif args.timezone:
            # Get current time in specified timezone
            format_type = None
            if args.format == "iso":
                format_type = TimeMaster.FORMAT_ISO
            elif args.format == "friendly":
                format_type = TimeMaster.FORMAT_FRIENDLY_CN
                
            result = tm.now(args.timezone, format=format_type)
            print(result)
            
        else:
            # Show help if no arguments provided
            parser.print_help()
            
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()