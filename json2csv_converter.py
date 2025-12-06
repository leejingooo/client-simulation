"""
JSON to CSV Converter for PSYCHE Evaluation Results

Converts PSYCHE evaluation results from JSON format to CSV format.
"""

import pandas as pd
from typing import Dict, Any
import io


def psyche_json_to_csv(evaluation_data: Dict[str, Any]) -> str:
    """
    Convert PSYCHE evaluation JSON data to CSV format.
    
    Args:
        evaluation_data: Dictionary containing evaluation results with structure:
            {
                "element_name": {
                    "sp_content": "...",
                    "paca_content": "...",
                    "score": 0.85,
                    "weight": 1,
                    "weighted_score": 0.85
                },
                ...
                "psyche_score": 45.5
            }
    
    Returns:
        CSV string with columns: element, sp_content, paca_content, score, weight, weighted_score
    """
    
    # Prepare data for DataFrame
    rows = []
    
    for element_name, element_data in evaluation_data.items():
        # Skip the psyche_score entry as it's not an element
        if element_name == 'psyche_score':
            continue
        
        # Skip if element_data is not a dictionary (safety check)
        if not isinstance(element_data, dict):
            continue
        
        row = {
            'element': element_name,
            'sp_content': element_data.get('sp_content', ''),
            'paca_content': element_data.get('paca_content', ''),
            'score': element_data.get('score', 0.0),
            'weight': element_data.get('weight', 1),
            'weighted_score': element_data.get('weighted_score', 0.0)
        }
        rows.append(row)
    
    # Add PSYCHE score as the last row
    if 'psyche_score' in evaluation_data:
        rows.append({
            'element': 'PSYCHE SCORE (Total)',
            'sp_content': '',
            'paca_content': '',
            'score': '',
            'weight': '',
            'weighted_score': evaluation_data['psyche_score']
        })
    
    # Create DataFrame
    df = pd.DataFrame(rows)
    
    # Convert to CSV string
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False, encoding='utf-8')
    csv_string = csv_buffer.getvalue()
    
    return csv_string


def psyche_json_to_dataframe(evaluation_data: Dict[str, Any]) -> pd.DataFrame:
    """
    Convert PSYCHE evaluation JSON data to pandas DataFrame.
    
    Args:
        evaluation_data: Dictionary containing evaluation results
    
    Returns:
        pandas DataFrame with columns: element, sp_content, paca_content, score, weight, weighted_score
    """
    
    rows = []
    
    for element_name, element_data in evaluation_data.items():
        if element_name == 'psyche_score':
            continue
        
        if not isinstance(element_data, dict):
            continue
        
        row = {
            'element': element_name,
            'sp_content': element_data.get('sp_content', ''),
            'paca_content': element_data.get('paca_content', ''),
            'score': element_data.get('score', 0.0),
            'weight': element_data.get('weight', 1),
            'weighted_score': element_data.get('weighted_score', 0.0)
        }
        rows.append(row)
    
    # Add PSYCHE score as the last row
    if 'psyche_score' in evaluation_data:
        rows.append({
            'element': 'PSYCHE SCORE (Total)',
            'sp_content': '',
            'paca_content': '',
            'score': '',
            'weight': '',
            'weighted_score': evaluation_data['psyche_score']
        })
    
    return pd.DataFrame(rows)


