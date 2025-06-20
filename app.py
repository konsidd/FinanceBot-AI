from flask import Flask, render_template, request, jsonify
import pandas as pd
import re
import os
import json # Already imported, good

# Try to read CSV first, then Excel as fallback
data_file = "report.csv"
if os.path.exists(data_file):
    data = pd.read_csv(data_file)
else:
    excel_path = "report.xlsx"
    if os.path.exists(excel_path):
        data = pd.read_excel(excel_path)
    else:
        # Create dummy data if neither file exists for demonstration purposes
        print("Warning: Neither report.csv nor report.xlsx found. Using dummy data.")
        data = pd.DataFrame({
            'Company': ['Apple', 'Tesla', 'Microsoft', 'Apple', 'Tesla', 'Microsoft', 'Apple', 'Tesla', 'Microsoft', 'Apple', 'Tesla', 'Microsoft'],
            'Year': [2020, 2020, 2020, 2021, 2021, 2021, 2022, 2022, 2022, 2023, 2023, 2023],
            'Total Revenue': [274515000000, 31536000000, 143015000000, 365817000000, 53823000000, 168088000000, 394328000000, 81462000000, 198270000000, 383285000000, 96773000000, 211915000000],
            'Net Income': [57411000000, 721000000, 44281000000, 94680000000, 5519000000, 61271000000, 99803000000, 12556000000, 72361000000, 96995000000, 14997000000, 72361000000],
            'Total Assets': [323888000000, 52148000000, 301311000000, 351002000000, 62131000000, 333779000000, 352755000000, 82338000000, 364840000000, 352583000000, 106618000000, 411976000000],
            'Total Liabilities': [258549000000, 28748000000, 183007000000, 287912000000, 30548000000, 191791000000, 302083000000, 36440000000, 198298000000, 290437000000, 43009000000, 205753000000],
            'Cash Flow From Operating Activities': [80674000000, 6939000000, 60670000000, 104038000000, 11497000000, 76743000000, 114320000000, 14724000000, 89035000000, 110544000000, 13203000000, 87681000000]
        })


app = Flask(__name__)

# Normalize column names and handle the data
data.columns = [col.strip().replace('_', ' ').title() for col in data.columns]

# Convert numeric columns to proper format
numeric_columns = ['Total Revenue', 'Net Income', 'Total Assets', 'Total Liabilities', 'Cash Flow From Operating Activities']
for col in numeric_columns:
    if col in data.columns:
        data[col] = pd.to_numeric(data[col], errors='coerce')

# Define comprehensive metrics mapping
metrics_map = {
    "revenue": "Total Revenue",
    "total revenue": "Total Revenue",
    "income": "Net Income", 
    "net income": "Net Income",
    "profit": "Net Income",
    "assets": "Total Assets",
    "total assets": "Total Assets",
    "liabilities": "Total Liabilities",
    "total liabilities": "Total Liabilities",
    "cash flow": "Cash Flow From Operating Activities",
    "operating cash flow": "Cash Flow From Operating Activities",
    "cash flow from operating activities": "Cash Flow From Operating Activities"
}

def format_number(value):
    """Format large numbers in a readable way"""
    if pd.isna(value) or value == 0:
        return "0"
    
    if abs(value) >= 1_000_000_000:
        return f"${value/1_000_000_000:.2f} billion"
    elif abs(value) >= 1_000_000:
        return f"${value/1_000_000:.2f} million" 
    elif abs(value) >= 1_000:
        return f"${value/1_000:.2f} thousand"
    else:
        return f"${value:.2f}"

def extract_company(query, companies):
    """Extract company name from query"""
    query_lower = query.lower()
    for company in companies:
        if company.lower() in query_lower:
            return company
    return None

def extract_year(query):
    """Extract year from query"""
    year_match = re.search(r"\b(20\d{2})\b", query)
    return int(year_match.group(1)) if year_match else None

def extract_metric(query):
    """Extract metric from query"""
    query_lower = query.lower()
    # Sort by length to match longer phrases first
    sorted_metrics = sorted(metrics_map.keys(), key=len, reverse=True)
    for metric_key in sorted_metrics:
        if metric_key in query_lower:
            return metrics_map[metric_key]
    return None

