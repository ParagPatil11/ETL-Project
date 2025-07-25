"""
Data Extractors for various data sources
"""

import pandas as pd
import sqlite3
import requests
import json
from abc import ABC, abstractmethod

class BaseExtractor(ABC):
    """Base class for all data extractors"""

    @abstractmethod
    def extract(self):
        pass

class CSVExtractor(BaseExtractor):
    """Extract data from CSV files"""

    def __init__(self, file_path):
        self.file_path = file_path

    def extract(self):
        """Extract data from CSV file"""
        try:
            df = pd.read_csv(self.file_path)
            return df
        except Exception as e:
            raise Exception(f"Failed to extract from CSV {self.file_path}: {str(e)}")

class DatabaseExtractor(BaseExtractor):
    """Extract data from SQL databases"""

    def __init__(self, connection_string):
        self.connection_string = connection_string

    def extract(self, query=None):
        """Extract data from database"""
        try:
            conn = sqlite3.connect(self.connection_string)

            if query:
                df = pd.read_sql_query(query, conn)
            else:
                # Default query to get all transactions
                df = pd.read_sql_query("SELECT * FROM transactions", conn)

            conn.close()
            return df

        except Exception as e:
            raise Exception(f"Failed to extract from database: {str(e)}")

class APIExtractor(BaseExtractor):
    """Extract data from REST APIs"""

    def __init__(self, api_url, headers=None):
        self.api_url = api_url
        self.headers = headers or {}

    def extract(self):
        """Extract data from API"""
        try:
            response = requests.get(self.api_url, headers=self.headers)
            response.raise_for_status()

            data = response.json()
            df = pd.DataFrame(data)

            return df

        except Exception as e:
            raise Exception(f"Failed to extract from API {self.api_url}: {str(e)}")
