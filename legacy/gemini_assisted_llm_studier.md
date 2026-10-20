# **Project Specification: "Study Partner" Windows App**

## **1\. Project Overview**

Goal: A native Windows 11 application for 2-in-1 devices (Surface/Spectre) that integrates PDF reading, stylus-based annotation, and AI assistance into a single cohesive study environment.  
Core Philosophy: "Pen for thinking, Touch for navigating." The app distinguishes between input methods to create a seamless flow between reading and writing.

## **2\. Technical Stack**

* **Frontend:** C\# (.NET 8 or later) with WinUI 3 (Windows App SDK).  
* **Backend (Local Middleware):** Python (FastAPI or Flask) running locally on localhost.  
  * Handles OpenRouter API requests.  
  * Manages context window state and token counting.  
* **Rendering Engine:** PDFium (via PdfiumViewer or similar wrapper) for high-performance rendering.  
* **PDF Manipulation:** PDFSharp (or similar MIT-licensed library) for writing vector ink annotations back to the file.  
* **Database:** SQLite (local study\_data.db) for managing library metadata.  
* **Configuration:** JSON (prompts.json, settings.json) for user-modifiable prompts and app settings.

## **3\. Core Modules & Functionality**

### **A. The Library (Home Screen)**

* **Function:** Persists the user's collection of documents.  
* **Data Storage (SQLite):**  
  * Documents Table: ID, FilePath, LastOpenedDate, LastPageNum, TotalPages.  
* **UI:** Grid view of PDF thumbnails.

### **B. The PDF Reader (Main View)**

* **Rendering:** Uses **PDFium** to render pages as high-resolution bitmaps.  
  * Implements "Virtualization": Only renders the current page ±2 pages to memory to ensure low RAM usage (\<200MB).  
* **Input Separation (Crucial):**  
  * **Touch:** Binds to ScrollViewer. One-finger drag pans the document; pinch-to-zoom scales the view.  
  * **Pen:** Binds to InkCanvas. The InkPresenter.InputDeviceTypes must be set strictly to CoreInputDeviceTypes.Pen.  
* **Text Interaction:**  
  * **Selection:** Text selection is **strictly limited to Long Press** interactions (touch or pen hold). Standard taps/drags do not select text to prevent interference with inking.

### **C. The Annotation Engine (Vector Inking)**

* **Type:** **Stroke-based (Vector)**.  
  * Ink is stored as mathematical paths, allowing infinite scaling/zooming without pixelation.  
* **Tools:**  
  * **Pen:** Standard writing tool.  
  * **Eraser:** Object eraser (removes entire stroke).  
  * **Lasso:** Selection tool for moving ink or capturing prompts.  
  * *Note: The Highlighter has been removed.*  
* **Hardware Button Mapping:**  
  * **Front Button (Barrel):** Hold to activate **Eraser**.  
  * **Back Button (Tail/Top):** Click/Hold to activate **Lasso Select** tool.  
* **Persistence (Save Logic):**  
  * **Format:** Destructive/Standard PDF Annotation.  
  * **Process:** On save/close, the app translates InkCanvas strokes (X,Y screen coordinates) into PDF coordinates and writes them as standard PDF Ink Annotations.

### **D. The "Handwritten Prompt" Interface**

* **Trigger:** Accessed via the **Lasso** tool (Back button).  
* **Workflow:**  
  1. User activates Lasso via the Pen Back Button.  
  2. User circles a region of the screen (handwritten notes or PDF text).  
  3. **Capture:** App captures the region as an image stream.  
  4. **Action:** Image is sent to the local Python server.  
  5. **Analysis:** Python server sends image to OpenRouter with a pre-defined prompt from prompts.json (e.g., "Analyze this handwritten note...").

## **4\. LLM Integration (Local Python Server)**

### **Architecture**

* **Frontend (C\#):** Acts as the UI client. Sends JSON payloads (user queries, base64 images, page text) to http://localhost:XXXX.  
* **Backend (Python):**  
  * **Context Manager:** Maintains a Python list/object representing the current conversation history and loaded context for the active session.  
  * **API Handler:** Uses the openai Python library (configured for OpenRouter) or requests to hit https://openrouter.ai/api/v1.

### **Context Window Management (Python Side)**

* **Visualizer (C\# UI):** Sidebar list populated by polling the Python server for current context state.  
  * *Example Item:* \[Page 12 Text\] \[X\]  
  * *Example Item:* \[User Screenshot 1\] \[X\]  
* **Adding Context:**  
  * **"Add Page":** C\# extracts text \-\> POST to Python \-\> Python appends to context list.  
  * **"Add Selection":** User Long Press Selects Text \-\> "Add to Context" \-\> POST to Python.

### **Configuration (prompts.json)**

* System prompts and helper prompts are loaded from a local editable JSON file.  
* **Structure Example:**  
  {  
    "system\_prompt": "You are an expert study assistant...",  
    "lasso\_analysis\_prompt": "Analyze this handwritten note and...",  
    "summarize\_prompt": "Summarize the following text..."  
  }

## **5\. Development Phases**

1. **Phase 1: The Viewer (Skeleton)**  
   * Set up WinUI 3 project.  
   * Implement PDFium rendering.  
   * Implement "Long Press" text selection logic.  
2. **Phase 2: Annotation Pipeline**  
   * Implement stroke-based InkCanvas.  
   * **Hardware Integration:** Map PointerPointProperties.IsBarrelButtonPressed to Eraser and handle Tail Button events for Lasso.  
3. **Phase 3: Python Middleware**  
   * Write simple Python Flask/FastAPI server.  
   * Implement OpenRouter API calls.  
   * Create prompts.json loader.  
4. **Phase 4: Integration**  
   * Connect C\# frontend to Python backend.  
   * Implement Lasso-to-LLM pipeline.