import pytest
from unittest.mock import patch
from common.backend import validate_jwt_token, upload_lap, JWTValidationError, LapUploadError

@patch('common.backend.requests.get')
def test_test_jwt_token_valid(mock_get):
    mock_get.return_value.ok = True
    mock_get.return_value.raise_for_status = lambda: None
    assert validate_jwt_token('validtoken', 'http://test') is True

@patch('common.backend.requests.get')
def test_test_jwt_token_invalid(mock_get):
    mock_get.side_effect = Exception('fail')
    with pytest.raises(JWTValidationError):
        validate_jwt_token('badtoken', 'http://test')

@patch('common.backend.requests.post')
def test_upload_lap_success(mock_post):
    mock_post.return_value.ok = True
    upload_lap('token', 'http://test', {'lap_id': 'lap_01', 'data': []})

@patch('common.backend.requests.post')
def test_upload_lap_fail(mock_post):
    mock_post.side_effect = Exception('fail')
    with pytest.raises(LapUploadError):
        upload_lap('token', 'http://test', {'lap_id': 'lap_01', 'data': []})
