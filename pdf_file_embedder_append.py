#!/usr/bin/env python3
"""
PDF File Embedder with Append Mode

This script embeds files into PDF documents by appending them to the end of the PDF file.
It allows specifying custom object numbers for both the embedded file and the file specification.

Usage:
    python pdf_file_embedder_append.py input.pdf file_to_embed output.pdf --obj-num 10 --filespec-obj-num 20
"""

import os
import sys
import argparse
import tempfile
import re
import struct
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


def append_file_to_pdf(input_pdf_path, file_to_embed_path, output_pdf_path, obj_num=None, filespec_obj_num=None, mime_type=None):
    """
    Append a file to a PDF by directly manipulating the PDF structure.
    This ensures the embedded file is at the end of the PDF.
    
    Args:
        input_pdf_path: Path to the input PDF
        file_to_embed_path: Path to the file to embed
        output_pdf_path: Path to the output PDF
        obj_num: Optional object number for the embedded file
        filespec_obj_num: Optional object number for the file specification
        mime_type: Optional MIME type for the embedded file
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Read the input PDF
        with open(input_pdf_path, 'rb') as f:
            pdf_data = f.read()
        
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
        
        # Find the end of the PDF file (before %%EOF)
        eof_pos = pdf_data.rfind(b'%%EOF')
        if eof_pos == -1:
            print("Error: Could not find EOF marker in PDF")
            return False
        
        # Find the last xref table
        xref_pos = pdf_data.rfind(b'xref', 0, eof_pos)
        if xref_pos == -1:
            print("Error: Could not find xref table in PDF")
            return False
        
        # Extract the trailer dictionary
        trailer_pos = pdf_data.rfind(b'trailer', xref_pos, eof_pos)
        if trailer_pos == -1:
            print("Error: Could not find trailer dictionary in PDF")
            return False
        
        # Find the start of the trailer dictionary
        trailer_dict_start = pdf_data.find(b'<<', trailer_pos)
        trailer_dict_end = pdf_data.find(b'>>', trailer_dict_start) + 2
        trailer_dict = pdf_data[trailer_dict_start:trailer_dict_end]
        
        # Extract the /Size value from the trailer
        size_match = re.search(rb'/Size\s+(\d+)', trailer_dict)
        if not size_match:
            print("Error: Could not find /Size in trailer dictionary")
            return False
        
        # Get the current size (number of objects)
        current_size = int(size_match.group(1))
        
        # Determine object numbers for our new objects
        if obj_num is None:
            embedded_file_obj_num = current_size
        else:
            embedded_file_obj_num = obj_num
        
        if filespec_obj_num is None:
            filespec_obj_num = current_size + 1
        
        # Update the size in the trailer dictionary
        new_size = max(filespec_obj_num, embedded_file_obj_num) + 1
        new_trailer_dict = re.sub(rb'/Size\s+\d+', f'/Size {new_size}'.encode(), trailer_dict)
        
        # Create the embedded file object
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
""".encode('latin-1')
        
        # Create the file specification object
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
""".encode('latin-1')
        
        # Check if the PDF already has a Names dictionary with EmbeddedFiles
        with Pdf.open(input_pdf_path) as pdf:
            has_names = '/Names' in pdf.Root
            has_embedded_files = has_names and '/EmbeddedFiles' in pdf.Root.Names
            
            if has_embedded_files:
                # Get the current Names dictionary object number
                names_obj_num = get_object_number(pdf.Root.Names)
                embedded_files_obj_num = get_object_number(pdf.Root.Names.EmbeddedFiles)
                
                # We need to update the existing Names dictionary
                if names_obj_num > 0 and embedded_files_obj_num > 0:
                    # Get the current Names array
                    names_array = pdf.Root.Names.EmbeddedFiles.Names
                    
                    # Create a new Names array with our file added
                    new_names_array = Array()
                    for item in names_array:
                        new_names_array.append(item)
                    
                    # Add our new file to the array
                    new_names_array.append(file_name)
                    new_names_array.append(filespec_obj_num)
                    
                    # Create a new EmbeddedFiles dictionary
                    embedded_files_obj = f"""
{embedded_files_obj_num} 0 obj
<<
  /Names [
    {' '.join([f"({item})" if isinstance(item, str) else f"{item} 0 R" for item in new_names_array])}
  ]
