import argparse
import PyPDF2
from pathlib import Path
import time


# "Modular" functions (used multiple times each)
def enumerate_duplicate_paths(start_path: Path):
    parent = start_path.parent
    suffix = "".join(start_path.suffixes)
    test_path = start_path.with_suffix('').name

    ends_in_a_number: bool = True

    try:
        iteration_number = int(test_path.split()[-1])

    except (ValueError, IndexError):
        iteration_number = 1
        ends_in_a_number = False

    print("    Generating name...")
    while ((parent / test_path).with_suffix(suffix)).exists():
        if ends_in_a_number:
            test_path = " ".join(test_path.split()[:-1])
        test_path += " " + str(iteration_number + 1)
        ends_in_a_number = True
        iteration_number += 1

    return (parent / test_path).with_suffix(suffix)


# "Procedural" functions(called once each)
def determine_pdfs(input_path: Path):
    print("Reading input directory.")
    print("    Verifying input path is a readable directory...")
    if not input_path.exists():
        print(str(input_path), "is not a valid file path.")
        exit(1)
    elif not input_path.is_dir():
        print(str(input_path), "is not a directory, it is either a file, or it is a broken symbolic link.")
        exit(1)

    pdfs_working_list: list = []
    print("    Identifying PDF files...")
    for child in input_path.iterdir():
        try:
            PyPDF2.PdfFileReader(str(child))

        except (PyPDF2.utils.PdfReadError, IsADirectoryError):
            # Do nothing
            print("       ", str(child), "is not a PDF file.")
        else:
            print("       ", str(child), "is a PDF file.")
            pdfs_working_list.append(child.absolute())

    print("PDFs list compiled.")
    return pdfs_working_list


def generate_output_path(input_path: Path, manual_path: str, new_dir: bool):
    print("Generating Output Path...")

    if manual_path and (not Path(manual_path).is_dir()):
        print(manual_path, "is not a valid output directory.")
        exit(1)

    final_path: Path
    if not new_dir:
        if manual_path:
            final_path = Path(manual_path)
        else:
            final_path = input_path
    else:
        parent_path: Path
        if manual_path:
            print("    Generating path from manual input and directory name.")
            parent_path = Path(manual_path)
        else:
            parent_path = input_path
        test_path = parent_path / (input_path.stem + " extracted pdfs")

        final_path = enumerate_duplicate_paths(test_path)
    print("    Output directory name generated as", str(final_path) + ".")
    return final_path


def create_output_directory(output_path: Path, pdfs_list: list):
    print("Creating output directory...")
    pdfs_list_count: int = len(pdfs_list)
    if pdfs_list_count > 0 and args.nd:
        output_path.mkdir()
        print("Output directory created.")
    elif not (pdfs_list_count > 0):
        print("No PDFs found in", args.input)
        exit(0)


def extract_text(pdf_paths: list, output_path: Path, input_path: str, max_extraction_time: float):
    print("Extracting text...")
    for pdf_path in pdf_paths:
        txt_path = enumerate_duplicate_paths(output_path.joinpath(Path(pdf_path.stem).with_suffix(".txt")))
        txt_path.touch()
        print("   ", pdf_path, "->", txt_path)

        pdf_reader = PyPDF2.PdfFileReader(str(pdf_path))
        try:
            page_max_index = pdf_reader.getNumPages() - 1
        except PyPDF2.utils.PdfReadError:
            if pdf_reader.isEncrypted:
                print("   ", pdf_path, "is encrypted and cannot be extracted. If you would like this file to be "
                                       "extracted, please decrypt the file and run the extraction again.")
            else:
                print("    There was a error reading", pdf_path, "the file may be corrupted so it will be skipped.")
            txt_path.unlink()
        else:
            page: int = 0
            extracted_text: str = ""

            start_time = time.time()
            while page <= page_max_index:
                if max_extraction_time and (start_time + max_extraction_time) < time.time():
                    print(pdf_path, "timed out after extracting", page, "/", (page_max_index + 1), "pages. To extract "
                                                                                                   "the full document"
                                                                                                   " run the command "
                                                                                                   "again with a "
                                                                                                   "longer or "
                                                                                                   "nonexistent time "
                                                                                                   "limit.")
                    break
                extracted_text += "\n\n" + pdf_reader.getPage(page).extractText()
                page += 1
            txt_path.write_text(extracted_text)

    print("PDFs in", input_path, "extracted to", str(output_path))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extracts text from all PDFs in a directory.")
    parser.add_argument("input", metavar="Input directory path", type=str, help="Path of directory with PDFs to "
                                                                                "extract.")
    parser.add_argument("-output", metavar="Output directory path", type=str, help="Path of directory to extract "
                                                                                   "files to (Defaults to same as "
                                                                                   "input).")
    parser.add_argument("-nd", action="store_true", help="Places extracted text files into new directory with same "
                                                         "name as pdf file(Defaults to false).")
    parser.add_argument("-timeout", metavar="Extraction time limit", type=float, help="Restricts the time for the "
                                                                                      "extraction of each PDF to the "
                                                                                      "inputted value in seconds.")
    args = parser.parse_args()

    pdfs = determine_pdfs(Path(args.input))
    output_dir_path = generate_output_path(Path(args.input), args.output, args.nd)

    create_output_directory(output_dir_path, pdfs)
    extract_text(pdfs, output_dir_path, args.input, args.timeout)
