1. Run with Python 3.10

2. Create a virtual environment

3. Install the dependencies:
  pip install fastapi uvicorn python-multipart \
  tree-sitter tree-sitter-python tree-sitter-javascript \
  tree-sitter-typescript tree-sitter-java tree-sitter-go \
  tree-sitter-rust tree-sitter-c tree-sitter-cpp tree-sitter-c-sharp \
  pygments pypdf pdfplumber python-docx markdown docutils

4. Run the server
  uvicorn main:app --reload

5. Run the command:
  curl -X POST http://127.0.0.1:8000/parse -F "files=@yourfile.py" -F "files=@yourdoc.pdf"

6. Save the URL for the local parser as an environment variable called: PARSER_API

    
