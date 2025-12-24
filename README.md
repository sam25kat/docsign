# Medical PDF Signing Platform

A 100% open-source, secure document signing platform for healthcare. Doctors can digitally sign patient documents with their uploaded signatures.

## Features

- **Signature Upload**: Upload your signature image, background is automatically removed
- **Secure Storage**: Signatures are encrypted with AES-256 encryption
- **PDF Signing**: Drag and position your signature anywhere on the PDF
- **Document Management**: Track pending and signed documents
- **Role-Based Access**: Admin uploads documents, doctors sign them
- **Download Signed PDFs**: Download signed documents anytime

## Tech Stack (100% Open Source)

### Backend
- **Flask** - Python web framework
- **PyPDF2** - PDF manipulation
- **ReportLab** - PDF generation
- **Pillow** - Image processing
- **rembg** - AI-powered background removal
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
npm start or npm run dev
```

The frontend will start at `http://localhost:3000`

## Usage Flow

1. **Login** as admin (`admin@example.com` / `admin123`)
2. **Upload a PDF** document (Admin only)
3. **Register a doctor account** or login as doctor
4. **Upload signature** (go to "My Signature" page)
5. **Sign documents** - click on document, place signature, save
6. **Download** signed PDFs from the "Signed" tab

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
- `POST /api/documents/upload` - Upload PDF (admin only)
- `GET /api/documents` - List documents
- `GET /api/documents/:id` - Get document details
- `GET /api/documents/:id/file` - Get PDF file
- `POST /api/documents/:id/sign` - Sign document
- `GET /api/documents/:id/download` - Download signed PDF
- `DELETE /api/documents/:id/delete` - Delete document (admin only)

## Security Features

- **Password Hashing**: Werkzeug secure password hashing
- **Session Management**: Flask-Login for secure sessions
- **Encrypted Signatures**: AES-256-GCM encryption for stored signatures
- **Integrity Verification**: SHA-256 hash for signature integrity
- **CORS Protection**: Configured CORS for frontend origin

## Project Structure

```
Document Signer/
├── backend/
│   ├── app.py              # Main Flask application
│   ├── config.py           # Configuration
│   ├── models.py           # Database models
│   ├── encryption.py       # AES-256 encryption utilities
│   ├── signature_processor.py  # Background removal & processing
│   ├── pdf_signer.py       # PDF signature overlay
│   └── requirements.txt    # Python dependencies
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── components/     # Reusable components
│   │   ├── pages/          # Page components
│   │   ├── services/       # API services
│   │   ├── context/        # React context
│   │   └── App.js          # Main app component
│   └── package.json
├── uploads/                # Uploaded PDFs
├── signed_documents/       # Signed PDFs
└── signatures/             # Encrypted signatures
```
