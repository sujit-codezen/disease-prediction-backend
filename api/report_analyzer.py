import os
import re
import json
from PIL import Image

NORMAL_RANGES = {
    'hemoglobin': {'min': 12.0, 'max': 17.5, 'unit': 'g/dL', 'low': 'Anemia risk', 'high': 'Polycythemia'},
    'glucose': {'min': 70, 'max': 140, 'unit': 'mg/dL', 'low': 'Hypoglycemia', 'high': 'Diabetes risk'},
    'cholesterol': {'min': 0, 'max': 200, 'unit': 'mg/dL', 'low': 'Normal', 'high': 'High cholesterol'},
    'ldl': {'min': 0, 'max': 130, 'unit': 'mg/dL', 'low': 'Normal', 'high': 'Bad cholesterol high'},
    'hdl': {'min': 40, 'max': 100, 'unit': 'mg/dL', 'low': 'Heart disease risk', 'high': 'Protective'},
    'triglycerides': {'min': 0, 'max': 150, 'unit': 'mg/dL', 'low': 'Normal', 'high': 'Pancreatitis risk'},
    'wbc': {'min': 4500, 'max': 11000, 'unit': '/μL', 'low': 'Infection risk', 'high': 'Infection/leukemia'},
    'rbc': {'min': 4.0, 'max': 6.0, 'unit': 'million/μL', 'low': 'Anemia', 'high': 'Polycythemia'},
    'platelets': {'min': 150000, 'max': 400000, 'unit': '/μL', 'low': 'Bleeding risk', 'high': 'Clotting risk'},
    'creatinine': {'min': 0.6, 'max': 1.2, 'unit': 'mg/dL', 'low': 'Normal', 'high': 'Kidney disease'},
    'bun': {'min': 7, 'max': 20, 'unit': 'mg/dL', 'low': 'Normal', 'high': 'Kidney disease'},
    'sodium': {'min': 135, 'max': 145, 'unit': 'mEq/L', 'low': 'Hyponatremia', 'high': 'Hypernatremia'},
    'potassium': {'min': 3.5, 'max': 5.0, 'unit': 'mEq/L', 'low': 'Hypokalemia', 'high': 'Hyperkalemia'},
    'calcium': {'min': 8.5, 'max': 10.5, 'unit': 'mg/dL', 'low': 'Osteoporosis', 'high': 'Hypercalcemia'},
    'tsh': {'min': 0.4, 'max': 4.0, 'unit': 'mIU/L', 'low': 'Hyperthyroidism', 'high': 'Hypothyroidism'},
    'alt': {'min': 7, 'max': 56, 'unit': 'U/L', 'low': 'Normal', 'high': 'Liver disease'},
    'ast': {'min': 10, 'max': 40, 'unit': 'U/L', 'low': 'Normal', 'high': 'Liver/heart disease'},
    'bilirubin': {'min': 0.1, 'max': 1.2, 'unit': 'mg/dL', 'low': 'Normal', 'high': 'Liver disease'},
    'vitamin_d': {'min': 30, 'max': 100, 'unit': 'ng/mL', 'low': 'Deficiency', 'high': 'Toxicity'},
    'iron': {'min': 60, 'max': 170, 'unit': 'μg/dL', 'low': 'Anemia', 'high': 'Hemochromatosis'},
}


def extract_text_from_image(file_path):
    try:
        import pytesseract
        image = Image.open(file_path)
        text = pytesseract.image_to_string(image)
        return text
    except Exception as e:
        return f"OCR Error: {str(e)}"


def parse_lab_values(text):
    values = {}
    patterns = [
        r'(\w[\w\s]*)\s*[:=]\s*([\d.]+)\s*(\w*/?\w*)',
        r'(\w[\w\s]*)\s+([\d.]+)\s*(\w*/?\w*)',
        r'(\w[\w\s]*)\s+([\d.]+)',
    ]

    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            name = match[0].strip().lower()
            try:
                value = float(match[1])
            except ValueError:
                continue

            for key in NORMAL_RANGES:
                if key in name or name in key:
                    values[key] = {
                        'value': value,
                        'unit': match[2] if len(match) > 2 else NORMAL_RANGES[key]['unit'],
                        'normal_range': f"{NORMAL_RANGES[key]['min']}-{NORMAL_RANGES[key]['max']}",
                    }
                    break

    return values


def analyze_lab_values(values):
    analysis = {}

    for test_name, data in values.items():
        if test_name not in NORMAL_RANGES:
            continue

        norm = NORMAL_RANGES[test_name]
        value = data['value']

        if value < norm['min']:
            status = 'low'
            concern = norm['low']
        elif value > norm['max']:
            status = 'high'
            concern = norm['high']
        else:
            status = 'normal'
            concern = 'Within normal range'

        analysis[test_name] = {
            'value': value,
            'unit': data.get('unit', norm['unit']),
            'status': status,
            'concern': concern,
            'normal_range': f"{norm['min']}-{norm['max']} {norm['unit']}",
        }

    return analysis


def generate_suggestions(analysis):
    suggestions = []

    for test_name, result in analysis.items():
        if result['status'] == 'low':
            if test_name == 'hemoglobin':
                suggestions.append('Increase iron-rich foods: spinach, red meat, lentils')
            elif test_name == 'vitamin_d':
                suggestions.append('Consider vitamin D supplements and sunlight exposure')
            elif test_name == 'glucose':
                suggestions.append('Eat regular meals to maintain blood sugar')
            elif test_name in ('calcium',):
                suggestions.append('Include dairy products and leafy greens in diet')
        elif result['status'] == 'high':
            if test_name == 'glucose':
                suggestions.append('Reduce sugar intake and monitor blood sugar regularly')
            elif test_name in ('cholesterol', 'ldl'):
                suggestions.append('Reduce saturated fats, increase fiber intake')
            elif test_name == 'triglycerides':
                suggestions.append('Limit alcohol, reduce sugar and refined carbs')
            elif test_name in ('alt', 'ast', 'bilirubin'):
                suggestions.append('Avoid alcohol, consult hepatologist')
            elif test_name in ('creatinine', 'bun'):
                suggestions.append('Stay hydrated, reduce salt intake')
            elif test_name == 'wbc':
                suggestions.append('Monitor for signs of infection, consult doctor')

    if not suggestions:
        suggestions.append('All values appear within normal range')
    suggestions.append('Always consult your healthcare provider for proper interpretation')

    return suggestions


def analyze_report(file_path, report_type='blood'):
    if report_type in ('blood', 'urine'):
        text = extract_text_from_image(file_path)
        values = parse_lab_values(text)
        analysis = analyze_lab_values(values)
        suggestions = generate_suggestions(analysis)

        return {
            'extracted_text': text,
            'values': values,
            'analysis': analysis,
            'suggestions': suggestions,
            'report_type': report_type,
        }

    return {
        'extracted_text': 'OCR not supported for this report type',
        'values': {},
        'analysis': {},
        'suggestions': ['Manual review required for this report type'],
        'report_type': report_type,
    }
