"""
Data Transformation and Cleaning Classes
"""

import pandas as pd
import numpy as np
from datetime import datetime
import re

class DataCleaner:
    """Data cleaning operations"""

    def clean_customer_data(self, df):
        """Clean customer data"""
        df_clean = df.copy()

        # Remove duplicates
        df_clean = df_clean.drop_duplicates(subset=['customer_id'])

        # Clean string fields
        df_clean['first_name'] = df_clean['first_name'].str.strip().str.title()
        df_clean['last_name'] = df_clean['last_name'].str.strip().str.title()
        df_clean['city'] = df_clean['city'].str.strip().str.title()

        # Clean email addresses
        df_clean['email'] = df_clean['email'].str.strip().str.lower()

        # Handle missing values
        df_clean = df_clean.dropna(subset=['customer_id', 'email'])

        return df_clean

    def clean_transaction_data(self, df):
        """Clean transaction data"""
        df_clean = df.copy()

        # Convert transaction_date to datetime
        df_clean['transaction_date'] = pd.to_datetime(df_clean['transaction_date'])

        # Remove transactions with invalid amounts
        df_clean = df_clean[df_clean['amount'] > 0]

        # Clean product names
        df_clean['product'] = df_clean['product'].str.strip().str.title()

        # Remove duplicates
        df_clean = df_clean.drop_duplicates(subset=['transaction_id'])

        # Handle missing values
        df_clean = df_clean.dropna(subset=['transaction_id', 'customer_id', 'amount'])

        return df_clean

class DataValidator:
    """Data validation operations"""

    def validate_customers(self, df):
        """Validate customer data"""
        # Email validation
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        df = df[df['email'].str.match(email_pattern)]

        # Age validation (reasonable age range)
        df = df[(df['age'] >= 18) & (df['age'] <= 120)]

        return df

    def validate_transactions(self, df):
        """Validate transaction data"""
        # Amount validation (positive amounts only)
        df = df[df['amount'] > 0]

        # Date validation (not future dates)
        today = datetime.now()
        df = df[df['transaction_date'] <= today]

        return df

    def generate_data_quality_report(self, df, dataset_name):
        """Generate data quality report"""
        report = {
            'dataset': dataset_name,
            'total_records': len(df),
            'missing_values': df.isnull().sum().to_dict(),
            'duplicate_records': df.duplicated().sum(),
            'data_types': df.dtypes.to_dict()
        }

        return report
