#!/usr/bin/python3
from gobgp_client_mod import *
import ijson
import argparse
import logging

def run():
    # Add CLI arguments
    parser = argparse.ArgumentParser(description="GoBGP client", usage="--help to list available commands")
    parser.add_argument("--json_rib", type=str, nargs="+", help="name of json files with BGP updates to send", required=True)
    parser.add_argument("--num_prefixes", type=int, help="Number of prefixes to send across all files")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO,format='%(levelname)s :: %(asctime)s :: %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')

    # Establish GoBGP API client connection to local GoBGP instance
    goBgpClient = GoBgpGo("localhost", 50051)
    
    # counters & break outer loop flag
    total_pfxs, sent_pfxs = 0, 0
    break_out = False

    # Process RIB files & send updates
    for rib in args.json_rib:
        if break_out:
            break
        logging.info(msg="Processing rib file {}".format(rib))
        try:
            rib_file = open(rib, "rb")
        except Exception as e:
            logging.warning(msg="Failed to open rib file {} {}".format(rib, e))
            continue
        for entry in ijson.items(rib_file, "item"):
            for pfx, paths in entry.items():
                total_pfxs += 1
                for path in paths:
                    try:
                        goBgpClient.send_update(pfx, path)
                        sent_pfxs += 1
                    except Exception as e:
                        logging.warning("Failed to send update for {} {}".format(pfx, e))   
            if args.num_prefixes is not None and total_pfxs >= args.num_prefixes:
                break_out = True
                break 
        rib_file.close()
    
    logging.info("Sent {:,} prefixes out of a total of {:,} expected prefixes".format(sent_pfxs, total_pfxs))
if __name__ == '__main__':
    run()
