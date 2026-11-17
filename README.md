# 🌸 DermaGlow AI
### Personalized Skincare Recommendation Website

**Developed by Salwa Choudhari**

DermaGlow AI is a web-based skincare recommendation platform designed to help users explore skincare products and create personalized skincare routines based on their skin type, concerns, sensitivity, and preferences.

The platform features a skincare questionnaire, product catalog, ingredient-based recommendations, customer reviews, and an administrative dashboard.

## 🚀 Live Website

https://derma-glow-ai.vercel.app

## ✨ Key Features

### 1. Personalized Skin Analysis
- Interactive skincare questionnaire
- Skin type and sensitivity selection
- Skin concern identification
- Ingredient exclusion preferences
- Budget selection
- Personalized skincare recommendations

### 2. Skincare Recommendation Engine
- Ingredient keyword matching
- Approved product recommendations
- Morning skincare routine
- Night skincare routine
- Product suitability guidance

### 3. Skincare Product Catalog
- Product search and category filters
- Product images and descriptions
- Ingredient information
- Indian reference prices, where available
- Product ratings and reviews

### 4. Customer Reviews
- Five-star rating system
- Customer review submission
- Review moderation
- Approved customer reviews displayed publicly

### 5. Admin Dashboard
- Secure administrator login
- Product approval and rejection
- Product information management
- Price management
- Customer review moderation

### 6. Product Data Integration
- Product information imported from Open Beauty Facts
- India-tagged skincare product filtering
- Duplicate prevention using product barcodes
- Automated product import script

## 🛠️ Technologies Used

| Technology | Purpose |
|---|---|
| Python | Backend development |
| Flask | Web framework |
| HTML5 | Website structure |
| CSS3 | Website styling |
| JavaScript | Frontend interactions |
| SQLite | Local development database |
| Neon PostgreSQL | Production database |
| GitHub | Source code management |
| Vercel | Website deployment |

## 📁 Project Structure

```text
DermaGlow/
├── app.py
├── database.py
├── recommender.py
├── recommendations.py
├── reviews.py
├── product_importer.py
├── daily_update.py
├── requirements.txt
├── static/
│   ├── css/
│   └── js/
└── templates/
    ├── index.html
    ├── skin_analysis.html
    ├── products.html
    ├── reviews.html
    └── admin.html
```

## 💻 Running Locally

Clone the repository:

```bash
git clone https://github.com/Salwac12/DermaGlow-AI.git
cd DermaGlow-AI
```

Create and activate a Python virtual environment:

```bash
python -m venv venv
```

On Windows PowerShell:

```powershell
.\venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Configure the required environment variables in a local `.env` file.

Initialize the local database:

```bash
python database.py
```

Run the application:

```bash
python app.py
```

Open:

http://127.0.0.1:5000

**Note:** Local SQLite data is not included in the GitHub repository. A fresh database will not automatically contain the existing product catalog.

## 🔐 Security

- Environment variables are used for sensitive configuration.
- Administrator credentials are not stored in the source code.
- Customer reviews require moderation.
- Sensitive files, including `.env`, are excluded from version control.
- CSRF protection is implemented for administrative actions and review submissions.

## ⚠️ Disclaimer

DermaGlow AI provides general skincare product information and recommendations. It does not provide medical diagnoses or treatments.

Recommendations are based on available product information and ingredient keywords. Users should check product labels and consult qualified professionals when necessary.

## 👩‍💻 Developer

**Salwa Choudhari**

Developed as a web application project demonstrating Python, Flask, database integration, web development, and personalized recommendation logic.
