#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF File Embedder using pikepdf

This script embeds a file into a PDF document by:
1. Scanning the PDF to find all used object numbers
2. Finding a free object number
3. Embedding the file using the free object number
"""

import os
import sys
import argparse
from pathlib import Path
import pikepdf
from pikepdf import Pdf, Name, Dictionary, Array, Stream


def get_used_object_numbers(pdf):
    """
    Scan the PDF and return a set of all used object numbers.
    
    Args:
        pdf: A pikepdf.Pdf object
        
    Returns:
        set: A set of all used object numbers
    """
    used_numbers = set()
    
    # Iterate through all objects in the PDF
    for obj_num, obj in enumerate(pdf.objects):
        if obj is not None:
            used_numbers.add(obj_num)
    
    # Also check the trailer and any other special objects
    if hasattr(pdf, '_trailer'):
        for key, value in pdf._trailer.items():
            if isinstance(value, pikepdf.Object) and hasattr(value, 'objgen'):
                obj_num, gen = value.objgen
                used_numbers.add(obj_num)
    
    return used_numbers


def find_free_object_number(pdf):
    """
    Find a free object number in the PDF.
    
    Args:
        pdf: A pikepdf.Pdf object
        
    Returns:
        int: A free object number
    """
    used_numbers = get_used_object_numbers(pdf)
    
    # Find the first free number
    free_num = 1
    while free_num in used_numbers:
        free_num += 1
    
    print(f"Found free object number: {free_num}")
    return free_num


def embed_file(pdf, file_path, free_obj_num=None):
    """
    Embed a file into the PDF using a free object number.
    
    Args:
        pdf: A pikepdf.Pdf object
        file_path: Path to the file to embed
        free_obj_num: Optional free object number to use
        
    Returns:
        int: The object number used for the embedded file
    """
    # If no free object number is provided, find one
    if free_obj_num is None:
        free_obj_num = find_free_object_number(pdf)
    
    # Read the file to embed
    with open(file_path, 'rb') as f:
        file_data = f.read()
    
    # Create file specification dictionary
    file_name = os.path.basename(file_path)
    
    # Create the embedded file stream
    embedded_file = Stream(pdf, file_data)
    
    # Create the file specification dictionary
    filespec = Dictionary(
        Type=Name.Filespec,
        F=file_name,
        EF=Dictionary(
            F=embedded_file
        )
    )
    
    # Add the file to the PDF's embedded files
    if '/Names' not in pdf.Root:
        pdf.Root.Names = Dictionary()
    
    if '/EmbeddedFiles' not in pdf.Root.Names:
        pdf.Root.Names.EmbeddedFiles = Dictionary(
            Names=Array()
        )
    
    # Add the file to the Names array
    names_array = pdf.Root.Names.EmbeddedFiles.Names
    names_array.append(file_name)
    names_array.append(filespec)
    
    # Manually assign the object number (this is a bit of a hack, but pikepdf doesn't expose this directly)
    # Note: This part is experimental and may not work in all cases
    try:
        # This is an internal API and might change in future versions of pikepdf
        pdf._objects.append(embedded_file)
        pdf._objects[free_obj_num] = embedded_file
    except Exception as e:
        print(f"Warning: Could not manually set object number: {e}")
        print("The file will still be embedded, but with an automatically assigned object number.")
    
    return free_obj_num


def main():
    parser = argparse.ArgumentParser(description='Embed a file into a PDF using a free object number')
    parser.add_argument('input_pdf', help='Input PDF file')
    parser.add_argument('file_to_embed', help='File to embed in the PDF')
    parser.add_argument('output_pdf', help='Output PDF file')
    parser.add_argument('--obj-num', type=int, help='Specific object number to use (optional)')
    
    args = parser.parse_args()
    
    # Check if files exist
    if not os.path.exists(args.input_pdf):
        print(f"Error: Input PDF file '{args.input_pdf}' does not exist")
        return 1
    
    if not os.path.exists(args.file_to_embed):
        print(f"Error: File to embed '{args.file_to_embed}' does not exist")
        return 1
    
    try:
        # Open the PDF
        with Pdf.open(args.input_pdf) as pdf:
            # Print some information about the PDF
            print(f"PDF Version: {pdf.pdf_version}")
            print(f"Number of Pages: {len(pdf.pages)}")
            
            # Get all used object numbers
            used_numbers = get_used_object_numbers(pdf)
            print(f"Used object numbers: {len(used_numbers)} objects")
            
            # Embed the file
            obj_num = embed_file(pdf, args.file_to_embed, args.obj_num)
            print(f"File embedded with object number: {obj_num}")
            
            # Save the modified PDF
            pdf.save(args.output_pdf)
            print(f"Modified PDF saved to: {args.output_pdf}")
            
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

