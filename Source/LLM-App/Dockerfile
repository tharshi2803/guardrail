FROM python:3.12-slim

WORKDIR /app

# Install guardrailsdk from sibling directory (build context is projects/)
COPY guardrailsdk/ /guardrailsdk/
RUN pip install --no-cache-dir /guardrailsdk

COPY ragqaapp/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY ragqaapp/ .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