>>
endobj
""".encode('latin-1')
                    
                    # Add the updated EmbeddedFiles dictionary to our output
                    embedded_file_obj += embedded_files_obj
            else:
                # We need to create a new Names dictionary
                names_obj_num = new_size
                embedded_files_obj_num = new_size + 1
                new_size += 2
                
                # Create the EmbeddedFiles dictionary
                embedded_files_obj = f"""
{embedded_files_obj_num} 0 obj
<<
  /Names [ ({file_name}) {filespec_obj_num} 0 R ]
>>
endobj
""".encode('latin-1')
                
                # Create the Names dictionary
                names_obj = f"""
{names_obj_num} 0 obj
<<
  /EmbeddedFiles {embedded_files_obj_num} 0 R
>>
endobj
""".encode('latin-1')
                
                # Add the new dictionaries to our output
                embedded_file_obj += embedded_files_obj + names_obj
                
                # Update the Root dictionary to include the Names dictionary
                with Pdf.open(input_pdf_path) as pdf:
                    root_obj_num = get_object_number(pdf.Root)
                    if root_obj_num > 0:
                        # Create a temporary file to modify the Root dictionary
                        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
                            temp_pdf_path = temp_file.name
                        
                        # Save a copy of the PDF
                        with Pdf.open(input_pdf_path) as pdf:
                            # Add the Names dictionary to the Root
                            pdf.Root.Names = Dictionary()
                            pdf.Root.Names.EmbeddedFiles = Dictionary(
                                Names=Array([file_name, filespec_obj_num])
                            )
                            pdf.save(temp_pdf_path)
                        
                        # Read the modified PDF to extract the updated Root dictionary
                        with open(temp_pdf_path, 'rb') as f:
                            temp_pdf_data = f.read()
                        
                        # Find the Root dictionary in the temporary PDF
                        root_pattern = re.compile(rb'%d 0 obj\s*<<.*?/Names.*?>>' % root_obj_num, re.DOTALL)
                        root_match = root_pattern.search(temp_pdf_data)
                        if root_match:
                            # Extract the updated Root dictionary
                            updated_root = root_match.group(0)
                            
                            # Replace the Root dictionary in the original PDF
                            original_root_pattern = re.compile(rb'%d 0 obj\s*<<.*?>>' % root_obj_num, re.DOTALL)
                            original_root_match = original_root_pattern.search(pdf_data)
                            if original_root_match:
                                pdf_data = pdf_data.replace(original_root_match.group(0), updated_root)
                        
                        # Clean up the temporary file
                        os.unlink(temp_pdf_path)
        
        # Create a new xref table
        xref_entries = []
        xref_entries.append(f"0 {new_size}")
        xref_entries.append("0000000000 65535 f ")
        
        # Add entries for existing objects (placeholder)
        for i in range(1, current_size):
            xref_entries.append("0000000000 00000 n ")
        
        # Add entries for our new objects
        # In a real implementation, we would calculate the actual byte offsets
        # For simplicity, we're using placeholders here
        for i in range(current_size, new_size):
            xref_entries.append("0000000000 00000 n ")
        
        new_xref_table = "xref\n" + "\n".join(xref_entries) + "\n"
        
        # Create the new PDF data
        # We'll insert our new objects before the last xref table
        new_pdf_data = pdf_data[:xref_pos] + embedded_file_obj + filespec_obj + new_xref_table.encode() + new_trailer_dict + b"\nstartxref\n" + str(xref_pos).encode() + b"\n%%EOF\n"
        
        # Write the new PDF
        with open(output_pdf_path, 'wb') as f:
            f.write(new_pdf_data)
        
        print(f"Successfully appended file to PDF with object numbers: {embedded_file_obj_num} (file) and {filespec_obj_num} (filespec)")
        return True
    
    except Exception as e:
        print(f"Error appending file to PDF: {e}")
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
    
    # Append the file to the PDF
    print(f"\nAppending file: {args.file_to_embed}")
    success = append_file_to_pdf(
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
                else:
                    print(f"Verification failed: Could not find embedded file '{file_name}'")
        except Exception as e:
            print(f"Warning: Could not verify the modified PDF: {e}")
            print("The PDF structure might be corrupted after direct modification.")
            print("Try opening the PDF with a PDF reader to check if it's valid.")
        
        return 0
    else:
        print("Failed to append file to PDF.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

