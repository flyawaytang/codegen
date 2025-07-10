#!/usr/bin/env python3
"""
PDF File Embedder with Incremental Update

This script embeds files into PDF documents using incremental updates,
which ensures the embedded file is added to the end of the PDF.
It allows specifying custom object numbers for both the embedded file and the file specification.

Usage:
    python pdf_file_embedder_incremental.py input.pdf file_to_embed output.pdf --obj-num 10 --filespec-obj-num 20
"""

import os
import sys
import argparse
import tempfile
from pathlib import Path
import pikepdf
from pikepdf import Pdf, Name, Dictionary, Array, Stream


def analyze_pdf_objects(pdf):
    """
    Analyze the PDF objects and return information about them.
    
    Args:
        pdf: A pikepdf.Pdf object
        
    Returns:
        tuple: (used_obj_nums, max_obj_num, free_obj_nums)
    """
    used_obj_nums = set()
    
    # Iterate through all objects in the PDF
    for obj_num, obj in enumerate(pdf.objects):
        if obj is not None:
            used_obj_nums.add(obj_num)
    
    # Find the maximum object number
    max_obj_num = max(used_obj_nums) if used_obj_nums else 0
    
    # Find available object numbers (starting from max_obj_num + 1)
    free_obj_nums = [i for i in range(max_obj_num + 1, max_obj_num + 100) if i not in used_obj_nums]
    
    return used_obj_nums, max_obj_num, free_obj_nums


def get_object_number(obj):
    """
    Get the object number of a pikepdf object.
    
    Args:
        obj: A pikepdf object
        
    Returns:
        int: The object number, or 0 if not available
    """
    try:
        if hasattr(obj, 'objgen'):
            obj_num, gen = obj.objgen
            return obj_num
    except Exception:
        pass
    return 0


