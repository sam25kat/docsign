# Medical PDF Signing Platform

A 100% open-source, secure document signing platform for healthcare. Doctors can digitally sign patient documents with their uploaded signatures.

## Features

### Core Features
- **Signature Upload**: Upload your signature image, background is automatically removed
- **Secure Storage**: Signatures encrypted with AES-256-GCM encryption
- **PDF Signing**: Drag and position your signature anywhere on the PDF
- **Document Management**: Track pending and signed documents
- **Role-Based Access**: Admin uploads documents, doctors sign them
- **Download Signed PDFs**: Download signed documents anytime

### Auto-Detect Signature Position
- **Smart Detection**: Automatically finds signature fields in PDFs
- **Medical Keywords**: Prioritizes medical-specific labels like "Signature of Physician", "Doctor's Signature", "Consulting Physician", etc.
- **Multi-language**: Supports English and Hindi signature labels
- **Precise Placement**: Places signature directly above the label text
- **Fallback Logic**: Uses line detection or bottom-of-page placement if no keywords found

### Bulk Signing
- **Sign Multiple Documents**: Select and sign multiple PDFs at once
- **Auto-Position for All**: Uses auto-detect for each document's signature placement
- **Progress Tracking**: Visual progress bar shows signing status
- **Error Handling**: Continues with remaining documents if one fails

### Multi-File Upload
- **Batch Upload**: Select multiple PDF files at once
- **Drag & Drop**: Drag multiple files into the upload zone
- **File Management**: View file list with sizes, remove individual files
- **Sequential Processing**: Uploads files one-by-one with progress indication

## Tech Stack (100% Open Source)

### Backend
- **Flask** - Python web framework
- **PyPDF2** - PDF manipulation
- **ReportLab** - PDF generation
- **Pillow** - Image processing
- **rembg** - AI-powered background removal
- **pdfplumber** - PDF text extraction with coordinates
- **cryptography** - AES-256 encryption
- **SQLite** - Database

### Frontend
- **React** - UI framework
- **react-pdf** - PDF rendering
- **react-router-dom** - Routing
- **axios** - API calls

## Quick Start

### Prerequisites
- Python 3.9+
- Node.js 18+
- pip
- npm

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the server
python app.py
```

The backend will start at `http://localhost:5000`

**Default Admin Credentials:**
- Email: `admin@example.com`
- Password: `admin123`

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm start
```

The frontend will start at `http://localhost:3000`

## Usage Flow

### Basic Document Signing
1. **Login** as admin (`admin@example.com` / `admin123`)
2. **Upload PDFs** - supports multiple files at once
3. **Register a doctor account** or login as doctor
4. **Upload signature** (go to "My Signature" page)
5. **Sign documents** - click on document, position signature, save
6. **Download** signed PDFs from the "Signed" tab

### Bulk Signing
1. Go to **Documents** page
2. Click **Bulk Sign** button
3. Select documents to sign (checkboxes)
4. Click **Sign Selected** - auto-detects signature position for each
5. View progress as documents are signed
6. Download signed documents individually or from "Signed" tab

### Auto-Detect Feature
When signing a single document:
1. Open the document for signing
2. Click **Auto-Detect Position** button
3. Signature automatically moves to detected position
4. Adjust manually if needed, then save

## API Endpoints

### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login
- `POST /api/auth/logout` - Logout
- `GET /api/auth/me` - Get current user

### Signatures
- `POST /api/signatures/upload` - Upload signature image
- `GET /api/signatures/preview` - Get signature preview
- `DELETE /api/signatures/delete` - Delete signature

### Documents
- `POST /api/documents/upload` - Upload PDF (admin only, supports batch)
- `GET /api/documents` - List documents
- `GET /api/documents/:id` - Get document details
- `GET /api/documents/:id/file` - Get PDF file
- `POST /api/documents/:id/sign` - Sign document
- `GET /api/documents/:id/download` - Download signed PDF
- `DELETE /api/documents/:id/delete` - Delete document (admin only)

### Auto-Detect & Bulk Signing
- `POST /api/documents/:id/detect-signature-position` - Detect signature position in PDF
- `POST /api/documents/bulk-sign` - Sign multiple documents at once

## Signature Detection Keywords

The auto-detect feature searches for these patterns (case-insensitive):

**Medical-Specific (Highest Priority)**
- Signature of Physician / Doctor
- Physician's Signature / Doctor's Signature
- Consulting Physician / Attending Physician
- Medical Officer Signature
- Surgeon's / Specialist's / Consultant Signature

**General**
- Authorized Signature
- Sign Here
- Signed By / Authorized By / Approved By

**Hindi**
- चिकित्सक के हस्ताक्षर (Doctor's signature)
- डॉक्टर के हस्ताक्षर
- हस्ताक्षर

## Security Features

- **Password Hashing**: Werkzeug secure password hashing
- **Session Management**: Flask-Login for secure sessions
- **Encrypted Signatures**: AES-256-GCM encryption for stored signatures
- **Integrity Verification**: SHA-256 hash for signature integrity
- **CORS Protection**: Configured CORS for frontend origin
- **Persistent Keys**: Encryption key stored in `.env` file

## Configuration

Create a `.env` file in the `backend/` folder:

```env
# Flask Configuration
SECRET_KEY=your-secret-key-here
FLASK_ENV=development
FLASK_DEBUG=1

# Database
DATABASE_URL=sqlite:///medical_docs.db

# Encryption Key (32 bytes base64 encoded)
# Generate with: python -c "import base64, os; print(base64.b64encode(os.urandom(32)).decode())"
# IMPORTANT: Do not change this key or existing signatures will become unreadable
ENCRYPTION_KEY=your-base64-encoded-key-here
```

## Project Structure

```
Document Signer/
├── backend/
│   ├── app.py                  # Main Flask application
│   ├── config.py               # Configuration
│   ├── models.py               # Database models
│   ├── encryption.py           # AES-256 encryption utilities
│   ├── signature_processor.py  # Background removal & processing
│   ├── signature_detector.py   # Auto-detect signature position
│   ├── pdf_signer.py           # PDF signature overlay
│   ├── .env                    # Environment configuration
│   └── requirements.txt        # Python dependencies
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── components/         # Reusable components
│   │   ├── pages/              # Page components
│   │   │   ├── Documents.js    # Document list with bulk signing
│   │   │   ├── SignDocument.js # PDF viewer with auto-detect
│   │   │   └── UploadDocument.js # Multi-file upload
│   │   ├── services/           # API services
│   │   ├── context/            # React context
│   │   └── App.js              # Main app component
│   └── package.json
├── uploads/                    # Uploaded PDFs
├── signed_documents/           # Signed PDFs
└── signatures/                 # Encrypted signatures
```

## Troubleshooting

### Signature Decryption Failed
If you see "cryptography.exceptions.InvalidTag" error:
- The encryption key has changed since the signature was uploaded
- Re-upload your signature after setting a persistent `ENCRYPTION_KEY` in `.env`

### Auto-Detect Not Finding Position
- Ensure the PDF contains searchable text (not scanned image)
- The feature looks for specific keywords - generic PDFs may use fallback positioning
- Install `pdfplumber` for best results: `pip install pdfplumber`

### Background Removal Slow
- First-time signature upload downloads the AI model (~170MB)
- Subsequent uploads are faster
- Ensure sufficient RAM (4GB+ recommended)