def expert_validation_json_to_csv(validation_data: Dict[str, Any]) -> str:
    """
    Convert expert validation JSON data to CSV format.
    
    Args:
        validation_data: Dictionary containing validation results with structure:
            {
                "experiment_number": 6101_101,
                "timestamp": 1234567890,
                "elements": {
                    "element_name": {
                        "expert_choice": "...",
                        "paca_content": "...",
                        "score": 1.0,
                        "weight": 5,
                        "weighted_score": 5.0
                    },
                    ...
                },
                "expert_score": 45.5
            }
    
    Returns:
        CSV string with columns: element, expert_choice, paca_content, score, weight, weighted_score
    """
    
    # Prepare data for DataFrame
    rows = []
    
    # Get elements
    elements = validation_data.get('elements', {})
    
    for element_name, element_data in elements.items():
        # Skip if element_data is not a dictionary (safety check)
        if not isinstance(element_data, dict):
            continue
        
        row = {
            'element': element_name,
            'expert_choice': element_data.get('expert_choice', ''),
            'paca_content': element_data.get('paca_content', ''),
            'score': element_data.get('score', 0.0),
            'weight': element_data.get('weight', 1),
            'weighted_score': element_data.get('weighted_score', 0.0)
        }
        rows.append(row)
    
    # Add Expert score as the last row
    if 'expert_score' in validation_data:
        rows.append({
            'element': 'EXPERT SCORE (Total)',
            'expert_choice': '',
            'paca_content': '',
            'score': '',
            'weight': '',
            'weighted_score': validation_data['expert_score']
        })
    
    # Add quality assessment scores (PIQSCA - PACA Interview Quality SCore Assessment)
    quality_assessment = validation_data.get('quality_assessment', {})
    
    if quality_assessment:
        # Add each quality criterion
        if 'Process of the Interview' in quality_assessment:
            rows.append({
                'element': 'PIQSCA - Process of the Interview',
                'expert_choice': '',
                'paca_content': '',
                'score': quality_assessment['Process of the Interview'],
                'weight': '',
                'weighted_score': ''
            })
        
        if 'Techniques' in quality_assessment:
            rows.append({
                'element': 'PIQSCA - Techniques',
                'expert_choice': '',
                'paca_content': '',
                'score': quality_assessment['Techniques'],
                'weight': '',
                'weighted_score': ''
            })
        
        if 'Information for Diagnosis' in quality_assessment:
            rows.append({
                'element': 'PIQSCA - Information for Diagnosis',
                'expert_choice': '',
                'paca_content': '',
                'score': quality_assessment['Information for Diagnosis'],
                'weight': '',
                'weighted_score': ''
            })
        
        # Calculate PIQSCA total score (sum of all three)
        piqsca_total = sum([
            quality_assessment.get('Process of the Interview', 0),
            quality_assessment.get('Techniques', 0),
            quality_assessment.get('Information for Diagnosis', 0)
        ])
        
        rows.append({
            'element': 'PIQSCA SCORE (Total)',
            'expert_choice': '',
            'paca_content': '',
            'score': '',
            'weight': '',
            'weighted_score': piqsca_total
        })
    
    # Create DataFrame
    df = pd.DataFrame(rows)
    
    # Convert to CSV string
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False, encoding='utf-8')
    csv_string = csv_buffer.getvalue()
    
    return csv_string


def expert_validation_json_to_dataframe(validation_data: Dict[str, Any]) -> pd.DataFrame:
    """
    Convert expert validation JSON data to pandas DataFrame.
    
    Args:
        validation_data: Dictionary containing validation results
    
    Returns:
        pandas DataFrame with columns: element, expert_choice, paca_content, score, weight, weighted_score
    """
    
    rows = []
    
    # Get elements
    elements = validation_data.get('elements', {})
    
    for element_name, element_data in elements.items():
        if not isinstance(element_data, dict):
            continue
        
        row = {
            'element': element_name,
            'expert_choice': element_data.get('expert_choice', ''),
            'paca_content': element_data.get('paca_content', ''),
            'score': element_data.get('score', 0.0),
            'weight': element_data.get('weight', 1),
            'weighted_score': element_data.get('weighted_score', 0.0)
        }
        rows.append(row)
    
    # Add Expert score as the last row
    if 'expert_score' in validation_data:
        rows.append({
            'element': 'EXPERT SCORE (Total)',
            'expert_choice': '',
            'paca_content': '',
            'score': '',
            'weight': '',
            'weighted_score': validation_data['expert_score']
        })
    
    # Add quality assessment scores (PIQSCA - PACA Interview Quality SCore Assessment)
    quality_assessment = validation_data.get('quality_assessment', {})
    
    if quality_assessment:
        # Add each quality criterion
        if 'Process of the Interview' in quality_assessment:
            rows.append({
                'element': 'PIQSCA - Process of the Interview',
                'expert_choice': '',
                'paca_content': '',
                'score': quality_assessment['Process of the Interview'],
                'weight': '',
                'weighted_score': ''
            })
        
        if 'Techniques' in quality_assessment:
            rows.append({
                'element': 'PIQSCA - Techniques',
                'expert_choice': '',
                'paca_content': '',
                'score': quality_assessment['Techniques'],
                'weight': '',
                'weighted_score': ''
            })
        
        if 'Information for Diagnosis' in quality_assessment:
            rows.append({
                'element': 'PIQSCA - Information for Diagnosis',
                'expert_choice': '',
                'paca_content': '',
                'score': quality_assessment['Information for Diagnosis'],
                'weight': '',
                'weighted_score': ''
            })
        
        # Calculate PIQSCA total score (sum of all three)
        piqsca_total = sum([
            quality_assessment.get('Process of the Interview', 0),
            quality_assessment.get('Techniques', 0),
            quality_assessment.get('Information for Diagnosis', 0)
        ])
        
        rows.append({
            'element': 'PIQSCA SCORE (Total)',
            'expert_choice': '',
            'paca_content': '',
            'score': '',
            'weight': '',
            'weighted_score': piqsca_total
        })
    
    return pd.DataFrame(rows)
