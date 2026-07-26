#!/bin/bash
# Download the SAML-D (Synthetic Anti-Money Laundering) dataset from Kaggle
# Usage: bash download_dataset.sh

set -e

DATASET_URL="https://www.kaggle.com/api/v1/datasets/download/berkanoztas/synthetic-transaction-monitoring-dataset-aml"
ZIP_FILE="$HOME/Downloads/synthetic-transaction-monitoring-dataset-aml.zip"
TARGET_DIR="backend/app/data"

echo "📥 Downloading SAML-D dataset from Kaggle..."

# Create target directory if it doesn't exist
mkdir -p "$TARGET_DIR"

# Download the dataset
curl -L -o "$ZIP_FILE" "$DATASET_URL"

echo "📦 Extracting dataset..."

# Unzip to the target directory
unzip -o "$ZIP_FILE" -d "$TARGET_DIR"

# Clean up the zip file
rm -f "$ZIP_FILE"

echo "✅ Dataset downloaded and extracted to $TARGET_DIR"
echo ""
echo "Files in $TARGET_DIR:"
ls -la "$TARGET_DIR"

echo ""
echo "⚠️  Please verify the CSV filename and update backend/app/tools/engine.py if needed."
echo "   The expected file is: $TARGET_DIR/transactions.csv"
