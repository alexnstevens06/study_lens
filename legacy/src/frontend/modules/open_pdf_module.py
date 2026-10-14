from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QFileDialog
from .base_module import BaseModule

class OpenPDFModule(BaseModule):
    @property
    def priority(self):
        return 5

    def get_actions(self):
        open_action = QAction("Open PDF", self.main_window)
        open_action.triggered.connect(self.open_pdf)
        return [open_action]

    def open_pdf(self):
        file_name, _ = QFileDialog.getOpenFileName(self.main_window, "Open PDF", "", "PDF Files (*.pdf)")
        if file_name:
            import fitz
            import os
            import shutil
            import time
            
            try:
                # Attempt to open the document
                doc = fitz.open(file_name)
                
                # Check if the document is "repaired" or otherwise broken for incremental updates
                if not doc.can_save_incrementally():
                    print(f"[OpenPDF] Document '{file_name}' requires repair. repairing...")
                    
                    try:
                        temp_path = file_name + ".tmp"
                        
                        # Full save with garbage collection and deflation to "scrub" the file
                        doc.save(temp_path, garbage=4, deflate=True)
                        doc.close()
                        
                        # Replace original with temp (robustly)
                        max_retries = 3
                        for attempt in range(max_retries):
                            try:
                                if os.path.exists(file_name):
                                    os.replace(temp_path, file_name)
                                else:
                                    os.rename(temp_path, file_name)
                                break
                            except OSError as e_os:
                                if attempt < max_retries - 1:
                                    print(f"[WARNING] File replace failed (attempt {attempt+1}/{max_retries}): {e_os}. Retrying...")
                                    time.sleep(0.5)
                                else:
                                    raise e_os

                        print(f"[OpenPDF] Document repaired and saved to '{file_name}'")
                        
                        # Re-open the now-clean document
                        doc = fitz.open(file_name)
                        
                    except Exception as e_repair:
                        print(f"[ERROR] Failed to repair document: {e_repair}")
                        # If repair fails, we might still be able to open it read-only or as-is, 
                        # but user should be warned (console log for now)
                        if os.path.exists(file_name):
                             doc = fitz.open(file_name)

                self.main_window.pdf_viewer.set_document(doc)
            except Exception as e:
                print(f"Error loading document: {e}")
