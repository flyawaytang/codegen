#!/usr/bin/env python3
"""
PDF File Embedder with Custom Object Numbers

This script embeds files into PDF documents with precise control over object numbers.
It uses a combination of pikepdf and direct PDF structure manipulation to ensure
the embedded file is placed at the specified object number.

Usage:
    python pdf_file_embedder_custom.py input.pdf file_to_embed output.pdf --obj-num 100 --filespec-obj-num 101
"""

import os
import sys
import re
import argparse
import tempfile
import shutil
import subprocess
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


def create_custom_pdf_with_embedded_file(input_pdf_path, file_to_embed_path, output_pdf_path, obj_num=None, filespec_obj_num=None, mime_type=None):
    """
    Create a new PDF with an embedded file at a custom object number.
    
    Args:
        input_pdf_path: Path to the input PDF
        file_to_embed_path: Path to the file to embed
        output_pdf_path: Path to the output PDF
        obj_num: Object number for the embedded file
        filespec_obj_num: Object number for the file specification
        mime_type: MIME type for the embedded file
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Create a temporary directory for our work
        temp_dir = tempfile.mkdtemp()
        
        # Step 1: Read the file to embed
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
        
        # Step 2: Analyze the input PDF
        with Pdf.open(input_pdf_path) as pdf:
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
            
            # Check if the object numbers are already in use
            if embedded_file_obj_num in used_obj_nums:
                print(f"Warning: Object number {embedded_file_obj_num} is already in use. This may cause issues.")
            
            if filespec_obj_num in used_obj_nums:
                print(f"Warning: Object number {filespec_obj_num} is already in use. This may cause issues.")
            
            # Get the root object number
            root_obj_num = get_object_number(pdf.Root)
        
        # Step 3: Create the embedded file object
        embedded_file_obj = f"""
{embedded_file_obj_num} 0 obj
<<
  /Type /EmbeddedFile
  /Subtype /{subtype}
  /Length {len(file_data)}
  /Size {len(file_data)}
>>
stream
{file_data.decode('latin-1', errors='replace')}
endstream
endobj
"""
        
        # Step 4: Create the file specification object
        filespec_obj = f"""
{filespec_obj_num} 0 obj
<<
  /Type /Filespec
  /F ({file_name})
  /UF ({file_name})
  /Desc (Embedded file: {file_name})
  /EF << /F {embedded_file_obj_num} 0 R >>
>>
endobj
"""
        
        # Step 5: Create a new Names dictionary if needed
        names_obj_num = max_obj_num + 3
        embedded_files_obj_num = max_obj_num + 4
        
        embedded_files_obj = f"""
{embedded_files_obj_num} 0 obj
<<
  /Names [ ({file_name}) {filespec_obj_num} 0 R ]
>>
endobj
"""
        
        names_obj = f"""
{names_obj_num} 0 obj
<<
  /EmbeddedFiles {embedded_files_obj_num} 0 R
