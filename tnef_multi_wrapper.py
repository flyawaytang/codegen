#!/usr/bin/env python3
# TNEF Multi Wrapper - Generate multiple TNEF files with custom embedded filenames
# This script creates multiple TNEF files, each with a custom embedded file

import os
import argparse
import json
import subprocess
import tempfile
import shutil

def parse_attachment_spec(spec):
    """Parse an attachment specification in the format 'file:name'"""
    if ':' in spec:
        file_path, custom_name = spec.split(':', 1)
    else:
        file_path = spec
        custom_name = os.path.basename(file_path)
    
    return file_path, custom_name

def main():
    parser = argparse.ArgumentParser(description='Create multiple TNEF files with custom embedded filenames')
    parser.add_argument('-o', '--output-dir', default='tnef_files', help='Output directory for TNEF files (default: tnef_files)')
    
    # Multiple attachment options
    parser.add_argument('-a', '--attach', action='append', help='Attachment in format "file:name" (can be used multiple times)')
    parser.add_argument('-f', '--file', action='append', help='File to attach (can be used multiple times)')
    parser.add_argument('-n', '--name', action='append', help='Custom name for attached file (must match number of --file options)')
    parser.add_argument('-j', '--json', help='JSON file containing attachment specifications')
    
    args = parser.parse_args()
    
    attachments = []
    
    # Process --attach options
    if args.attach:
        for spec in args.attach:
            file_path, custom_name = parse_attachment_spec(spec)
            attachments.append({'file': file_path, 'name': custom_name})
    
    # Process --file and --name options
    if args.file:
        names = args.name if args.name else [None] * len(args.file)
        if len(names) < len(args.file):
            names.extend([None] * (len(args.file) - len(names)))
        
        for file_path, custom_name in zip(args.file, names):
            if custom_name is None:
                custom_name = os.path.basename(file_path)
            
            attachments.append({'file': file_path, 'name': custom_name})
    
    # Process --json option
    if args.json:
        try:
            with open(args.json, 'r') as f:
                json_data = json.load(f)
            
            for item in json_data:
                if 'file' in item and 'name' in item:
                    attachments.append({'file': item['file'], 'name': item['name']})
        except Exception as e:
            print(f"Error processing JSON file: {e}")
    
    # Check if we have any attachments
    if not attachments:
        print("Error: No attachments specified. Use --attach, --file/--name, or --json options.")
        parser.print_help()
        return
    
    # Create output directory if it doesn't exist
    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)
    
    # Create a TNEF file for each attachment
    for i, attachment in enumerate(attachments, 1):
        file_path = attachment['file']
        custom_name = attachment['name']
        output_file = os.path.join(args.output_dir, f"winmail_{i}.dat")
        
        try:
            # Call the compatible TNEF creator script
            cmd = ["python", "tnef_creator_compatible.py", "-f", custom_name, "-c", file_path, "-o", output_file]
            subprocess.run(cmd, check=True)
            print(f"Created TNEF file {output_file} with embedded file {custom_name}")
        except Exception as e:
            print(f"Error creating TNEF file for {file_path}: {e}")
    
    print(f"\nCreated {len(attachments)} TNEF files in directory: {args.output_dir}")
    print("To extract all files, run: for f in tnef_files/*.dat; do tnef --number-backups $f; done")

if __name__ == "__main__":
    main()