def get_available_data_summary():
    """Get summary of available data"""
    companies = data['Company'].unique().tolist()
    years = sorted(data['Year'].unique().tolist())
    metrics = [col for col in data.columns if col not in ['Company', 'Year']]
    
    return {
        'companies': companies,
        'years': years,
        'metrics': metrics
    }

def handle_comparison_query(query):
    """Handle comparison queries between companies or years"""
    query_lower = query.lower()
    
    # Check for general comparison keywords
    if "compare" in query_lower or "vs" in query_lower or "versus" in query_lower:
        companies = data['Company'].unique()
        found_companies = [c for c in companies if c.lower() in query_lower]
        
        # Check for numeric years in query for comparison
        years_in_query = re.findall(r"\b(20\d{2})\b", query_lower)
        target_year = None
        if years_in_query:
            # Prioritize the first found year, or refine logic if multiple years possible in one comparison
            target_year = int(years_in_query[0])
        else:
            target_year = data['Year'].max() # Default to latest year if no year specified

        metric = extract_metric(query)
        
        if len(found_companies) >= 2 and metric:
            results = []
            chart_datasets = []
            
            # Map metric name to a more readable format for chart label
            display_metric_name = metric.replace('Total ', '').replace(' From Operating Activities', '').title()

            chart_labels = [c.capitalize() for c in found_companies]
            chart_data_values = []
            
            for company in found_companies:
                row = data[(data['Company'] == company) & (data['Year'] == target_year)]
                if not row.empty:
                    value = row.iloc[0][metric]
                    results.append(f"{company.capitalize()}: {format_number(value)}")
                    chart_data_values.append(value)
                else:
                    results.append(f"No data available for {company.capitalize()} in {target_year}.")
                    chart_data_values.append(0) # Add 0 or None for missing data in chart

            if results:
                # Assign distinct colors for comparison chart
                colors = ['rgba(102, 126, 234, 0.8)', 'rgba(240, 147, 251, 0.8)', 'rgba(79, 172, 254, 0.8)']
                border_colors = ['rgb(102, 126, 234)', 'rgb(240, 147, 251)', 'rgb(79, 172, 254)']

                # Create separate dataset for each company in a bar chart for clearer comparison
                for i, company_name in enumerate(found_companies):
                    company_data_for_chart = data[(data['Company'] == company_name) & (data['Year'] == target_year)]
                    value_for_chart = company_data_for_chart.iloc[0][metric] if not company_data_for_chart.empty else 0
                    
                    chart_datasets.append({
                        'label': f"{company_name.capitalize()} {display_metric_name}",
                        'data': [value_for_chart],
                        'backgroundColor': colors[i % len(colors)], # Cycle through colors
                        'borderColor': border_colors[i % len(border_colors)],
                        'borderWidth': 2
                    })

                chart_info = {
                    'type': 'bar', # Force bar chart for comparison
                    'labels': chart_labels,
                    'datasets': [{
                        'label': f"{display_metric_name} in {target_year}",
                        'data': chart_data_values,
                        'backgroundColor': [colors[i % len(colors)] for i in range(len(chart_labels))],
                        'borderColor': [border_colors[i % len(border_colors)] for i in range(len(chart_labels))],
                        'borderWidth': 2
                    }]
                }
                
                # Corrected: Create a single dataset with multiple bars
                chart_info = {
                    'type': 'bar',
                    'labels': chart_labels,
                    'datasets': [
                        {
                            'label': f"{display_metric_name} in {target_year}",
                            'data': chart_data_values,
                            'backgroundColor': [colors[i % len(colors)] for i in range(len(chart_labels))],
                            'borderColor': [border_colors[i % len(border_colors)] for i in range(len(chart_labels))],
                            'borderWidth': 2
                        }
                    ]
                }
                
                return {"response": f"{display_metric_name} comparison for {target_year}:<br><br>{'<br>'.join(results)}", "chart_data": chart_info}
    
    return None

