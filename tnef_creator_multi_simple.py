#!/usr/bin/env python3
# TNEF Creator Multi Simple - Generate TNEF files with multiple custom embedded filenames
# This script creates a TNEF file (winmail.dat) with multiple custom embedded files
# Uses a simpler approach to ensure compatibility with standard TNEF extraction tools

import struct
import os
import argparse
import random
import time
import datetime
import binascii
import json
import tempfile
import subprocess

def parse_attachment_spec(spec):
    """Parse an attachment specification in the format 'file:name'"""
    if ':' in spec:
        file_path, custom_name = spec.split(':', 1)
    else:
        file_path = spec
        custom_name = os.path.basename(file_path)
    
    return file_path, custom_name

def create_tnef_with_single_file(output_file, filename, content):
    """Create a TNEF file with a single embedded file using the compatible script"""
    # Create a temporary file for the content
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        temp_file.write(content)
        temp_path = temp_file.name
    
    try:
        # Call the compatible TNEF creator script
        cmd = ["python", "tnef_creator_compatible.py", "-f", filename, "-c", temp_path, "-o", output_file]
        subprocess.run(cmd, check=True, capture_output=True)
    finally:
        # Clean up the temporary file
        os.unlink(temp_path)
    
    return output_file

def main():
    parser = argparse.ArgumentParser(description='Create a TNEF file with multiple custom embedded files')
    parser.add_argument('-o', '--output-dir', default='.', help='Output directory for TNEF files (default: current directory)')
    parser.add_argument('-p', '--prefix', default='winmail', help='Prefix for output TNEF files (default: winmail)')
    
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
            try:
                with open(file_path, 'rb') as f:
                    content = f.read()
                attachments.append({'filename': custom_name, 'content': content})
            except Exception as e:
                print(f"Error reading file {file_path}: {e}")
    
    # Process --file and --name options
    if args.file:
        names = args.name if args.name else [None] * len(args.file)
        if len(names) < len(args.file):
            names.extend([None] * (len(args.file) - len(names)))
        
        for file_path, custom_name in zip(args.file, names):
            if custom_name is None:
                custom_name = os.path.basename(file_path)
            
            try:
                with open(file_path, 'rb') as f:
                    content = f.read()
                attachments.append({'filename': custom_name, 'content': content})
            except Exception as e:
                print(f"Error reading file {file_path}: {e}")
    
    # Process --json option
    if args.json:
        try:
            with open(args.json, 'r') as f:
                json_data = json.load(f)
            
            for item in json_data:
                if 'file' in item and 'name' in item:
                    try:
                        with open(item['file'], 'rb') as f:
                            content = f.read()
                        attachments.append({'filename': item['name'], 'content': content})
                    except Exception as e:
                        print(f"Error reading file {item['file']}: {e}")
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
    tnef_files = []
    for i, attachment in enumerate(attachments, 1):
        output_file = os.path.join(args.output_dir, f"{args.prefix}_{i}.dat")
        create_tnef_with_single_file(output_file, attachment['filename'], attachment['content'])
        tnef_files.append(output_file)
        print(f"Created TNEF file {output_file} with embedded file {attachment['filename']}")
    
    print(f"\nCreated {len(attachments)} TNEF files in directory: {args.output_dir}")
    print("To extract all files, run: for f in *.dat; do tnef --number-backups $f; done")
    
    # Create a batch file for extracting all TNEF files
    batch_file = os.path.join(args.output_dir, "extract_all.sh")
    with open(batch_file, 'w') as f:
        f.write("#!/bin/bash\n")
        f.write("# Extract all TNEF files\n")
        for tnef_file in tnef_files:
            f.write(f"tnef --number-backups {os.path.basename(tnef_file)}\n")
    
    os.chmod(batch_file, 0o755)
    print(f"Created extraction script: {batch_file}")

if __name__ == "__main__":
    main()

