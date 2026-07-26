#!/bin/bash
# Download the SAML-D (Synthetic Anti-Money Laundering) dataset from Kaggle
# Usage: bash download_dataset.sh

set -e
curl -L -o backend/app/data/SAML-D.zip https://www.kaggle.com/api/v1/datasets/download/berkanoztas/synthetic-transaction-monitoring-dataset-aml
unzip backend/app/data/SAML-D.zip
mv SAML-D.csv backend/app/data/SAML-D.csv