@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        user_query = request.form.get("user_input", "").lower()
        response_text = ""
        chart_data = None

        # Handle comparison queries first
        comparison_response = handle_comparison_query(user_query)
        if comparison_response:
            return jsonify(comparison_response) # Return JSON directly for comparison

        # Handle single company or trend queries
        companies = data['Company'].unique()
        company = extract_company(user_query, companies)
        year = extract_year(user_query)
        metric = extract_metric(user_query)
        
        # Adjusting 2024 to 2023 as per index.html's logic
        if year == 2024:
            year = 2023

        if company and metric:
            display_metric_name = metric.replace('Total ', '').replace(' From Operating Activities', '').title()

            if "trend" in user_query or "over time" in user_query or not year:
                # Handle trend query
                company_trend = data[data['Company'].str.lower() == company.lower()][['Year', metric]].dropna().sort_values(by='Year')
                if not company_trend.empty:
                    chart_data = {
                        'type': 'line',
                        'labels': company_trend['Year'].tolist(),
                        'datasets': [{
                            'label': f"{company.capitalize()} {display_metric_name} Trend",
                            'data': company_trend[metric].tolist(),
                            'borderColor': 'rgb(118, 75, 162)',
                            'backgroundColor': 'rgba(118, 75, 162, 0.2)',
                            'borderWidth': 3,
                            'fill': True,
                            'tension': 0.4,
                            'pointBackgroundColor': 'rgb(118, 75, 162)',
                            'pointBorderColor': '#fff',
                            'pointBorderWidth': 2,
                            'pointRadius': 6
                        }]
                    }
                    response_text = f"Here's the {display_metric_name.lower()} trend for {company.capitalize()} from {company_trend['Year'].min()} to {company_trend['Year'].max()}."
                else:
                    response_text = f"No trend data available for {display_metric_name.lower()} of {company.capitalize()}."
            else:
                # Handle single year query
                row = data[(data['Company'].str.lower() == company.lower()) & (data['Year'] == year)]
                if not row.empty:
                    value = row.iloc[0][metric]
                    if pd.notna(value):
                        response_text = f"{company.capitalize()}'s {display_metric_name.lower()} in {year} was {format_number(value)}."
                    else:
                        response_text = f"No data available for {display_metric_name.lower()} of {company.capitalize()} in {year}."
                else:
                    response_text = f"Sorry, I couldn't find data for {company.capitalize()} in {year}."
                    available_years = data[data['Company'].str.lower() == company.lower()]['Year'].unique()
                    if len(available_years) > 0:
                        response_text += f" Available years for {company.capitalize()}: {', '.join(map(str, sorted(available_years)))}"
        
        elif "help" in user_query or "what can you do" in user_query:
            summary = get_available_data_summary()
            response_text = f"""I can help you analyze financial data for: {', '.join([c.capitalize() for c in summary['companies']])}.
Available years: {', '.join(map(str, summary['years']))}
Available metrics: {', '.join([m.replace('Total ', '').replace(' From Operating Activities', '').title() for m in summary['metrics']])}
Try asking questions like:
• "What was Apple's revenue in 2022?"
• "Show me Tesla's net income in 2024"
• "Compare Microsoft and Apple revenue in 2023"
• "What are Tesla's liabilities?"
• "Show Apple's revenue trend"
"""
        else:
            response_text = """Please ask a specific question about financial data. For example:
• "What was the revenue of Apple in 2022?"
• "Show me Tesla's net income in 2024"
• "Compare Microsoft and Apple revenue"
• "Show Apple's revenue trend"
• Type 'help' to see all available data"""
        
        return jsonify(response=response_text, chart_data=chart_data)

    # For GET requests, render the initial page
    data_summary = get_available_data_summary()
    return render_template("index.html", 
                         companies=data_summary['companies'],
                         years=data_summary['years'],
                         metrics=data_summary['metrics'])

if __name__ == "__main__":
    # Ensure report.csv or report.xlsx exists, or the dummy data will be used.
    # For a real application, you'd handle this more robustly.
    app.run(debug=True)