>>
endobj
"""
        
        # Step 6: Create a modified Root dictionary
        # First, save a copy of the original PDF
        temp_pdf_path = os.path.join(temp_dir, "temp.pdf")
        shutil.copy2(input_pdf_path, temp_pdf_path)
        
        # Modify the Root dictionary to include the Names dictionary
        with Pdf.open(temp_pdf_path) as pdf:
            # Check if the PDF already has a Names dictionary
            has_names = '/Names' in pdf.Root
            
            if not has_names:
                # Add the Names dictionary to the Root
                pdf.Root.Names = Dictionary()
                pdf.Root.Names.EmbeddedFiles = Dictionary(
                    Names=Array([file_name, filespec_obj_num])
                )
                
                # Save the modified PDF
                temp_modified_path = os.path.join(temp_dir, "temp_modified.pdf")
                pdf.save(temp_modified_path)
                
                # Read the modified PDF to extract the updated Root dictionary
                with open(temp_modified_path, 'rb') as f:
                    temp_pdf_data = f.read()
                
                # Find the Root dictionary in the temporary PDF
                root_pattern = re.compile(rb'%d 0 obj\s*<<.*?/Names.*?>>' % root_obj_num, re.DOTALL)
                root_match = root_pattern.search(temp_pdf_data)
                
                if root_match:
                    # Extract the updated Root dictionary
                    updated_root = root_match.group(0)
                    
                    # Read the original PDF
                    with open(input_pdf_path, 'rb') as f:
                        pdf_data = f.read()
                    
                    # Replace the Root dictionary in the original PDF
                    original_root_pattern = re.compile(rb'%d 0 obj\s*<<.*?>>' % root_obj_num, re.DOTALL)
                    original_root_match = original_root_pattern.search(pdf_data)
                    
                    if original_root_match:
                        pdf_data = pdf_data.replace(original_root_match.group(0), updated_root)
                        
                        # Write the modified PDF to a temporary file
                        temp_output_path = os.path.join(temp_dir, "temp_output.pdf")
                        with open(temp_output_path, 'wb') as f:
                            f.write(pdf_data)
                        
                        # Now append our new objects to this PDF
                        with open(temp_output_path, 'rb') as f:
                            pdf_data = f.read()
                        
                        # Find the end of the PDF file (before %%EOF)
                        eof_pos = pdf_data.rfind(b'%%EOF')
                        if eof_pos == -1:
                            print("Error: Could not find EOF marker in PDF")
                            return False
                        
                        # Insert our new objects before the EOF marker
                        new_objects = (embedded_file_obj + filespec_obj + embedded_files_obj + names_obj).encode('latin-1')
                        new_pdf_data = pdf_data[:eof_pos] + new_objects + pdf_data[eof_pos:]
                        
                        # Write the final PDF
                        with open(output_pdf_path, 'wb') as f:
                            f.write(new_pdf_data)
                        
                        print(f"Successfully created PDF with embedded file at object numbers: {embedded_file_obj_num} (file) and {filespec_obj_num} (filespec)")
                        return True
        
        # If we get here, something went wrong
        print("Error: Failed to modify the PDF")
        return False
    
    except Exception as e:
        print(f"Error creating custom PDF: {e}")
        return False
    finally:
        # Clean up temporary directory
        shutil.rmtree(temp_dir)


def main():
    parser = argparse.ArgumentParser(description='Embed a file into a PDF with custom object numbers')
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
    
    # Create a custom PDF with the embedded file
    print(f"\nEmbedding file: {args.file_to_embed}")
    success = create_custom_pdf_with_embedded_file(
        args.input_pdf,
        args.file_to_embed,
        args.output_pdf,
        args.obj_num,
        args.filespec_obj_num,
        args.mime_type
    )
    
    if success:
        print(f"Modified PDF saved to: {args.output_pdf}")
        
        # Verify the embedding
        try:
            with Pdf.open(args.output_pdf) as pdf:
                print("\nVerifying embedded file...")
                file_name = os.path.basename(args.file_to_embed)
                if verify_embedded_file(pdf, file_name):
                    print(f"Verification successful: Found embedded file '{file_name}'")
                    
                    # Check the object numbers
                    if '/Names' in pdf.Root and '/EmbeddedFiles' in pdf.Root.Names:
                        names_array = pdf.Root.Names.EmbeddedFiles.Names
                        if len(names_array) >= 2:
                            filespec = names_array[1]
                            if '/EF' in filespec and '/F' in filespec.EF:
                                embedded_file = filespec.EF.F
                                
                                # Get the actual object numbers
                                embedded_file_num = get_object_number(embedded_file)
                                filespec_num = get_object_number(filespec)
                                
                                print(f"Actual embedded file object number: {embedded_file_num}")
                                print(f"Actual file specification object number: {filespec_num}")
                                
                                if args.obj_num is not None and embedded_file_num != args.obj_num:
                                    print(f"Warning: Requested object number {args.obj_num} for embedded file, but got {embedded_file_num}")
                                
                                if args.filespec_obj_num is not None and filespec_num != args.filespec_obj_num:
                                    print(f"Warning: Requested object number {args.filespec_obj_num} for file specification, but got {filespec_num}")
                else:
                    print(f"Verification failed: Could not find embedded file '{file_name}'")
        except Exception as e:
            print(f"Warning: Could not verify the modified PDF: {e}")
            print("The PDF structure might be corrupted after direct modification.")
            print("Try opening the PDF with a PDF reader to check if it's valid.")
        
        return 0
    else:
        print("Failed to create custom PDF with embedded file.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

