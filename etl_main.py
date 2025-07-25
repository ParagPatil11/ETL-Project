"""
Main ETL Pipeline
Orchestrates the complete Extract, Transform, Load process
"""

import pandas as pd
import logging
import yaml
from datetime import datetime
from src.extract.data_extractors import CSVExtractor, DatabaseExtractor
from src.transform.data_cleaners import DataCleaner
from src.transform.data_validators import DataValidator
from src.load.data_loaders import DatabaseLoader
from src.utils.logger import setup_logger
from src.utils.config import Config

class ETLPipeline:
    def __init__(self, config_path='config/config.yml'):
        """Initialize ETL Pipeline with configuration"""
        self.config = Config(config_path)
        self.logger = setup_logger('etl_pipeline')
        self.stats = {
            'start_time': None,
            'end_time': None,
            'records_extracted': 0,
            'records_transformed': 0,
            'records_loaded': 0,
            'errors': []
        }

    def extract_data(self):
        """Extract data from various sources"""
        self.logger.info("Starting data extraction...")

        try:
            # Extract customer data from CSV
            csv_extractor = CSVExtractor(self.config.get('sources.customer_csv'))
            customers_df = csv_extractor.extract()

            # Extract transaction data from database
            db_extractor = DatabaseExtractor(self.config.get('sources.transactions_db'))
            transactions_df = db_extractor.extract()

            self.stats['records_extracted'] = len(customers_df) + len(transactions_df)
            self.logger.info(f"Extracted {self.stats['records_extracted']} records")

            return customers_df, transactions_df

        except Exception as e:
            self.logger.error(f"Error during extraction: {str(e)}")
            self.stats['errors'].append(f"Extraction error: {str(e)}")
            raise

    def transform_data(self, customers_df, transactions_df):
        """Transform and clean the extracted data"""
        self.logger.info("Starting data transformation...")

        try:
            # Initialize data cleaner and validator
            cleaner = DataCleaner()
            validator = DataValidator()

            # Clean customer data
            customers_clean = cleaner.clean_customer_data(customers_df)

            # Clean transaction data
            transactions_clean = cleaner.clean_transaction_data(transactions_df)

            # Validate data quality
            customers_valid = validator.validate_customers(customers_clean)
            transactions_valid = validator.validate_transactions(transactions_clean)

            # Join and aggregate data
            final_df = self._join_and_aggregate(customers_valid, transactions_valid)

            self.stats['records_transformed'] = len(final_df)
            self.logger.info(f"Transformed {self.stats['records_transformed']} records")

            return final_df

        except Exception as e:
            self.logger.error(f"Error during transformation: {str(e)}")
            self.stats['errors'].append(f"Transformation error: {str(e)}")
            raise

    def load_data(self, data_df):
        """Load transformed data to target destination"""
        self.logger.info("Starting data loading...")

        try:
            # Load to database
            db_loader = DatabaseLoader(self.config.get('targets.data_warehouse'))
            db_loader.load(data_df, table_name='customer_summary')

            # Load to CSV for backup
            output_path = f"data/output/customer_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            data_df.to_csv(output_path, index=False)

            self.stats['records_loaded'] = len(data_df)
            self.logger.info(f"Loaded {self.stats['records_loaded']} records")

        except Exception as e:
            self.logger.error(f"Error during loading: {str(e)}")
            self.stats['errors'].append(f"Loading error: {str(e)}")
            raise

    def _join_and_aggregate(self, customers_df, transactions_df):
        """Join customer and transaction data and create aggregations"""
        # Join data on customer_id
        joined_df = customers_df.merge(
            transactions_df, 
            on='customer_id', 
            how='inner'
        )

        # Aggregate transaction data per customer
        agg_df = joined_df.groupby([
            'customer_id', 'first_name', 'last_name', 
            'email', 'age', 'city'
        ]).agg({
            'amount': ['sum', 'mean', 'count']
        }).round(2)

        # Flatten column names
        agg_df.columns = ['total_spent', 'avg_transaction', 'transaction_count']
        agg_df = agg_df.reset_index()

        # Filter customers with more than $500 total spending
        agg_df = agg_df[agg_df['total_spent'] > 500]

        return agg_df

    def run(self):
        """Execute the complete ETL pipeline"""
        self.stats['start_time'] = datetime.now()
        self.logger.info("Starting ETL Pipeline execution")

        try:
            # Extract
            customers_df, transactions_df = self.extract_data()

            # Transform
            final_df = self.transform_data(customers_df, transactions_df)

            # Load
            self.load_data(final_df)

            self.stats['end_time'] = datetime.now()
            duration = self.stats['end_time'] - self.stats['start_time']

            self.logger.info(f"ETL Pipeline completed successfully in {duration}")
            self.logger.info(f"Final statistics: {self.stats}")

            return True, self.stats

        except Exception as e:
            self.stats['end_time'] = datetime.now()
            self.logger.error(f"ETL Pipeline failed: {str(e)}")
            return False, self.stats

if __name__ == "__main__":
    pipeline = ETLPipeline()
    success, stats = pipeline.run()

    if success:
        print("ETL Pipeline completed successfully!")
        print(f"Statistics: {stats}")
    else:
        print("ETL Pipeline failed!")
        print(f"Errors: {stats['errors']}")
