---
description: Deploy CrisisOps AI to Google Cloud Run
---

Follow these steps to deploy the unified container to Google Cloud Run.

### 1. Unified Deployment Command
Wait, before running this, ensure you have set up your Google Cloud Project.

// turbo
```bash
gcloud run deploy crisis-ops-ai \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars "DATABASE_URL=your_db_url,GEMINI_API_KEY=your_key"
```

### 2. Manual Steps if Build Fails
If the direct `source` deployment fails, follow the manual build and push path:

#### Build the image using Cloud Build
```bash
gcloud builds submit --tag gcr.io/[PROJECT_ID]/crisis-ops-ai
```

#### Deploy the image
```bash
gcloud run deploy crisis-ops-ai \
  --image gcr.io/[PROJECT_ID]/crisis-ops-ai \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```
