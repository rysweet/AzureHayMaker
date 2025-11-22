# Azure HayMaker Orchestrator - Azure Functions on Container Apps
# For Container Apps with E16 workload profile (128GB RAM)

FROM mcr.microsoft.com/azure-functions/python:4-python3.11

# Set working directory
WORKDIR /home/site/wwwroot

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy orchestrator code (EXCLUDE old *_api.py files - they conflict with function_app.py)
COPY azure_haymaker/ ./azure_haymaker/
RUN rm -f ./azure_haymaker/orchestrator/*_api.py ./azure_haymaker/orchestrator/timer_trigger.py ./azure_haymaker/orchestrator/workflow_orchestrator.py ./azure_haymaker/orchestrator/orchestrator_app.py ./azure_haymaker/orchestrator/activities/*.py 2>/dev/null || true

# Copy Azure Functions required files
COPY function_app.py .
COPY host.json .

# Azure Functions expects function code in /home/site/wwwroot
# The Functions runtime will automatically discover and run the app

# Expose port 80 (Azure Functions default)
EXPOSE 80

ENV AzureWebJobsScriptRoot=/home/site/wwwroot \
    AzureFunctionsJobHost__Logging__Console__IsEnabled=true \
    FUNCTIONS_WORKER_RUNTIME=python
