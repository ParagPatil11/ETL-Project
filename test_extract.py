"""
Unit tests for data extraction modules
"""

import unittest
import pandas as pd
from unittest.mock import patch, MagicMock
from src.extract.data_extractors import CSVExtractor, DatabaseExtractor, APIExtractor

class TestDataExtractors(unittest.TestCase):

    def test_csv_extractor_success(self):
        """Test successful CSV extraction"""
        # Create sample CSV data
        sample_data = pd.DataFrame({
            'id': [1, 2, 3],
            'name': ['Alice', 'Bob', 'Charlie']
        })

        with patch('pandas.read_csv', return_value=sample_data):
            extractor = CSVExtractor('test.csv')
            result = extractor.extract()

            self.assertEqual(len(result), 3)
            self.assertListEqual(list(result.columns), ['id', 'name'])

    def test_csv_extractor_file_not_found(self):
        """Test CSV extraction with file not found"""
        with patch('pandas.read_csv', side_effect=FileNotFoundError):
            extractor = CSVExtractor('nonexistent.csv')

            with self.assertRaises(Exception) as context:
                extractor.extract()

            self.assertIn("Failed to extract from CSV", str(context.exception))

    @patch('sqlite3.connect')
    @patch('pandas.read_sql_query')
    def test_database_extractor_success(self, mock_read_sql, mock_connect):
        """Test successful database extraction"""
        # Mock database connection and query result
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn

        sample_data = pd.DataFrame({
            'id': [1, 2, 3],
            'amount': [100, 200, 300]
        })
        mock_read_sql.return_value = sample_data

        extractor = DatabaseExtractor('test.db')
        result = extractor.extract()

        self.assertEqual(len(result), 3)
        mock_connect.assert_called_once_with('test.db')
        mock_conn.close.assert_called_once()

    @patch('requests.get')
    def test_api_extractor_success(self, mock_get):
        """Test successful API extraction"""
        # Mock API response
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {'id': 1, 'name': 'Product A'},
            {'id': 2, 'name': 'Product B'}
        ]
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        extractor = APIExtractor('http://api.example.com/data')
        result = extractor.extract()

        self.assertEqual(len(result), 2)
        self.assertIn('id', result.columns)
        self.assertIn('name', result.columns)

    @patch('requests.get')
    def test_api_extractor_http_error(self, mock_get):
        """Test API extraction with HTTP error"""
        mock_get.side_effect = Exception("HTTP 500 Error")

        extractor = APIExtractor('http://api.example.com/data')

        with self.assertRaises(Exception) as context:
            extractor.extract()

        self.assertIn("Failed to extract from API", str(context.exception))

if __name__ == '__main__':
    unittest.main()
