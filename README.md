# 📄 CV Assistant Chat App

A fullstack AI-powered chat assistant that allows users to upload CVs in PDF format and ask natural language questions to identify candidate profiles based on experience and skills.

## 🚀 Features

- ✅ Upload PDF CVs via a drag-and-drop interface
- 🧠 Extracts content using **Azure Document Intelligence**
- 🔍 Retrieves relevant documents using **TF-IDF-based RAG (Retrieval-Augmented Generation)**
- 💬 Allows users to ask queries like: *"Who has experience with Kubernetes?"*
- 🧾 Responds with matching filenames and relevant text
- ✨ Optional lightweight **GPT-2 (distilgpt2)** generation for enriched answers
- ⚙️ Fully containerized and deployed on **Azure Kubernetes Service (AKS)** with **NGINX Ingress**
- 🔐 Secrets managed securely via **Azure Key Vault**

## 📦 Tech Stack

- **Frontend:** React.js
- **Backend:** FastAPI (Python)
- **Document Processing:** Azure Document Intelligence
- **Optional Generation:** HuggingFace Transformers (distilgpt2)
- **Containerization:** Docker
- **Deployment:** Azure Kubernetes Service (AKS) + NGINX Ingress
- **Secrets Management:** Azure Key Vault & Github Secrets


### Prerequisites for the Setup

- Azure subscription with Document Intelligence resource
- Azure Kubernetes Service (AKS)
- Azure Container Registry (ACR)
- Python 3.10+, Node.js 18+, Docker, kubectl, Azure CLI
