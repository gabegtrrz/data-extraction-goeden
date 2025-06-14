import ocrmypdf
import argparse
import logging
import sys
from pathlib import Path
from multiprocessing import Pool, cpu_count
from datetime import datetime
import ocrmypdf.exceptions
# from tqdm import tqdm #progress bar


# --- Logging Config --_

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s]: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)], # Print logs to the console
)

logger = logging.getLogger(__name__)


def ocr_worker(input_pdf_path_str: str, output_pdf_path_str: str, force_ocr: bool, language: str = 'eng+fil'):
    '''
    worker function to process single PDF files

    Args:
    - input_pdf_path_str (str)
    - output_pdf_path_str (str)
    - force_ocr (bool): Whether to force OCR even if text is present.
    - language (str): Language for OCR.

    Returns:
    - dict: dictionary containing:
        - status: ('success' or 'error'),
        - input_file: input file path,
        either
        ouput_path 
        OR
        error: error message

    '''

    # input_pdf_path = Path(input_pdf_path_str) # convert to Path object for easier handling

    try: 
        ocrmypdf.ocr(
            input_file= input_pdf_path_str,
            output_file=output_pdf_path_str,
            force_ocr=force_ocr,
            language=language,
            progress_bar=True,
            deskew=True
            )
        
        output = {
            'status': 'success',
            'input_file': input_pdf_path_str,
            'output_path': output_pdf_path_str
            }
        
        return output

    except ocrmypdf.exceptions.EncryptedPdfError:
        output = {
            'status': 'error',
            'input_file': input_pdf_path_str,
            'error': "Encrypted PDF - cannot process."
            }
        
        return output
    
    except ocrmypdf.exceptions.InputFileError as e:
        output = {
            'status': 'error',
            'input_file': input_pdf_path_str,
            'error': f"Input file error: {e}"
            }
        
        return output
        
    except Exception as e:
        output = {
            'status': 'error',
            'input_file': input_pdf_path_str,
            'error': f"Unexpected error: {e}"
            }
        
        return output

# --- Main Function ---

def main():
    parser = argparse.ArgumentParser(
        description="Batch OCR PDF files in a folder using OCRmyPDF with multicore processing."
    )
    parser.add_argument(
        "input_folder", type=str, help="Path to the folder containing PDF files."
    )

    # optional argument for forcing OCR
    parser.add_argument(
        "--force-ocr",
        action="store_true",
        help="Force OCR even if the document appears to have text. Default is False."
    )

    # optional argument for setting num of wrokers
    parser.add_argument(
        "--workers",
        type=int,
        # Default to total cores minus 2, but at least 1
        default=max(1, cpu_count() - 2),
        help=f"Set the number of parallel worker processes. Default: {max(1, cpu_count() - 2)}"
    )
    
    # optional argument for specifying language
    parser.add_argument(
        "--language",
        type=str,
        default="eng",
        help="Specify the OCR language (e.g., eng, fil). Default: eng+fil"
    )

    args = parser.parse_args()

    input_folder_path = Path(args.input_folder)

    # --- Validate Input Folder ---

    if not input_folder_path.is_dir():
        logger.error(f"Error: The provided path '{input_folder_path}' is not a valid directory.")
        sys.exit(1)
    
    
    # --- Create Folder ---

    # timestamp_str = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    # output_folder_name = f"OUTPUT_PDFs_{timestamp_str}"

    output_folder_name = f"OCRed_PDFs_"
    output_folder_path = input_folder_path / output_folder_name

    try:
        output_folder_path.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        logger.error(f'Could not create output folder "{output_folder_path}". Error {e}')

    # --- Find PDF files ---
    # look for files ending with .pdf
    logger.info(f'Scanning for PDF files in: {input_folder_path}')

    pdf_files = []
    # yields list of pathlib.Path objects ending in .pdf
    for p in input_folder_path.iterdir():
        if p.is_file() and p.suffix.lower() == '.pdf':
            pdf_files.append(p)

    if not pdf_files:
        logger.info('No files found in the input folder.')
        sys.exit(0)
    
    logger.info(f'Found {len(pdf_files)} PDF files. Initializing...')



    # --- Prepare for multiprocessing ---

    tasks_for_starmap = []

    for pdf_file_path in pdf_files:
        output_pdf_name = f'[OCR] {pdf_file_path.name}'
        output_pdf_full_path = output_folder_path / output_pdf_name
        # Output PDF Directory is in ### Create Folder Named with timestamp ### above

        tasks_for_starmap.append(
            (str(pdf_file_path), str(output_pdf_full_path), args.force_ocr, args.language)
            )

    # --- Execute OCR with multiprocessing ---

    # determine number of CPU cores to use.
    # we want to use max and leaving 1 free core to avoid crashing

    num_workers = args.workers

    logger.info(f"Starting OCR processing using {num_workers} parallel processes.")
    logger.info(f"OCR Language: '{args.language}', Force OCR: {args.force_ocr}")
    logger.info("Each OCR will use a single core.")

    results = []

    with Pool(processes=num_workers) as pool:
        results = list(pool.starmap(func=ocr_worker,iterable= tasks_for_starmap))

        # tqdm(starmap_iterator, desc="Processing PDFs", total=len(tasks_for_starmap))

    # --- Processing Summary ---

    successful_count = 0
    failed_files_info = []

    for res in results:
        if res['status'] == 'success':
            successful_count += 1
        else:
            failed_files_info.append(f"- File: {Path(res['input_file']).name}, Error: {res['error']}")
    
    logger.info("\n\n\n --- OCR Processing Summary ---\n")
    logger.info(f"Output folder: {output_folder_path}")
    logger.info(f"Total PDF files found: {len(pdf_files)}")
    logger.info(f"Successfully Processed: {successful_count} file(s).")
    
    failed_count = len(failed_files_info)
    if failed_count > 0:
        logger.warning(f"Failed to OCR: {failed_count} file(s). Details below:")
        for info in failed_files_info:
            logger.warning(info)
    else:
        logger.info("All found PDF files processed successfully!")
        
    logger.info("Script finished. \n ")


if __name__ == "__main__":
    main()