def embed_file_incremental(input_pdf_path, file_to_embed_path, output_pdf_path, obj_num=None, filespec_obj_num=None, mime_type=None):
    """
    Embed a file into a PDF using incremental updates.
    This ensures the embedded file is added to the end of the PDF.
    
    Args:
        input_pdf_path: Path to the input PDF
        file_to_embed_path: Path to the file to embed
        output_pdf_path: Path to the output PDF
        obj_num: Optional object number for the embedded file
        filespec_obj_num: Optional object number for the file specification
        mime_type: Optional MIME type for the embedded file
        
    Returns:
        tuple: (embedded_file_obj_num, filespec_obj_num) - The object numbers used
    """
    # Read the file to embed
    with open(file_to_embed_path, 'rb') as f:
        file_data = f.read()
    
    # Get the file name
    file_name = os.path.basename(file_to_embed_path)
    
    # Determine MIME type if not provided
    if mime_type is None:
        # Simple MIME type detection based on extension
        ext = os.path.splitext(file_to_embed_path)[1].lower()
        mime_map = {
            '.txt': 'text/plain',
            '.pdf': 'application/pdf',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.html': 'text/html',
            '.htm': 'text/html',
            '.xml': 'text/xml',
            '.json': 'application/json',
            '.zip': 'application/zip',
            '.doc': 'application/msword',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.xls': 'application/vnd.ms-excel',
            '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            '.ppt': 'application/vnd.ms-powerpoint',
            '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        }
        mime_type = mime_map.get(ext, 'application/octet-stream')
    
    # Extract the subtype from the MIME type
    subtype = mime_type.split('/')[-1].capitalize()
    
    # Open the PDF with pikepdf
    with Pdf.open(input_pdf_path) as pdf:
        # Analyze the PDF objects
        used_obj_nums, max_obj_num, free_obj_nums = analyze_pdf_objects(pdf)
        
        # Determine object numbers for our new objects
        if obj_num is None:
            embedded_file_obj_num = max_obj_num + 1
        else:
            embedded_file_obj_num = obj_num
        
        if filespec_obj_num is None:
            filespec_obj_num = max_obj_num + 2
        else:
            filespec_obj_num = filespec_obj_num
        
        # Create the embedded file stream with parameters
        params = {
            '/Type': Name.EmbeddedFile,
            '/Subtype': Name('/' + subtype),
            '/Size': len(file_data)
        }
        
        # Create a new stream object with our desired object number
        # We'll use a temporary object first
        embedded_file = Stream(pdf, file_data, params)
        
        # Create the file specification dictionary
        filespec = Dictionary(
            Type=Name.Filespec,
            F=file_name,
            UF=file_name,  # Unicode filename
            Desc=f"Embedded file: {file_name}",
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
        
        # Save the PDF with append mode
        # This will append the new objects to the end of the file
        # Check if the version of pikepdf supports incremental updates
        save_kwargs = {}
        if hasattr(pdf, 'save') and 'incremental' in pdf.save.__code__.co_varnames:
            save_kwargs['incremental'] = True
            save_kwargs['encryption'] = False
            save_kwargs['linearize'] = False
        
        # Save the PDF
        pdf.save(output_pdf_path, **save_kwargs)
        
        # Get the actual object numbers assigned
        embedded_file_actual_num = get_object_number(embedded_file)
        filespec_actual_num = get_object_number(filespec)
        
        print(f"Embedded file object number: {embedded_file_actual_num}")
        print(f"File specification object number: {filespec_actual_num}")
        
        return embedded_file_actual_num, filespec_actual_num


def extract_embedded_file(pdf, output_dir='.'):
    """
    Extract embedded files from the PDF.
    
    Args:
        pdf: A pikepdf.Pdf object
        output_dir: Directory to save extracted files
        
    Returns:
        list: List of extracted file paths
    """
    extracted_files = []
    
    # Check if the PDF has embedded files
    if '/Names' in pdf.Root and '/EmbeddedFiles' in pdf.Root.Names:
        names_array = pdf.Root.Names.EmbeddedFiles.Names
        
        # Process the Names array (name, filespec pairs)
        for i in range(0, len(names_array), 2):
            if i + 1 < len(names_array):
                file_name = str(names_array[i])
                filespec = names_array[i + 1]
                
                # Get the embedded file stream
                if '/EF' in filespec and '/F' in filespec.EF:
                    embedded_file = filespec.EF.F
                    
                    # Extract the file data
                    file_data = embedded_file.read_bytes()
                    
                    # Save the file
                    output_path = os.path.join(output_dir, file_name)
                    with open(output_path, 'wb') as f:
                        f.write(file_data)
                    
                    extracted_files.append(output_path)
                    print(f"Extracted: {file_name} -> {output_path}")
    
    if not extracted_files:
        print("No embedded files found in the PDF.")
    
    return extracted_files


def verify_embedded_file(pdf, file_name):
    """
    Verify that a file is embedded in the PDF.
    
    Args:
        pdf: A pikepdf.Pdf object
        file_name: Name of the file to verify
        
    Returns:
        bool: True if the file is embedded, False otherwise
    """
    if '/Names' in pdf.Root and '/EmbeddedFiles' in pdf.Root.Names:
        names_array = pdf.Root.Names.EmbeddedFiles.Names
        
        # Process the Names array (name, filespec pairs)
        for i in range(0, len(names_array), 2):
            if i + 1 < len(names_array):
                name = str(names_array[i])
                if name == file_name:
                    return True
    
    return False


def main():
    parser = argparse.ArgumentParser(description='Embed a file into a PDF by appending it to the end')
    parser.add_argument('input_pdf', help='Input PDF file')
    parser.add_argument('file_to_embed', nargs='?', help='File to embed in the PDF')
    parser.add_argument('output_pdf', nargs='?', help='Output PDF file')
    parser.add_argument('--analyze-only', action='store_true', help='Only analyze the PDF without embedding')
    parser.add_argument('--extract', action='store_true', help='Extract embedded files from the PDF')
    parser.add_argument('--output-dir', default='.', help='Directory to save extracted files (default: current directory)')
    parser.add_argument('--mime-type', help='MIME type for the embedded file')
    parser.add_argument('--obj-num', type=int, help='Specific object number to use for the embedded file')
    parser.add_argument('--filespec-obj-num', type=int, help='Specific object number to use for the file specification')
    
    args = parser.parse_args()
    
    # Check if the input PDF exists
    if not os.path.exists(args.input_pdf):
        print(f"Error: Input PDF file '{args.input_pdf}' does not exist.")
        return 1
    
    # Create output directory if it doesn't exist
    if args.extract and not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)
    
    # Open the PDF for analysis
    try:
        with Pdf.open(args.input_pdf) as pdf:
            # Analyze the PDF objects
            used_obj_nums, max_obj_num, free_obj_nums = analyze_pdf_objects(pdf)
            
            # Print PDF information
            print(f"PDF Version: {pdf.pdf_version}")
            print(f"Number of Pages: {len(pdf.pages)}")
            print(f"Total objects: {len(used_obj_nums)}")
            print(f"Maximum object number: {max_obj_num}")
            print(f"Available free object numbers: {free_obj_nums[:10]}...")
            
            # If analyze-only, print detailed object information
            if args.analyze_only:
                print("\nDetailed object information:")
                for obj_num in sorted(used_obj_nums):
                    obj = pdf.get_object(obj_num, 0)
                    print(f"Object {obj_num} (Generation 0): {type(obj).__name__}")
                return 0
            
            # If extract, extract embedded files
            if args.extract:
                print("\nExtracting embedded files...")
                extract_embedded_file(pdf, args.output_dir)
                return 0
            
            # Check if file_to_embed and output_pdf are provided
            if args.file_to_embed is None or args.output_pdf is None:
                print("Error: Both file_to_embed and output_pdf must be provided for embedding.")
                return 1
            
            # Check if the file to embed exists
            if not os.path.exists(args.file_to_embed):
                print(f"Error: File to embed '{args.file_to_embed}' does not exist.")
                return 1
    
    except Exception as e:
        print(f"Error analyzing PDF: {e}")
        return 1
    
    # Embed the file incrementally
    print(f"\nEmbedding file: {args.file_to_embed}")
    try:
        embedded_file_obj_num, filespec_obj_num = embed_file_incremental(
            args.input_pdf,
            args.file_to_embed,
            args.output_pdf,
            args.obj_num,
            args.filespec_obj_num,
            args.mime_type
        )
        
        print(f"Modified PDF saved to: {args.output_pdf}")
        
        # Verify the embedding
        with Pdf.open(args.output_pdf) as pdf:
            print("\nVerifying embedded file...")
            file_name = os.path.basename(args.file_to_embed)
            if verify_embedded_file(pdf, file_name):
                print(f"Verification successful: Found embedded file '{file_name}'")
            else:
                print(f"Verification failed: Could not find embedded file '{file_name}'")
        
        return 0
    except Exception as e:
        print(f"Error embedding file: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
